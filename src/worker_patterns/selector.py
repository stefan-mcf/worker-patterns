from __future__ import annotations

import yaml

from .adapter import adapt_to_runtime
from .policy import (
    BASE_PATTERNS,
    CLOSE_SCORE_MARGIN,
    DEFAULT_PROOF_EXPECTATIONS,
    OVERRIDE_PREFIX,
    OVERRIDE_REASON_PREFIX,
    OVERRIDE_REQUESTED_BY_PREFIX,
    PATTERN_ALIASES,
    PATTERN_DIMENSIONS,
    PATTERN_KEYWORDS,
    PATTERN_SCORE_FORMULAS,
    SELECTOR_VERSION,
    SIMPLER_PATTERN_ORDER,
    _read_policy_text,
)
from .profile_policy import WorkerProfilesPolicy
from .schemas import (
    ModuleSwarmScalePolicy,
    PatternLane,
    PatternPlan,
    PatternRequest,
    PatternSelection,
    WorkerPattern,
)


def _blob(request: PatternRequest) -> str:
    filtered_notes = [note for note in request.notes if not _is_override_note(note)]
    return " ".join((request.objective, " ".join(request.scopes), " ".join(request.dependencies), " ".join(filtered_notes))).lower()


def _is_override_note(note: str) -> bool:
    lowered = note.lower()
    return lowered.startswith(OVERRIDE_PREFIX.lower()) or lowered.startswith(OVERRIDE_REQUESTED_BY_PREFIX.lower()) or lowered.startswith(OVERRIDE_REASON_PREFIX.lower())


def _signals(blob: str) -> tuple[str, ...]:
    found: list[str] = []
    for keywords in PATTERN_KEYWORDS.values():
        for keyword in keywords:
            if keyword in blob:
                found.append(keyword)
    return tuple(sorted(set(found)))


def _parse_override(request: PatternRequest) -> dict[str, str | bool]:
    override = ""
    requested_by = ""
    reason = ""
    for note in request.notes:
        lowered = note.lower()
        if lowered.startswith(OVERRIDE_PREFIX.lower()):
            override = note.split(":", 1)[1].strip()
        elif lowered.startswith(OVERRIDE_REQUESTED_BY_PREFIX.lower()):
            requested_by = note.split(":", 1)[1].strip()
        elif lowered.startswith(OVERRIDE_REASON_PREFIX.lower()):
            reason = note.split(":", 1)[1].strip()

    invalid_reason = ""
    normalized = ""
    if override:
        try:
            normalized = _normalize_pattern_name(override).value
        except ValueError:
            invalid_reason = f"unrecognized pattern override: {override}"
    return {
        "override": normalized,
        "override_requested_by": requested_by,
        "override_reason": reason,
        "is_valid": bool(normalized) and not invalid_reason,
        "invalid_reason": invalid_reason,
    }


def _normalize_pattern_name(raw: str) -> WorkerPattern:
    cleaned = raw.strip().lower()
    if cleaned in PATTERN_ALIASES:
        return PATTERN_ALIASES[cleaned]
    return WorkerPattern(cleaned)


def infer_dimensions(request: PatternRequest) -> dict[str, int]:
    blob = _blob(request)
    dims = {name: 0 for name in PATTERN_DIMENSIONS}
    dims["workpiece_singularity"] = 1
    dims["verification_criticality"] = 1 if request.review_required else 0

    if request.variants_requested > 1 or any(k in blob for k in PATTERN_KEYWORDS[WorkerPattern.BLUEPRINT_FANOUT]):
        dims["uncertainty_of_solution"] = 3
    if request.dependencies or any(k in blob for k in PATTERN_KEYWORDS[WorkerPattern.PHASED_ASSEMBLY]):
        dims["dependency_depth"] = min(3, max(1, len(request.dependencies))) if request.dependencies else 3
    if len(request.scopes) > 1 or any(k in blob for k in PATTERN_KEYWORDS[WorkerPattern.MODULE_SWARM]):
        dims["module_separability"] = 3
        dims["workpiece_singularity"] = 0
    if request.review_required or request.tests_required or any(k in blob for k in PATTERN_KEYWORDS[WorkerPattern.TWIN_INSPECTION]):
        dims["verification_criticality"] = 3
    if (
        "no shared file" not in blob
        and any(token in blob for token in ("shared file", "same file", "merge", "collision", "ambiguous ownership"))
    ):
        dims["merge_conflict_risk"] = 3
    elif dims["module_separability"] >= 2 and "disjoint" not in blob:
        dims["merge_conflict_risk"] = 1
    if request.recovery or any(k in blob for k in PATTERN_KEYWORDS[WorkerPattern.RECOVERY_LANE]):
        dims["workpiece_singularity"] = 3
        dims["module_separability"] = min(dims["module_separability"], 1)
        dims["merge_conflict_risk"] = max(dims["merge_conflict_risk"], 2)
    if request.risk_level.lower() in {"high", "critical"} or any(k in blob for k in PATTERN_KEYWORDS[WorkerPattern.BRIDGE_LANE]):
        dims["verification_criticality"] = max(dims["verification_criticality"], 2 if request.risk_level.lower() == "high" else 3)
        dims["merge_conflict_risk"] = max(dims["merge_conflict_risk"], 1 if request.risk_level.lower() == "high" else 2)
    return dims


