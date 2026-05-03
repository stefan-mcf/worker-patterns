from __future__ import annotations

from pathlib import Path

import yaml

from hermes_worker_patterns import (
    ExecutionMechanism,
    PatternRequest,
    WorkerPattern,
    select_worker_pattern,
)
from hermes_worker_patterns.policy import SELECTOR_VERSION

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pattern_cases.yaml"
FIXTURES = yaml.safe_load(FIXTURE_PATH.read_text())["cases"]


def _request_from_fixture(payload: dict) -> PatternRequest:
    return PatternRequest(
        objective=payload["objective"],
        scopes=tuple(payload.get("scopes", [])),
        dependencies=tuple(payload.get("dependencies", [])),
        risk_level=payload.get("risk_level", "normal"),
        review_required=payload.get("review_required", True),
        tests_required=payload.get("tests_required", False),
        variants_requested=payload.get("variants_requested", 0),
        durable=payload.get("durable", False),
        persistent_workers=payload.get("persistent_workers", False),
        recovery=payload.get("recovery", False),
        max_parallel_lanes=payload.get("max_parallel_lanes", 4),
        notes=tuple(payload.get("notes", [])),
    )


def _pattern(value: str) -> WorkerPattern:
    return WorkerPattern(value)


def _mechanism(value: str) -> ExecutionMechanism:
    return ExecutionMechanism(value)


def test_fixture_cases_cover_base_patterns_and_overlay():
    for case in FIXTURES:
        plan = select_worker_pattern(_request_from_fixture(case["request"]))
        assert plan.selection.selected_pattern == _pattern(case["expected_pattern"])
        assert plan.selection.overlays == tuple(_pattern(item) for item in case["expected_overlays"])
        assert plan.hermes_mapping.primary_mechanism == _mechanism(case["expected_mechanism"])


def test_explicit_pattern_override_is_validated_and_applied():
    plan = select_worker_pattern(
        PatternRequest(
            "Fix one typo in README",
            notes=(
                "pattern:module-swarm",
                "pattern_override_requested_by:stefan",
                "pattern_override_reason:exercise explicit policy control",
            ),
        )
    )
    assert plan.selection.selected_pattern == WorkerPattern.MODULE_SWARM
    assert plan.selection.selection_source == "validated_explicit_structured_override"
    assert plan.selection.override == WorkerPattern.MODULE_SWARM.value
    assert plan.selection.override_requested_by == "stefan"
    assert plan.selection.override_reason == "exercise explicit policy control"


def test_invalid_pattern_override_is_reported_and_ignored():
    plan = select_worker_pattern(PatternRequest("Fix one typo in README", notes=("pattern:not-a-real-pattern",)))
    assert plan.selection.selected_pattern == WorkerPattern.SEQUENTIAL
    assert plan.selection.invalid_override_reason == "unrecognized pattern override: not-a-real-pattern"
    assert plan.selection.selection_source in {"policy_scoring", "policy_fallback", "policy_scoring_close_score_prefer_simpler"}


def test_close_scores_prefer_simpler_pattern():
    plan = select_worker_pattern(PatternRequest("simple task", dependencies=("schema",), review_required=False))
    assert plan.selection.selected_pattern == WorkerPattern.SEQUENTIAL
    assert plan.selection.selection_source == "policy_scoring_close_score_prefer_simpler"
    assert plan.selection.scores[WorkerPattern.SEQUENTIAL.value] == plan.selection.scores[WorkerPattern.PHASED_ASSEMBLY.value]


def test_selection_metadata_is_auditable():
    plan = select_worker_pattern(PatternRequest("Refactor auth and billing modules", scopes=("auth", "billing"), tests_required=True))
    assert plan.selection.selector_version == SELECTOR_VERSION
    assert plan.selection.dimensions
    assert plan.selection.scores
    assert isinstance(plan.selection.score_adjustments, dict)
    assert isinstance(plan.selection.matched_signals, tuple)
    assert plan.selection.selection_source
