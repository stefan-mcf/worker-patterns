import json

import pytest

from hermes_worker_patterns.adapter import dry_run_execution_plan
from hermes_worker_patterns.cli import main
from hermes_worker_patterns.execution_plan import render_execution_plan
from hermes_worker_patterns.schemas import PatternRequest
from hermes_worker_patterns.selector import select_worker_pattern


def test_execution_plan_renders_delegate_task_specs_without_commands():
    plan = select_worker_pattern(
        PatternRequest(
            objective="Refactor auth and billing modules",
            scopes=("auth", "billing"),
        )
    )

    rendered = render_execution_plan(plan)

    assert rendered.dry_run is True
    assert rendered.mechanism == "delegate_task"
    assert rendered.commands == ()
    assert rendered.kanban_tasks == ()
    assert rendered.delegate_tasks
    assert all(task["goal"] for task in rendered.delegate_tasks)
    assert all(task["context"] for task in rendered.delegate_tasks)
    assert all(task["toolsets"] for task in rendered.delegate_tasks)
    assert any("Dry-run only" in note for note in rendered.safety_notes)


def test_execution_plan_renders_swarm_profile_commands_as_argv_arrays(tmp_path, monkeypatch):
    roster_path = tmp_path / "swarm.yaml"
    roster_path.write_text(
        """
workers:
  - id: swarm1
    name: Overflow
    role: Parked lane
    preferredTaskTypes: [implementation]
    acceptsBroadcast: false
  - id: swarm5
    name: Builder
    role: Primary Builder
    preferredTaskTypes: [implementation, feature]
    acceptsBroadcast: true
  - id: swarm6
    name: Reviewer
    role: Reviewer / Merge Gate
    preferredTaskTypes: [review, qa, verification]
    acceptsBroadcast: true
"""
    )
    monkeypatch.setenv("HERMES_SWARM_ROSTER_PATH", str(roster_path))
    plan = select_worker_pattern(
        PatternRequest(
            objective="Implement persistent profile lanes",
            scopes=("router",),
            persistent_workers=True,
        )
    )

    rendered = render_execution_plan(plan)

    assert rendered.mechanism == "swarm_profiles"
    assert rendered.commands
    command_profiles = [command[2] for command in rendered.commands]
    assert "swarm1" not in command_profiles
    assert "swarm5" in command_profiles
    assert "swarm6" in command_profiles
    assert any("canonical swarm roster" in lane["hermes_hint"] for lane in rendered.lanes)
    for command in rendered.commands:
        assert isinstance(command, tuple)
        assert command[:5] == ("hermes", "--profile", command[2], "chat", "-Q")
        assert "-q" in command


def test_execution_plan_renders_kanban_task_graph_without_creating_tasks():
    plan = select_worker_pattern(
        PatternRequest(
            objective="Ship phased migration",
            dependencies=("schema", "api", "cutover"),
            durable=True,
        )
    )

    rendered = render_execution_plan(plan)

    assert rendered.mechanism == "kanban"
    assert rendered.commands == ()
    assert rendered.delegate_tasks == ()
    assert rendered.kanban_tasks
    assert all(task["dry_run"] is True for task in rendered.kanban_tasks)
    assert rendered.kanban_tasks[1]["depends_on"] == ["lane-1-phase-worker"]


def test_adapter_exposes_dry_run_execution_plan_entrypoint():
    plan = select_worker_pattern(PatternRequest(objective="Fix one narrow bug"))

    rendered = dry_run_execution_plan(plan)

    assert rendered.dry_run is True
    assert rendered.mechanism == plan.hermes_mapping.primary_mechanism.value


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
    assert data["mechanism"] == "delegate_task"
    assert data["delegate_tasks"]
    assert data["commands"] == []


def test_cli_execute_flag_fails_closed_before_plan_rendering():
    with pytest.raises(SystemExit):
        main(["render-execution-plan", "Refactor auth", "--execute"])