def _score_pattern(pattern: WorkerPattern, dimensions: dict[str, int]) -> int:
    formula = PATTERN_SCORE_FORMULAS.get(pattern, {})
    score = 0
    for dimension, weight in (formula.get("positive") or {}).items():
        score += int(weight) * int(dimensions.get(dimension, 0))
    for dimension, weight in (formula.get("negative") or {}).items():
        score -= int(weight) * int(dimensions.get(dimension, 0))
    return score


def _score_adjustments(blob: str) -> tuple[tuple[str, ...], dict[str, int]]:
    matched: list[str] = []
    adjustments: dict[str, int] = {}
    for pattern, keywords in PATTERN_KEYWORDS.items():
        hits = [keyword for keyword in keywords if keyword in blob]
        if not hits:
            continue
        matched.extend(hits)
        adjustments[pattern.value] = min(2, len(hits))
    return tuple(sorted(set(matched))), adjustments


def _base_selection(dimensions: dict[str, int], blob: str) -> tuple[WorkerPattern, str, dict[str, int], dict[str, int], tuple[str, ...], str]:
    matched_signals, score_adjustments = _score_adjustments(blob)
    base_scores = {pattern.value: _score_pattern(pattern, dimensions) for pattern in BASE_PATTERNS}
    final_scores = {pattern_id: base_scores[pattern_id] + score_adjustments.get(pattern_id, 0) for pattern_id in base_scores}
    ranked = sorted(final_scores.items(), key=lambda item: (-item[1], item[0]))
    best_pattern_name, best_score = ranked[0]
    best_pattern = WorkerPattern(best_pattern_name)
    selection_source = "policy_scoring" if best_score > 0 else "policy_fallback"
    if len(ranked) > 1:
        runner_up_name, runner_up_score = ranked[1]
        runner_up = WorkerPattern(runner_up_name)
        simpler = _prefer_simpler_pattern(best_pattern, runner_up)
        if simpler and 0 <= best_score - runner_up_score <= CLOSE_SCORE_MARGIN and simpler != best_pattern:
            best_pattern = simpler
            selection_source = "policy_scoring_close_score_prefer_simpler"
    return best_pattern, _reason_for(best_pattern), final_scores, score_adjustments, matched_signals, selection_source


def _prefer_simpler_pattern(first: WorkerPattern, second: WorkerPattern) -> WorkerPattern | None:
    eligible = {
        WorkerPattern.SEQUENTIAL,
        WorkerPattern.MODULE_SWARM,
        WorkerPattern.PHASED_ASSEMBLY,
        WorkerPattern.BLUEPRINT_FANOUT,
    }
    if first not in eligible or second not in eligible:
        return None
    order = {pattern: index for index, pattern in enumerate(SIMPLER_PATTERN_ORDER)}
    return first if order.get(first, 999) <= order.get(second, 999) else second


def _is_code_heavy_request(request: PatternRequest, base: WorkerPattern) -> bool:
    blob = _blob(request)
    if base in {WorkerPattern.PHASED_ASSEMBLY, WorkerPattern.SEQUENTIAL}:
        return "code" in request.scopes or "code" in blob
    return any(
        token in blob
        for token in (
            "code-heavy",
            "premium_code",
            "spark",
            "code heavy",
            "implementation-heavy",
        )
    )


def _has_disjoint_scope_signal(request: PatternRequest) -> bool:
    blob = _blob(request)
    return any(
        token in blob
        for token in (
            "disjoint",
            "separate directories",
            "separate directory",
            "no shared files",
            "own directory",
        )
    )


