import json

import pytest

from worker_patterns.adapter import dry_run_execution_plan
from worker_patterns.cli import main
from worker_patterns.execution_plan import render_execution_plan
from worker_patterns.schemas import PatternRequest
from worker_patterns.selector import select_worker_pattern


def test_execution_plan_renders_ephemeral_worker_specs_without_commands():
    plan = select_worker_pattern(
        PatternRequest(
            objective="Refactor auth and billing modules",
            scopes=("auth", "billing"),
        )
    )

    rendered = render_execution_plan(plan)

    assert rendered.dry_run is True
    assert rendered.mechanism == "ephemeral_workers"
    assert rendered.commands == ()
    assert rendered.task_graph_tasks == ()
    assert rendered.ephemeral_worker_tasks
    assert rendered.delegate_tasks == rendered.ephemeral_worker_tasks
    assert all(task["goal"] for task in rendered.ephemeral_worker_tasks)
    assert all(task["context"] for task in rendered.ephemeral_worker_tasks)
    assert all(task["toolsets"] for task in rendered.ephemeral_worker_tasks)
    assert any("Dry-run only" in note for note in rendered.safety_notes)


def test_execution_plan_renders_persistent_worker_specs_without_runtime_commands(tmp_path, monkeypatch):
    roster_path = tmp_path / "workers.yaml"
    roster_path.write_text(
        """
workers:
  - id: parked-worker
    name: Overflow
    role: Parked lane
    preferredTaskTypes: [implementation]
    acceptsBroadcast: false
  - id: builder-worker
    name: Builder
    role: Primary Builder
    preferredTaskTypes: [implementation, feature]
    acceptsBroadcast: true
  - id: review-worker
    name: Reviewer
    role: Reviewer / Merge Gate
    preferredTaskTypes: [review, qa, verification]
    acceptsBroadcast: true
"""
    )
    monkeypatch.setenv("WORKER_PATTERNS_ROSTER_PATH", str(roster_path))
    plan = select_worker_pattern(
        PatternRequest(
            objective="Implement persistent profile lanes",
            scopes=("router",),
            persistent_workers=True,
        )
    )

    rendered = render_execution_plan(plan)

    assert rendered.mechanism == "persistent_workers"
    assert rendered.commands == ()
    assert rendered.worker_specs
    assert rendered.worker_specs[0]["adapter_command"] is None
    assert "Map this logical worker profile" in rendered.worker_specs[0]["adapter_hint"]
    assert rendered.worker_specs[0]["worker_profile"] == "builder-worker"



def test_execution_plan_renders_kanban_task_graph_without_creating_tasks():
    plan = select_worker_pattern(
        PatternRequest(
            objective="Ship phased migration",
            dependencies=("schema", "api", "cutover"),
            durable=True,
        )
    )

    rendered = render_execution_plan(plan)

    assert rendered.mechanism == "task_graph"
    assert rendered.commands == ()
    assert rendered.ephemeral_worker_tasks == ()
    assert rendered.task_graph_tasks
    assert rendered.kanban_tasks == rendered.task_graph_tasks
    assert all(task["dry_run"] is True for task in rendered.task_graph_tasks)
    assert rendered.task_graph_tasks[1]["depends_on"] == ["lane-1-phase-worker"]


def test_adapter_exposes_dry_run_execution_plan_entrypoint():
    plan = select_worker_pattern(PatternRequest(objective="Fix one narrow bug"))

    rendered = dry_run_execution_plan(plan)

    assert rendered.dry_run is True
    assert rendered.mechanism == plan.runtime_mapping.primary_mechanism.value


def test_cli_render_execution_plan_json(capsys):
    assert (
        main(
            [
                "render-execution-plan",
                "Refactor auth and billing",
                "--scope",
                "auth",
                "--scope",
                "billing",
            ]
        )
        == 0
    )

    data = json.loads(capsys.readouterr().out)

    assert data["dry_run"] is True
    assert data["mechanism"] == "ephemeral_workers"
    assert data["ephemeral_worker_tasks"]
    assert data["delegate_tasks"] == data["ephemeral_worker_tasks"]
    assert data["commands"] == []


def test_cli_execute_flag_fails_closed_before_plan_rendering():
    with pytest.raises(SystemExit):
        main(["render-execution-plan", "Refactor auth", "--execute"])
