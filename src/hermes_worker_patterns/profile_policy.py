import os
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

from hermes_worker_patterns.schemas import ModelPolicy, PatternLane


@dataclass
class RolePolicy:
    preferred_profile: str
    fallback_profiles: list[str] = field(default_factory=list)
    model_policy: ModelPolicy = field(default_factory=ModelPolicy)
    toolsets: list[str] = field(default_factory=list)


@dataclass
class EscalationPolicy:
    premium_escalation_profile: str
    module_swarm_default_profile: str
    code_heavy_profile: str
    premium_code_cap: int = 3  # Preserve non-module-swarm premium-code cap of 3


@dataclass(frozen=True)
class SwarmRosterEntry:
    id: str
    name: str = ""
    role: str = ""
    specialty: str = ""
    model: str = ""
    preferred_task_types: tuple[str, ...] = ()
    accepts_broadcast: bool = True


@dataclass(frozen=True)
class ModuleSwarmScaleRecommendation:
    requested_lane_count: int
    max_active_lanes: int
    waves_required: int
    wave_size: int
    profile_pool_strategy: str
    integrator_per_wave: bool


def _unique_profiles(profiles: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []
    for profile in profiles:
        if profile in seen:
            continue
        seen.add(profile)
        unique.append(profile)
    return tuple(unique)


@dataclass
class WorkerProfilesPolicy:
    roles: dict[str, RolePolicy]
    escalation_policy: EscalationPolicy
    swarm_roster: tuple[SwarmRosterEntry, ...] = ()
    swarm_roster_path: Path | None = None

    @classmethod
    def load_from_yaml(cls, path: Path) -> "WorkerProfilesPolicy":
        data = yaml.safe_load(path.read_text())
        return cls.load_from_mapping(data)

    @classmethod
    def load_from_mapping(cls, data: dict | None) -> "WorkerProfilesPolicy":
        data = data or {}

        roles = {}
        for role_name, role_data in data.get("roles", {}).items():
            model_policy_data = role_data.get("model_policy", {})
            model_policy = ModelPolicy(
                disable_reasoning=model_policy_data.get("disable_reasoning", False)
            )
            roles[role_name] = RolePolicy(
                preferred_profile=role_data["preferred_profile"],
                fallback_profiles=role_data.get("fallback_profiles", []),
                model_policy=model_policy,
                toolsets=role_data.get("toolsets", []),
            )

        escalation_data = data.get("escalation_policy", {})
        escalation_policy = EscalationPolicy(
            premium_escalation_profile=escalation_data["premium_escalation_profile"],
            module_swarm_default_profile=escalation_data["module_swarm_default_profile"],
            code_heavy_profile=escalation_data["code_heavy_profile"],
            premium_code_cap=escalation_data.get("premium_code_cap", 3),
        )

        roster_path = _default_swarm_roster_path()
        roster = _load_swarm_roster(roster_path) if roster_path is not None else ()

        return cls(
            roles=roles,
            escalation_policy=escalation_policy,
            swarm_roster=roster,
            swarm_roster_path=roster_path,
        )

    def apply_canonical_swarm_roster(
        self,
        lanes: tuple[PatternLane, ...],
    ) -> tuple[tuple[PatternLane, ...], tuple[str, ...]]:
        """Map persistent swarm lanes through the canonical Hermes roster.

        Worker-pattern selection owns execution *shape* only. When persistent
        Hermes swarm profiles are requested and a canonical Hermes Workspace
        `swarm.yaml` roster is available, worker identity must come from that
        roster rather than from generic worker-profile policy or lane-number
        heuristics. Parked/offline entries are never selected.
        """

        if not self.swarm_roster:
            return lanes, ()

        notes = [
            f"Persistent swarm profiles mapped via canonical roster: {self.swarm_roster_path}.",
            "Worker-pattern selector chose execution shape only; swarm.yaml remains worker identity/role authority.",
        ]
        unhealthy_profiles = _unhealthy_swarm_profiles()
        if unhealthy_profiles:
            notes.append(
                "Skipped temporarily unhealthy swarm profiles: " + ", ".join(sorted(unhealthy_profiles)) + "."
            )
        used_profiles: set[str] = set()
        mapped_lanes: list[PatternLane] = []
        for lane in lanes:
            task_types = _task_types_for_lane(lane)
            entry = self._select_swarm_entry(task_types, used_profiles)
            if entry is None:
                mapped_lanes.append(lane)
                notes.append(
                    f"No active roster match for lane {lane.role}; kept profile {lane.selected_profile}."
                )
                continue

            used_profiles.add(entry.id)
            hint_suffix = (
                f"canonical swarm roster: {entry.id} ({entry.name}; {entry.role}; model label: {entry.model})"
            )
            mapped_lanes.append(
                replace(
                    lane,
                    selected_profile=entry.id,
                    fallback_profiles=(),
                    hermes_hint=(f"{lane.hermes_hint}; {hint_suffix}" if lane.hermes_hint else hint_suffix),
                )
            )
        return tuple(mapped_lanes), tuple(dict.fromkeys(notes))

    def _select_swarm_entry(
        self,
        task_types: tuple[str, ...],
        used_profiles: set[str],
    ) -> SwarmRosterEntry | None:
        candidates = [
            entry
            for entry in self.swarm_roster
            if entry.accepts_broadcast
            and entry.id not in used_profiles
            and entry.id not in _unhealthy_swarm_profiles()
        ]
        if not candidates:
            return None
        for task_type in task_types:
            for entry in candidates:
                if task_type in entry.preferred_task_types:
                    return entry
        return None

    def select_profile_for_role(
        self,
        role: str,
        is_premium_escalation: bool = False,
        is_module_swarm: bool = False,
        is_code_heavy: bool = False,
    ) -> PatternLane:
        # Default to a generic policy if role not found to prevent errors
        role_policy = self.roles.get(role, RolePolicy(preferred_profile="default", fallback_profiles=["default"]))

        selected_profile = role_policy.preferred_profile
        fallback_profiles = tuple(role_policy.fallback_profiles)
        toolsets = tuple(role_policy.toolsets)
        model_policy = role_policy.model_policy

        if is_module_swarm:
            # Module-swarm execution is the default low-cost parallel profile only. Fail closed rather
            # than silently falling back to premium, review, or default profiles.
            selected_profile = self.escalation_policy.module_swarm_default_profile
            fallback_profiles = ()
            model_policy = ModelPolicy(disable_reasoning=True)
        elif is_premium_escalation:
            selected_profile = self.escalation_policy.premium_escalation_profile
            fallback_profiles = (self.escalation_policy.premium_escalation_profile,) + fallback_profiles
        elif is_code_heavy:
            selected_profile = self.escalation_policy.code_heavy_profile
            fallback_profiles = (self.escalation_policy.code_heavy_profile,) + fallback_profiles

        fallback_profiles = tuple(
            profile for profile in _unique_profiles(fallback_profiles) if profile != selected_profile
        )

        return PatternLane(
            role=role,
            selected_profile=selected_profile,
            fallback_profiles=fallback_profiles,
            toolsets=toolsets,
            model_policy=model_policy,
        )

    def recommend_module_swarm_scale(
        self,
        *,
        requested_lane_count: int,
        max_parallel_lanes: int,
        disjoint_scopes: bool,
        merge_conflict_risk: int,
        risk_level: str = "normal",
        code_heavy: bool = False,
        review_required: bool = False,
        tests_required: bool = False,
    ) -> ModuleSwarmScaleRecommendation:
        """Return safe module-swarm concurrency policy for large decompositions.

        Large module-swarm requests are preserved as a decomposition contract,
        not as permission to run every lane at once.
        Module-swarm execution lanes are the default low-cost parallel profile only; code-heavy
        module-swarm requests do not switch to premium-code or inherit the
        non-module-swarm premium-code cap.
        """
        requested = max(1, requested_lane_count)
        requested_parallel = max(1, max_parallel_lanes)
        risk = risk_level.lower()

        if disjoint_scopes and merge_conflict_risk <= 1 and risk in {"low", "normal"}:
            profile_pool_strategy = "low_cost_disjoint"
            max_active_lanes = min(requested, requested_parallel)
        else:
            profile_pool_strategy = "low_cost_conservative"
            max_active_lanes = min(requested, requested_parallel, 4)

        max_active_lanes = max(1, max_active_lanes)
        waves_required = (requested + max_active_lanes - 1) // max_active_lanes
        integrator_per_wave = waves_required > 1 and (
            merge_conflict_risk >= 2
            or profile_pool_strategy != "low_cost_disjoint"
            or risk in {"high", "critical"}
            or (review_required and profile_pool_strategy != "low_cost_disjoint")
            or (tests_required and profile_pool_strategy != "low_cost_disjoint")
        )

        return ModuleSwarmScaleRecommendation(
            requested_lane_count=requested,
            max_active_lanes=max_active_lanes,
            waves_required=waves_required,
            wave_size=max_active_lanes,
            profile_pool_strategy=profile_pool_strategy,
            integrator_per_wave=integrator_per_wave,
        )

    def profile_pool_strategy_for(
        self,
        is_module_swarm: bool = False,
        is_disjoint: bool = True,
        merge_conflict_risk: int = 0,
        risk_level: str = "normal",
    ) -> str:
        """Backward-compatible strategy helper."""
        if is_module_swarm and is_disjoint and merge_conflict_risk <= 1 and risk_level.lower() in ("low", "normal"):
            return "low_cost_disjoint"
        if risk_level.lower() == "critical":
            return "low_cost_conservative"
        return "low_cost_conservative"

    def capped_premium_code_lane_count(self, requested: int) -> int:
        """Enforce the premium-code cap of 3 for premium-code workers."""
        return min(requested, self.escalation_policy.premium_code_cap)


def _default_swarm_roster_path() -> Path | None:
    configured = os.getenv("HERMES_SWARM_ROSTER_PATH")
    if not configured:
        return None
    candidate = Path(configured).expanduser()
    return candidate if candidate.exists() else None


def _unhealthy_swarm_profiles() -> set[str]:
    """Profiles to skip for this selector pass.

    `HERMES_SWARM_UNHEALTHY_PROFILES` is the canonical knob. The
    `*_BLOCKED_PROFILES` aliases are accepted for provider-side blocked/error
    cases so callers can quarantine a profile after failures such as provider
    refusal/filter code 103 without editing the roster or global Hermes config.
    """

    raw_values = (
        os.getenv("HERMES_SWARM_UNHEALTHY_PROFILES", ""),
        os.getenv("HERMES_SWARM_BLOCKED_PROFILES", ""),
        os.getenv("HERMES_SWARM_PROVIDER_BLOCKED_PROFILES", ""),
    )
    profiles: set[str] = set()
    for raw in raw_values:
        profiles.update(item.strip() for item in raw.split(",") if item.strip())
    return profiles


def _load_swarm_roster(path: Path) -> tuple[SwarmRosterEntry, ...]:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    entries = data.get("workers", data if isinstance(data, list) else [])
    roster: list[SwarmRosterEntry] = []
    for raw_entry in entries:
        if not isinstance(raw_entry, dict) or not raw_entry.get("id"):
            continue
        roster.append(
            SwarmRosterEntry(
                id=str(raw_entry["id"]),
                name=str(raw_entry.get("name", "")),
                role=str(raw_entry.get("role", "")),
                specialty=str(raw_entry.get("specialty", "")),
                model=str(raw_entry.get("model", "")),
                preferred_task_types=tuple(
                    str(item).lower() for item in raw_entry.get("preferredTaskTypes", [])
                ),
                accepts_broadcast=bool(raw_entry.get("acceptsBroadcast", True)),
            )
        )
    return tuple(roster)


def _task_types_for_lane(lane: PatternLane) -> tuple[str, ...]:
    scope_task_types = []
    for scope in lane.scope:
        normalized = scope.lower()
        if normalized in {"docs", "documentation", "runbook", "handoff", "spec"}:
            scope_task_types.extend(["docs", "runbook", "handoff", "spec"])
        elif normalized in {"review", "qa", "verification", "test", "tests", "smoke"}:
            scope_task_types.extend(["review", "qa", "verification", "smoke"])
        elif normalized in {"scheduler", "cron", "ops", "health", "monitoring"}:
            scope_task_types.extend(["ops", "lifecycle", "backend", "implementation"])
        else:
            scope_task_types.append(normalized)

    role = lane.role.lower()
    if role in {"builder", "phase-worker", "recovery-worker"}:
        return tuple(dict.fromkeys([*scope_task_types, "implementation", "feature", "patch", "backend", "integration"]))
    if role == "reviewer":
        return tuple(dict.fromkeys(["review", "qa", "verification", "smoke", *scope_task_types]))
    if role in {"integrator", "curator"}:
        return tuple(dict.fromkeys(["coordination", "handoff", "integration", "merge-gate", *scope_task_types]))
    if role == "variant-designer":
        return tuple(dict.fromkeys([*scope_task_types, "research", "analysis", "options", "spec"]))
    return tuple(dict.fromkeys(scope_task_types))