def _reason_for(base: WorkerPattern) -> str:
    reasons = {
        WorkerPattern.BRIDGE_LANE: "critical recovery or canonical landing requires bridge lane",
        WorkerPattern.RECOVERY_LANE: "recovery, blocked, or stale work requires a narrow repair lane",
        WorkerPattern.BLUEPRINT_FANOUT: "task asks for alternatives, variants, or curation",
        WorkerPattern.PHASED_ASSEMBLY: "dependency depth suggests ordered waves",
        WorkerPattern.MODULE_SWARM: "multiple scopes or module separability supports parallel lanes",
        WorkerPattern.SEQUENTIAL: "single bounded workpiece has limited parallel benefit",
    }
    return reasons[base]


def _explicit_base_pattern(request: PatternRequest, dimensions: dict[str, int]) -> WorkerPattern | None:
    if request.recovery and request.risk_level.lower() == "critical":
        return WorkerPattern.BRIDGE_LANE
    if request.recovery:
        return WorkerPattern.RECOVERY_LANE
    if dimensions["uncertainty_of_solution"] >= 3:
        return WorkerPattern.BLUEPRINT_FANOUT
    return None


def _lanes_for(
    request: PatternRequest,
    base: WorkerPattern,
    overlays: tuple[WorkerPattern, ...],
    profile_policy: WorkerProfilesPolicy,  # New parameter
    dimensions: dict[str, int] | None = None,  # Added for scale policy
) -> tuple[PatternLane, ...]:
    lanes: list[PatternLane] = []
    is_premium_escalation = request.risk_level.lower() == "critical"
    is_module_swarm = base == WorkerPattern.MODULE_SWARM
    is_code_heavy = _is_code_heavy_request(request, base)
    dims = dimensions or {}

    if base == WorkerPattern.MODULE_SWARM:
        scopes = request.scopes or ("workstream-a", "workstream-b")
        scale = profile_policy.recommend_module_swarm_scale(
            requested_lane_count=len(scopes),
            max_parallel_lanes=request.max_parallel_lanes,
            disjoint_scopes=_has_disjoint_scope_signal(request),
            merge_conflict_risk=dims.get("merge_conflict_risk", 0),
            risk_level=request.risk_level,
            code_heavy=is_code_heavy,
            review_required=request.review_required,
            tests_required=request.tests_required,
        )

        worker_profile = profile_policy.select_profile_for_role(
            "code-worker",
            is_premium_escalation=False,
            is_module_swarm=True,
            is_code_heavy=False,
        )
        for scope in scopes:
            lanes.append(
                PatternLane(
                    role="builder",
                    count=1,
                    scope=(scope,),
                    purpose="parallel scoped implementation lane; execute in safe waves, not all at once",
                    runtime_hint=f"wave-limited {scale.profile_pool_strategy}; max active builders {scale.max_active_lanes}",
                    selected_profile=worker_profile.selected_profile,
                    fallback_profiles=worker_profile.fallback_profiles,
                    toolsets=worker_profile.toolsets,
                    model_policy=worker_profile.model_policy,
                )
            )

        integrator_profile_lane = profile_policy.select_profile_for_role(
            "integrator-worker",
            is_premium_escalation=False,
            is_module_swarm=True,
            is_code_heavy=False,
        )
        cadence = "after each wave" if scale.integrator_per_wave else "after all waves"
        lanes.append(
            PatternLane(
                role="integrator",
                count=scale.waves_required if scale.integrator_per_wave else 1,
                scope=scopes,
                purpose=f"merge/check lane outputs {cadence}",
                runtime_hint="current-session lane or goal-style continuation",
                selected_profile=integrator_profile_lane.selected_profile,
                fallback_profiles=integrator_profile_lane.fallback_profiles,
                toolsets=integrator_profile_lane.toolsets,
                model_policy=integrator_profile_lane.model_policy,
            )
        )
    elif base == WorkerPattern.BLUEPRINT_FANOUT:
        count = min(max(request.variants_requested or 2, 2), request.max_parallel_lanes)
        for i in range(count):
            designer_profile_lane = profile_policy.select_profile_for_role(
                "planner-worker",
                is_premium_escalation=is_premium_escalation,
                is_module_swarm=is_module_swarm,
                is_code_heavy=is_code_heavy,
            )
            lanes.append(
                PatternLane(
                    role="variant-designer",
                    count=1,
                    scope=(),
                    purpose=f"produce alternative {i + 1}",
                    runtime_hint="delegate_task batch",
                    selected_profile=designer_profile_lane.selected_profile,
                    fallback_profiles=designer_profile_lane.fallback_profiles,
                    toolsets=designer_profile_lane.toolsets,
                    model_policy=designer_profile_lane.model_policy,
                )
            )
        curator_profile_lane = profile_policy.select_profile_for_role(
            "review-worker",
            is_premium_escalation=is_premium_escalation,
            is_module_swarm=is_module_swarm,
            is_code_heavy=is_code_heavy,
        )
        lanes.append(
            PatternLane(
                role="curator",
                count=1,
                scope=(),
                purpose="compare variants and select/merge",
                runtime_hint="current-session lane",
                selected_profile=curator_profile_lane.selected_profile,
                fallback_profiles=curator_profile_lane.fallback_profiles,
                toolsets=curator_profile_lane.toolsets,
                model_policy=curator_profile_lane.model_policy,
            )
        )
    elif base == WorkerPattern.PHASED_ASSEMBLY:
        deps = request.dependencies or ("phase-1", "phase-2")
        for dep in deps:
            phase_worker_profile_lane = profile_policy.select_profile_for_role(
                "code-worker",
                is_premium_escalation=is_premium_escalation,
                is_module_swarm=is_module_swarm,
                is_code_heavy=is_code_heavy,
            )
            lanes.append(
                PatternLane(
                    role="phase-worker",
                    count=1,
                    scope=(dep,),
                    purpose="complete dependency wave item",
                    runtime_hint="Kanban child task or /goal step",
                    selected_profile=phase_worker_profile_lane.selected_profile,
                    fallback_profiles=phase_worker_profile_lane.fallback_profiles,
                    toolsets=phase_worker_profile_lane.toolsets,
                    model_policy=phase_worker_profile_lane.model_policy,
                )
            )
    elif base in {WorkerPattern.RECOVERY_LANE, WorkerPattern.BRIDGE_LANE}:
        recovery_profile_lane = profile_policy.select_profile_for_role(
            "recovery-worker",
            is_premium_escalation=is_premium_escalation,
            is_module_swarm=is_module_swarm,
            is_code_heavy=is_code_heavy,
        )
        lanes.append(
            PatternLane(
                role="recovery-worker",
                count=1,
                scope=request.scopes,
                purpose="narrow repair/resume lane",
                runtime_hint="single strong worker/profile",
                selected_profile=recovery_profile_lane.selected_profile,
                fallback_profiles=recovery_profile_lane.fallback_profiles,
                toolsets=recovery_profile_lane.toolsets,
                model_policy=recovery_profile_lane.model_policy,
            )
        )
    else: # SEQUENTIAL
        builder_profile_lane = profile_policy.select_profile_for_role(
            "code-worker",
            is_premium_escalation=is_premium_escalation,
            is_module_swarm=is_module_swarm,
            is_code_heavy=is_code_heavy,
        )
        lanes.append(
            PatternLane(
                role="builder",
                count=1,
                scope=request.scopes,
                purpose="single bounded implementation lane",
                runtime_hint="direct runtime turn or goal-style continuation",
                selected_profile=builder_profile_lane.selected_profile,
                fallback_profiles=builder_profile_lane.fallback_profiles,
                toolsets=builder_profile_lane.toolsets,
                model_policy=builder_profile_lane.model_policy,
            )
        )

    if WorkerPattern.TWIN_INSPECTION in overlays:
        reviewer_profile_lane = profile_policy.select_profile_for_role(
            "review-worker",
            is_premium_escalation=False if is_module_swarm else is_premium_escalation,
            is_module_swarm=is_module_swarm,
            is_code_heavy=False if is_module_swarm else is_code_heavy,
        )
        lanes.append(
            PatternLane(
                role="reviewer",
                count=1,
                scope=request.scopes,
                purpose="independent review/test verification",
                runtime_hint="delegate_task reviewer or swarm review profile",
                selected_profile=reviewer_profile_lane.selected_profile,
                fallback_profiles=reviewer_profile_lane.fallback_profiles,
                toolsets=reviewer_profile_lane.toolsets,
                model_policy=reviewer_profile_lane.model_policy,
            )
        )
    return tuple(lanes)


