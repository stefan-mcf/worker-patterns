import json

import pytest
from worker_patterns.runtime_tool import worker_pattern_tool, worker_pattern_tool_json


def test_worker_pattern_tool_accepts_json_string_and_returns_execution_plan():
    result = worker_pattern_tool(
        json.dumps(
            {
                "objective": "Refactor auth and billing modules",
                "scopes": ["auth", "billing"],
                "tests_required": True,
            }
        )
    )

    assert result["dry_run"] is True
    assert result["kind"] == "worker_pattern_execution_plan"
    assert result["plan"]["selection"]["selected_pattern"] == "module-swarm"
    assert result["execution_plan"]["mechanism"] == "delegate_task"
    assert result["execution_plan"]["delegate_tasks"]


def test_worker_pattern_tool_accepts_dict_aliases_for_swarm_output():
    result = worker_pattern_tool(
        {
            "objective": "Maintain persistent router and review lanes",
            "scope": "router",
            "persistent_workers": True,
            "output": "swarm",
        }
    )

    assert result["dry_run"] is True
    assert result["kind"] == "worker_pattern_swarm_spec"
    assert result["swarm"]["dry_run"] is True
    assert result["swarm"]["workers"]
    assert result["swarm"]["workers"][0]["command_argv"][:2] == ["hermes", "--profile"]


def test_worker_pattern_tool_json_returns_json_text():
    text = worker_pattern_tool_json(
        {
            "objective": "Ship phased migration",
            "dependency": ["schema", "api", "cutover"],
            "durable": True,
            "output": "kanban",
        }
    )

    result = json.loads(text)

    assert result["kind"] == "worker_pattern_kanban_spec"
    assert result["kanban"]["dry_run"] is True
    assert result["kanban"]["tasks"][1]["depends_on"] == ["lane-1-phase-worker"]


def test_worker_pattern_tool_rejects_invalid_output():
    with pytest.raises(ValueError, match="output must be one of"):
        worker_pattern_tool({"objective": "Do work", "output": "execute"})


def test_worker_pattern_tool_rejects_non_object_json():
    with pytest.raises(ValueError, match="JSON object"):
        worker_pattern_tool("[]")
