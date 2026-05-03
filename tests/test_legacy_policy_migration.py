from pathlib import Path

import yaml

from hermes_worker_patterns.profile_policy import WorkerProfilesPolicy
from hermes_worker_patterns.schemas import PatternRequest, WorkerPattern
from hermes_worker_patterns.selector import select_worker_pattern

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "legacy_policy_expected_mappings.yaml"
POLICY = ROOT / "policies" / "worker_profiles.yaml"


def _fixture() -> dict:
    return yaml.safe_load(FIXTURE.read_text())


def _request(payload: dict) -> PatternRequest:
    return PatternRequest(
        objective=payload["objective"],
        scopes=tuple(payload.get("scopes", ())),
        dependencies=tuple(payload.get("dependencies", ())),
        risk_level=payload.get("risk_level", "normal"),
        review_required=payload.get("review_required", True),
        tests_required=payload.get("tests_required", False),
        variants_requested=payload.get("variants_requested", 0),
        durable=payload.get("durable", False),
        persistent_workers=payload.get("persistent_workers", False),
        recovery=payload.get("recovery", False),
        max_parallel_lanes=payload.get("max_parallel_lanes", 4),
        notes=tuple(payload.get("notes", ())),
    )


def _lanes_by_role(plan) -> dict[str, list]:
    lanes: dict[str, list] = {}
    for lane in plan.lanes:
        lanes.setdefault(lane.role, []).append(lane)
    return lanes


def test_legacy_role_profile_defaults_remain_mapped_to_hermes_profiles():
    data = _fixture()
    policy = WorkerProfilesPolicy.load_from_yaml(POLICY)

    for role, expected in data["role_profile_mappings"].items():
        lane = policy.select_profile_for_role(role)
        assert lane.selected_profile == expected["expected_profile"]
        assert lane.fallback_profiles == tuple(expected["expected_fallback_profiles"])
        assert lane.model_policy.disable_reasoning is expected["disable_reasoning"]


def test_legacy_escalation_and_cap_policy_remains_mapped():
    data = _fixture()["escalation_mappings"]
    policy = WorkerProfilesPolicy.load_from_yaml(POLICY)

    assert policy.escalation_policy.premium_escalation_profile == data["premium_escalation_profile"]
    assert policy.escalation_policy.module_swarm_default_profile == data["module_swarm_default_profile"]
    assert policy.escalation_policy.code_heavy_profile == data["code_heavy_profile"]
    assert policy.escalation_policy.premium_code_cap == data["premium_code_cap"]
    assert policy.capped_premium_code_lane_count(32) == data["premium_code_cap"]


def test_legacy_pattern_cases_map_to_current_selector_and_profiles():
    for legacy_name, case in _fixture()["pattern_mappings"].items():
        plan = select_worker_pattern(_request(case["request"]))
        lanes = _lanes_by_role(plan)

        assert plan.selection.selected_pattern == WorkerPattern(case["mapped_pattern"]), legacy_name
        if expected_overlay := case.get("expected_overlay"):
            assert WorkerPattern(expected_overlay) in plan.selection.overlays

        if expected_profile := case.get("expected_builder_profile"):
            assert lanes["builder"][0].selected_profile == expected_profile
        if expected_profile := case.get("expected_phase_worker_profile"):
            assert lanes["phase-worker"][0].selected_profile == expected_profile
        if expected_profile := case.get("expected_variant_profile"):
            assert lanes["variant-designer"][0].selected_profile == expected_profile
        if expected_profile := case.get("expected_curator_profile"):
            assert lanes["curator"][0].selected_profile == expected_profile
        if expected_profile := case.get("expected_recovery_profile"):
            assert lanes["recovery-worker"][0].selected_profile == expected_profile

        if expected_strategy := case.get("expected_scale_strategy"):
            assert plan.module_swarm_scale is not None
            assert plan.module_swarm_scale.profile_pool_strategy == expected_strategy
            assert plan.module_swarm_scale.max_active_lanes == case["expected_max_active_lanes"]
            for lane in plan.lanes:
                if lane.role in {"builder", "integrator", "reviewer"}:
                    assert lane.selected_profile == "worker-code-fast"
                    assert lane.fallback_profiles == ()
                    assert lane.model_policy.disable_reasoning is True