def _proof_expectations(base: WorkerPattern, overlays: tuple[WorkerPattern, ...], request: PatternRequest) -> tuple[str, ...]:
    expectations: list[str] = list(DEFAULT_PROOF_EXPECTATIONS[base])
    for overlay in overlays:
        expectations.extend(DEFAULT_PROOF_EXPECTATIONS[overlay])
    if request.tests_required:
        expectations.append("test command/output or explicit reason tests were not run")
    if request.scopes:
        expectations.append("final summary names touched scopes: " + ", ".join(request.scopes))
    return tuple(dict.fromkeys(expectations))



def _safety_notes(request: PatternRequest) -> tuple[str, ...]:
    notes = ["Runtimes execute; this package only selects/adapts worker patterns."]
    blob = _blob(request)
    if any(token in blob for token in ("browser", "website", "web app", "playwright", "selenium", "browser harness", "browser use")):
        notes.append(
            "Browser-capable route only: prefer Browser Harness/Browser Use in a later explicitly approved execution flow; this package must not execute browser actions or use credentials."
        )
    if any(token in blob for token in ("security", "credential", "secret", "token", "blocked", "sensitive")) or request.risk_level.lower() in {"high", "critical"}:
        notes.append("Safety-sensitive work requires explicit review and dry-run inspection before any execution.")
    if any(token in blob for token in ("package", "release", "publish", "pypi", "distribution")):
        notes.append("Packaging/release routes are planning-only here; publishing or remote pushes require explicit human approval.")
    return tuple(dict.fromkeys(notes))

