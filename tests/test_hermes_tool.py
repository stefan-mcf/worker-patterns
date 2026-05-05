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
    assert result["execution_plan"]["mechanism"] == "ephemeral_workers"
    assert result["execution_plan"]["ephemeral_worker_tasks"]
    assert result["execution_plan"]["delegate_tasks"] == result["execution_plan"]["ephemeral_worker_tasks"]


def test_worker_pattern_tool_accepts_dict_aliases_for_swarm_output():
    result = worker_pattern_tool(
        {
            "objective": "Maintain persistent router and review lanes",
            "scope": "router",
            "persistent_workers": True,
            "output": "persistent_workers",
        }
    )

    assert result["dry_run"] is True
    assert result["kind"] == "worker_pattern_persistent_worker_spec"
    assert result["persistent_workers"]["dry_run"] is True
    assert result["persistent_workers"]["workers"]
    assert result["persistent_workers"]["workers"][0]["adapter_command"] is None
    assert "Map this logical worker profile" in result["persistent_workers"]["workers"][0]["adapter_hint"]


def test_worker_pattern_tool_json_returns_json_text():
    text = worker_pattern_tool_json(
        {
            "objective": "Ship phased migration",
            "dependency": ["schema", "api", "cutover"],
            "durable": True,
            "output": "task_graph",
        }
    )

    result = json.loads(text)

    assert result["kind"] == "worker_pattern_task_graph_spec"
    assert result["task_graph"]["dry_run"] is True
    assert result["task_graph"]["tasks"][1]["depends_on"] == ["lane-1-phase-worker"]


def test_worker_pattern_tool_accepts_legacy_output_aliases():
    delegate = worker_pattern_tool({"objective": "Refactor two modules", "scope": ["a", "b"], "output": "delegate"})
    assert delegate["delegate"] == delegate["ephemeral_workers"]

    swarm = worker_pattern_tool({"objective": "Use persistent review lane", "persistent_workers": True, "output": "swarm"})
    assert swarm["swarm"] == swarm["persistent_workers"]

    kanban = worker_pattern_tool({"objective": "Ship ordered migration", "dependency": ["a", "b", "c"], "output": "kanban"})
    assert kanban["kanban"] == kanban["task_graph"]



def test_worker_pattern_tool_rejects_invalid_output():
    with pytest.raises(ValueError, match="output must be one of"):
        worker_pattern_tool({"objective": "Do work", "output": "execute"})


def test_worker_pattern_tool_rejects_non_object_json():
    with pytest.raises(ValueError, match="JSON object"):
        worker_pattern_tool("[]")
