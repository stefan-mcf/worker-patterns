from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from worker_patterns.schemas import ModelPolicy, PatternLane

PRIMARY_ROSTER_ENV = "WORKER_PATTERNS_ROSTER_PATH"
PRIMARY_UNAVAILABLE_ENV = "WORKER_PATTERNS_UNAVAILABLE_WORKERS"
DEPRECATED_ROSTER_ENVS = ("HERMES_SWARM_ROSTER_PATH",)
DEPRECATED_UNAVAILABLE_ENVS = (
    "HERMES_SWARM_UNHEALTHY_PROFILES",
    "HERMES_SWARM_BLOCKED_PROFILES",
    "HERMES_SWARM_PROVIDER_BLOCKED_PROFILES",
)


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
    premium_code_cap: int = 3


@dataclass(frozen=True)
class WorkerRosterEntry:
    id: str
    name: str = ""
    role: str = ""
    specialty: str = ""
    model: str = ""
    preferred_task_types: tuple[str, ...] = ()
    accepts_broadcast: bool = True


# Deprecated compatibility alias.
SwarmRosterEntry = WorkerRosterEntry


@dataclass(frozen=True)
class ModuleSwarmScaleRecommendation:
    requested_lane_count: int
    max_active_lanes: int
    waves_required: int
    wave_size: int
    profile_pool_strategy: str
    integrator_per_wave: bool


@dataclass(frozen=True)
class RosterValidationResult:
    ok: bool
    path: str
    worker_count: int = 0
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "path": self.path,
            "worker_count": self.worker_count,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


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
    worker_roster: tuple[WorkerRosterEntry, ...] = ()
    worker_roster_path: Path | None = None

    @property
    def swarm_roster(self) -> tuple[WorkerRosterEntry, ...]:
        return self.worker_roster

    @property
    def swarm_roster_path(self) -> Path | None:
        return self.worker_roster_path

    @classmethod
    def load_from_yaml(cls, path: Path) -> WorkerProfilesPolicy:
        data = yaml.safe_load(path.read_text())
        return cls.load_from_mapping(data)

    @classmethod
    def load_from_mapping(cls, data: dict | None) -> WorkerProfilesPolicy:
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

        roster_path = _default_worker_roster_path()
        roster = _load_worker_roster(roster_path) if roster_path is not None else ()
        return cls(
            roles=roles,
            escalation_policy=escalation_policy,
            worker_roster=roster,
            worker_roster_path=roster_path,
        )

    def apply_worker_roster(
        self,
        lanes: tuple[PatternLane, ...],
    ) -> tuple[tuple[PatternLane, ...], tuple[str, ...]]:
        """Map persistent worker lanes through an optional user roster."""

        if not self.worker_roster:
            return lanes, ()

        notes = [
            f"Persistent workers mapped via configured roster: {self.worker_roster_path}.",
            "Worker-pattern selector chose execution shape only; the roster remains worker identity authority.",
        ]
        unavailable = _unavailable_workers()
        if unavailable:
            notes.append(
                "Skipped temporarily unavailable workers: " + ", ".join(sorted(unavailable)) + "."
            )
        used_profiles: set[str] = set()
        mapped_lanes: list[PatternLane] = []
        for lane in lanes:
            task_types = _task_types_for_lane(lane)
            entry = self._select_worker_entry(task_types, used_profiles)
            if entry is None:
                mapped_lanes.append(lane)
                notes.append(
                    f"No active roster match for lane {lane.role}; kept profile {lane.selected_profile}."
                )
                continue
            used_profiles.add(entry.id)
            hint_suffix = (
                f"configured worker roster: {entry.id} ({entry.name}; {entry.role}; model label: {entry.model})"
            )
            mapped_lanes.append(
                replace(
                    lane,
                    selected_profile=entry.id,
                    fallback_profiles=(),
                    runtime_hint=(f"{lane.runtime_hint}; {hint_suffix}" if lane.runtime_hint else hint_suffix),
                )
            )
        return tuple(mapped_lanes), tuple(dict.fromkeys(notes))

    # Deprecated compatibility method.
    def apply_canonical_swarm_roster(
        self, lanes: tuple[PatternLane, ...]
    ) -> tuple[tuple[PatternLane, ...], tuple[str, ...]]:
        return self.apply_worker_roster(lanes)

    def _select_worker_entry(
        self,
        task_types: tuple[str, ...],
        used_profiles: set[str],
    ) -> WorkerRosterEntry | None:
        candidates = [
            entry
            for entry in self.worker_roster
            if entry.accepts_broadcast
            and entry.id not in used_profiles
            and entry.id not in _unavailable_workers()
        ]
        if not candidates:
            return None
        for task_type in task_types:
            for entry in candidates:
                if task_type in entry.preferred_task_types:
                    return entry
        return None

    # Deprecated compatibility method.
    def _select_swarm_entry(
        self,
        task_types: tuple[str, ...],
        used_profiles: set[str],
    ) -> WorkerRosterEntry | None:
        return self._select_worker_entry(task_types, used_profiles)

    def select_profile_for_role(
        self,
        role: str,
        is_premium_escalation: bool = False,
        is_module_swarm: bool = False,
        is_code_heavy: bool = False,
    ) -> PatternLane:
        role_policy = self.roles.get(role, RolePolicy(preferred_profile="default", fallback_profiles=[]))
        selected_profile = role_policy.preferred_profile
        fallback_profiles = tuple(role_policy.fallback_profiles)
        toolsets = tuple(role_policy.toolsets)
        model_policy = role_policy.model_policy

        if is_module_swarm:
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
        if is_module_swarm and is_disjoint and merge_conflict_risk <= 1 and risk_level.lower() in ("low", "normal"):
            return "low_cost_disjoint"
        return "low_cost_conservative"

    def capped_premium_code_lane_count(self, requested: int) -> int:
        return min(requested, self.escalation_policy.premium_code_cap)


