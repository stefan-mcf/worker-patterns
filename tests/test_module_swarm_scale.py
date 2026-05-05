from pathlib import Path

import yaml

from worker_patterns.schemas import ExecutionMechanism, PatternRequest, WorkerPattern
from worker_patterns.selector import select_worker_pattern

FIXTURE = Path(__file__).parent / "fixtures" / "module_swarm_32_lane_case.yaml"
FORBIDDEN_PROFILE_TOKENS = ("premium_code", "gpt", "default")


def _case(case_name: str) -> dict:
    data = yaml.safe_load(FIXTURE.read_text())
    return next(item for item in data["cases"] if item["name"] == case_name)


def _request_from_fixture(case_name: str) -> PatternRequest:
    case = _case(case_name)
    request = case["request"]
    return PatternRequest(
        objective=request["objective"],
        scopes=tuple(request["scopes"]),
        max_parallel_lanes=request["max_parallel_lanes"],
        risk_level=request["risk_level"],
        review_required=request["review_required"],
        tests_required=request["tests_required"],
        notes=tuple(request.get("notes", ())),
    )


def _assert_module_swarm_low_cost_only(plan):
    execution_roles = {"builder", "integrator", "reviewer"}
    lanes = [lane for lane in plan.lanes if lane.role in execution_roles]
    assert lanes
    for lane in lanes:
        assert lane.selected_profile == "worker-code-fast"
        assert lane.fallback_profiles == ()
        assert lane.model_policy.disable_reasoning is True
        serialized = " ".join((lane.selected_profile, *lane.fallback_profiles)).lower()
        assert not any(token in serialized for token in FORBIDDEN_PROFILE_TOKENS)


def _assert_fixture_profile_expectations(plan, case_name: str):
    case = _case(case_name)
    expected_profile = case["expected_profile"]
    forbidden_profiles = tuple(case["forbidden_profiles"])
    expected_disable_reasoning = case["expected_disable_reasoning"]
    for lane in plan.lanes:
        if lane.role not in {"builder", "integrator", "reviewer"}:
            continue
        assert lane.selected_profile == expected_profile
        assert lane.model_policy.disable_reasoning is expected_disable_reasoning
        serialized = " ".join((lane.selected_profile, *lane.fallback_profiles))
        assert not any(profile in serialized for profile in forbidden_profiles)


def test_32_lane_disjoint_swarm_becomes_safe_waves():
    plan = select_worker_pattern(
        _request_from_fixture("module_swarm_32_lane_disjoint_cheap")
    )

    builders = [lane for lane in plan.lanes if lane.role == "builder"]
    integrators = [lane for lane in plan.lanes if lane.role == "integrator"]

    assert plan.selection.selected_pattern == WorkerPattern.MODULE_SWARM
    assert plan.runtime_mapping.primary_mechanism == ExecutionMechanism.EPHEMERAL_WORKERS
    assert plan.module_swarm_scale is not None
    assert plan.module_swarm_scale.requested_lane_count == 32
    assert plan.module_swarm_scale.max_active_lanes == 8
    assert plan.module_swarm_scale.wave_size == 8
    assert plan.module_swarm_scale.waves_required == 4
    assert plan.module_swarm_scale.profile_pool_strategy == "low_cost_disjoint"
    assert plan.module_swarm_scale.integrator_per_wave is False
    assert len(builders) == 32
    assert tuple(lane.scope[0] for lane in builders) == plan.request.scopes
    assert len(integrators) == 1
    assert integrators[0].count == 1
    _assert_module_swarm_low_cost_only(plan)
    _assert_fixture_profile_expectations(plan, "module_swarm_32_lane_disjoint_cheap")


def test_32_lane_conflict_swarm_uses_conservative_waves_and_integrates_per_wave():
    plan = select_worker_pattern(_request_from_fixture("module_swarm_32_lane_high_risk"))

    assert plan.module_swarm_scale is not None
    assert plan.module_swarm_scale.requested_lane_count == 32
    assert plan.module_swarm_scale.max_active_lanes == 4
    assert plan.module_swarm_scale.wave_size == 4
    assert plan.module_swarm_scale.waves_required == 8
    assert plan.module_swarm_scale.profile_pool_strategy == "low_cost_conservative"
    assert plan.module_swarm_scale.integrator_per_wave is True
    integrators = [lane for lane in plan.lanes if lane.role == "integrator"]
    assert len(integrators) == 1
    assert integrators[0].count == 8
    _assert_module_swarm_low_cost_only(plan)
    _assert_fixture_profile_expectations(plan, "module_swarm_32_lane_high_risk")


def test_code_heavy_module_swarm_still_uses_low_cost_profile_not_premium_code():
    scopes = tuple(f"module-{index:02d}" for index in range(1, 33))
    plan = select_worker_pattern(
        PatternRequest(
            objective="Code-heavy implementation across disjoint modules",
            scopes=scopes,
            max_parallel_lanes=8,
            review_required=False,
            tests_required=False,
            notes=("disjoint scopes; code-heavy; module-swarm remains the default low-cost parallel profile only",),
        )
    )

    assert plan.selection.selected_pattern == WorkerPattern.MODULE_SWARM
    assert plan.module_swarm_scale is not None
    assert plan.module_swarm_scale.requested_lane_count == 32
    assert plan.module_swarm_scale.max_active_lanes == 8
    assert plan.module_swarm_scale.profile_pool_strategy == "low_cost_disjoint"
    _assert_module_swarm_low_cost_only(plan)


def test_non_module_swarm_has_no_module_swarm_scale_policy():
    plan = select_worker_pattern(PatternRequest(objective="Do one bounded code change"))

    assert plan.selection.selected_pattern != WorkerPattern.MODULE_SWARM
    assert plan.module_swarm_scale is None
