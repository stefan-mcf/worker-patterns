from pathlib import Path

from hermes_worker_patterns import PatternRequest, select_worker_pattern
from hermes_worker_patterns.adapter import adapt_to_hermes
from hermes_worker_patterns.schemas import HermesMapping
from worker_patterns.adapter import adapt_to_runtime
from worker_patterns.schemas import RuntimeMapping


def test_former_hermes_import_path_remains_compatibility_shim():
    plan = select_worker_pattern(PatternRequest(objective="small docs update"))

    assert plan.selection.selected_pattern.value == "sequential"
    assert adapt_to_hermes is adapt_to_runtime
    assert HermesMapping is RuntimeMapping


def test_compatibility_policy_data_stays_synchronized():
    canonical = Path("src/worker_patterns/policies")
    shim = Path("src/hermes_worker_patterns/policies")

    for policy in ["pattern_rules.yaml", "worker_profiles.yaml"]:
        assert (canonical / policy).read_text() == (shim / policy).read_text()
