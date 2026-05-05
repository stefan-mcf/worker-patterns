import json

import pytest

from worker_patterns.mcp_server import (
    render_execution_plan_bridge,
    select_worker_pattern_bridge,
)


def test_select_worker_pattern_bridge_returns_selection_only():
    result = select_worker_pattern_bridge(
        {
            "objective": "Refactor independent auth and billing modules",
            "scopes": ["auth", "billing"],
            "notes": ["disjoint scopes"],
        }
    )

    assert result["dry_run"] is True
    assert result["kind"] == "worker_pattern_selection"
    assert result["plan"]["selection"]["selected_pattern"] == "module-swarm"
    assert "execution_plan" not in result


def test_render_execution_plan_bridge_forces_dry_run_execution_plan():
    result = render_execution_plan_bridge(
        json.dumps(
            {
                "objective": "Keep persistent review and implementation lanes warm",
                "scope": "router",
                "persistent_workers": True,
                "output": "select",
            }
        )
    )

    assert result["dry_run"] is True
    assert result["kind"] == "worker_pattern_execution_plan"
    assert result["execution_plan"]["dry_run"] is True
    assert result["execution_plan"]["mechanism"] == "persistent_workers"
    assert result["execution_plan"]["commands"] == []
    assert result["execution_plan"]["worker_specs"]


def test_mcp_bridge_rejects_non_object_json():
    with pytest.raises(ValueError, match="JSON object"):
        select_worker_pattern_bridge("[]")