def deprecated_env_warnings() -> tuple[str, ...]:
    warnings = []
    for env_name in (*DEPRECATED_ROSTER_ENVS, *DEPRECATED_UNAVAILABLE_ENVS):
        if os.getenv(env_name):
            warnings.append(f"Deprecated environment variable in use: {env_name}")
    return tuple(warnings)


def _default_worker_roster_path() -> Path | None:
    configured = os.getenv(PRIMARY_ROSTER_ENV)
    if not configured:
        for env_name in DEPRECATED_ROSTER_ENVS:
            configured = os.getenv(env_name)
            if configured:
                break
    if not configured:
        return None
    candidate = Path(configured).expanduser()
    return candidate if candidate.exists() else None


# Deprecated compatibility alias.
def _default_swarm_roster_path() -> Path | None:
    return _default_worker_roster_path()


def _unavailable_workers() -> set[str]:
    raw_values = [os.getenv(PRIMARY_UNAVAILABLE_ENV, "")]
    raw_values.extend(os.getenv(env_name, "") for env_name in DEPRECATED_UNAVAILABLE_ENVS)
    profiles: set[str] = set()
    for raw in raw_values:
        profiles.update(item.strip() for item in raw.split(",") if item.strip())
    return profiles


# Deprecated compatibility alias.
def _unhealthy_swarm_profiles() -> set[str]:
    return _unavailable_workers()


def _entry_task_types(raw_entry: dict[str, Any]) -> tuple[str, ...]:
    values = raw_entry.get("preferred_task_types", raw_entry.get("preferredTaskTypes", []))
    return tuple(str(item).lower() for item in values or [])


def _entry_accepts_broadcast(raw_entry: dict[str, Any]) -> bool:
    return bool(raw_entry.get("accepts_broadcast", raw_entry.get("acceptsBroadcast", True)))


def _load_worker_roster(path: Path) -> tuple[WorkerRosterEntry, ...]:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        entries = data.get("workers", [])
    else:
        entries = []
    roster: list[WorkerRosterEntry] = []
    for raw_entry in entries:
        if not isinstance(raw_entry, dict) or not raw_entry.get("id"):
            continue
        roster.append(
            WorkerRosterEntry(
                id=str(raw_entry["id"]),
                name=str(raw_entry.get("name", "")),
                role=str(raw_entry.get("role", "")),
                specialty=str(raw_entry.get("specialty", "")),
                model=str(raw_entry.get("model", "")),
                preferred_task_types=_entry_task_types(raw_entry),
                accepts_broadcast=_entry_accepts_broadcast(raw_entry),
            )
        )
    return tuple(roster)


# Deprecated compatibility alias.
def _load_swarm_roster(path: Path) -> tuple[WorkerRosterEntry, ...]:
    return _load_worker_roster(path)


def validate_roster_file(path: str | Path) -> RosterValidationResult:
    roster_path = Path(path).expanduser()
    errors: list[str] = []
    warnings: list[str] = []
    if not roster_path.exists():
        return RosterValidationResult(False, str(roster_path), errors=("roster path does not exist",))
    try:
        data = yaml.safe_load(roster_path.read_text()) or {}
    except Exception as exc:  # noqa: BLE001 - CLI should surface parse errors tersely.
        return RosterValidationResult(False, str(roster_path), errors=(f"failed to parse YAML: {exc}",))
    workers = data.get("workers") if isinstance(data, dict) else data
    if not isinstance(workers, list):
        return RosterValidationResult(False, str(roster_path), errors=("top-level workers list is required",))
    seen: set[str] = set()
    for index, worker in enumerate(workers, start=1):
        if not isinstance(worker, dict):
            errors.append(f"worker {index} must be a mapping")
            continue
        worker_id = str(worker.get("id", "")).strip()
        if not worker_id:
            errors.append(f"worker {index} missing id")
        elif worker_id in seen:
            errors.append(f"duplicate worker id: {worker_id}")
        else:
            seen.add(worker_id)
        roles = worker.get("roles", worker.get("role"))
        if isinstance(roles, str):
            roles_ok = bool(roles.strip())
        else:
            roles_ok = isinstance(roles, list) and any(str(role).strip() for role in roles)
        if not roles_ok:
            errors.append(f"worker {worker_id or index} must declare at least one role")
        capabilities = worker.get("capabilities", [])
        if capabilities is not None and not isinstance(capabilities, list):
            errors.append(f"worker {worker_id or index} capabilities must be a list")
        for key in ("url", "endpoint", "api_key", "token", "secret", "password"):
            if key in worker and "adapter" not in worker:
                warnings.append(f"worker {worker_id or index} includes adapter-specific key outside adapter: {key}")
    return RosterValidationResult(
        ok=not errors,
        path=str(roster_path),
        worker_count=len(workers),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


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