def select_worker_pattern(request: PatternRequest) -> PatternPlan:
    profile_policy = WorkerProfilesPolicy.load_from_mapping(yaml.safe_load(_read_policy_text("worker_profiles.yaml")))

    blob = _blob(request)
    dimensions = infer_dimensions(request)
    override_info = _parse_override(request)
    matched_signals, score_adjustments = _score_adjustments(blob)
    scores = {pattern.value: _score_pattern(pattern, dimensions) + score_adjustments.get(pattern.value, 0) for pattern in BASE_PATTERNS}

    if override_info["is_valid"]:
        base = WorkerPattern(str(override_info["override"]))
        reason = f"validated explicit override selected {base.value}"
        selection_source = "validated_explicit_structured_override"
    else:
        explicit_base = _explicit_base_pattern(request, dimensions)
        if explicit_base is not None:
            base = explicit_base
            reason = _reason_for(base)
            selection_source = "policy_scoring"
        else:
            base, reason, scores, score_adjustments, matched_signals, selection_source = _base_selection(dimensions, blob)

    overlays: list[WorkerPattern] = []
    if request.review_required and base != WorkerPattern.TWIN_INSPECTION:
        overlays.append(WorkerPattern.TWIN_INSPECTION)

    lanes = _lanes_for(request, base, tuple(overlays), profile_policy, dimensions=dimensions)
    swarm_roster_notes: tuple[str, ...] = ()
    if request.persistent_workers:
        lanes, swarm_roster_notes = profile_policy.apply_canonical_swarm_roster(lanes)

    module_swarm_scale = None
    if base == WorkerPattern.MODULE_SWARM:
        scopes = request.scopes or ("workstream-a", "workstream-b")
        recommendation = profile_policy.recommend_module_swarm_scale(
            requested_lane_count=len(scopes),
            max_parallel_lanes=request.max_parallel_lanes,
            disjoint_scopes=_has_disjoint_scope_signal(request),
            merge_conflict_risk=dimensions.get("merge_conflict_risk", 0),
            risk_level=request.risk_level,
            code_heavy=_is_code_heavy_request(request, base),
            review_required=request.review_required,
            tests_required=request.tests_required,
        )
        module_swarm_scale = ModuleSwarmScalePolicy(
            requested_lane_count=recommendation.requested_lane_count,
            max_active_lanes=recommendation.max_active_lanes,
            waves_required=recommendation.waves_required,
            wave_size=recommendation.wave_size,
            profile_pool_strategy=recommendation.profile_pool_strategy,
            integrator_per_wave=recommendation.integrator_per_wave,
        )

    selection = PatternSelection(
        selected_pattern=base,
        overlays=tuple(overlays),
        reason=reason,
        dimensions=dimensions,
        matched_signals=matched_signals,
        scores=scores,
        score_adjustments=score_adjustments,
        selection_source=selection_source,
        selector_version=SELECTOR_VERSION,
        override=str(override_info["override"]),
        override_requested_by=str(override_info["override_requested_by"]),
        override_reason=str(override_info["override_reason"]),
        invalid_override_reason=str(override_info["invalid_reason"]),
    )
    return PatternPlan(
        request=request,
        selection=selection,
        lanes=lanes,
        runtime_mapping=adapt_to_runtime(request, selection, lanes),
        proof_expectations=_proof_expectations(base, tuple(overlays), request),
        safety_notes=tuple(dict.fromkeys((*_safety_notes(request), *swarm_roster_notes))),
        role_rules={role_name: role_policy for role_name, role_policy in profile_policy.roles.items()},
        profile_mapping={role_name: role_policy.preferred_profile for role_name, role_policy in profile_policy.roles.items()},
        module_swarm_scale=module_swarm_scale,
    )
