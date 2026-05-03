from pathlib import Path

import pytest
import yaml
from worker_patterns.execution_plan import render_execution_plan
from worker_patterns.runtime_tool import worker_pattern_tool
from worker_patterns.schemas import PatternRequest
from worker_patterns.selector import select_worker_pattern

FIXTURE = Path("tests/fixtures/golden_routing_cases.yaml")


def _request(payload):
    review_required = bool(payload.get("review_required", True))
    if payload.get("no_review"):
        review_required = False
    return PatternRequest(
        objective=payload["objective"],
        scopes=tuple(payload.get("scopes", ())),
        dependencies=tuple(payload.get("dependencies", ())),
        risk_level=payload.get("risk_level", "normal"),
        review_required=review_required,
        tests_required=bool(payload.get("tests_required", False)),
        variants_requested=int(payload.get("variants_requested", 0)),
        durable=bool(payload.get("durable", False)),
        persistent_workers=bool(payload.get("persistent_workers", False)),
        recovery=bool(payload.get("recovery", False)),
        notes=tuple(payload.get("notes", ())),
    )


@pytest.mark.parametrize("case", yaml.safe_load(FIXTURE.read_text())["cases"], ids=lambda c: c["name"])
def test_golden_routing_case(case):
    plan = select_worker_pattern(_request(case["request"]))
    execution = render_execution_plan(plan).to_dict()
    tool_output = worker_pattern_tool({**case["request"], "output": "execution_plan"})

    assert plan.selection.selected_pattern.value == case["expected_pattern"]
    assert plan.runtime_mapping.primary_mechanism.value == case["expected_mechanism"]
    assert execution["mechanism"] == case["expected_mechanism"]
    assert plan.request.review_required is case["review_required"]
    assert [lane.role for lane in plan.lanes] == case["lane_roles"]
    assert any(case["safety_contains"] in note for note in execution["safety_notes"])
    assert execution["dry_run"] is True
    assert tool_output["dry_run"] is True
    assert tool_output["execution_plan"]["dry_run"] is True

    if expected_profile := case.get("expected_profile"):
        roles = set(case.get("module_swarm_execution_roles", ()))
        assert roles
        forbidden_profiles = tuple(case.get("forbidden_profiles", ()))
        expected_fallbacks = tuple(case.get("expected_fallback_profiles", ()))
        expected_disable_reasoning = case.get("expected_disable_reasoning")
        for lane in plan.lanes:
            if lane.role not in roles:
                continue
            assert lane.selected_profile == expected_profile
            assert lane.fallback_profiles == expected_fallbacks
            if expected_disable_reasoning is not None:
                assert lane.model_policy.disable_reasoning is expected_disable_reasoning
            serialized = " ".join((lane.selected_profile, *lane.fallback_profiles))
            assert not any(profile in serialized for profile in forbidden_profiles)
