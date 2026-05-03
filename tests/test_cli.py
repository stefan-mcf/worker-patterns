import json

import pytest
from worker_patterns.cli import main


def test_cli_select_json(capsys):
    assert (
        main(
            [
                "select",
                "Refactor auth and billing",
                "--scope",
                "auth",
                "--scope",
                "billing",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["selection"]["selected_pattern"] == "module-swarm"
    assert data["runtime_mapping"]["primary_mechanism"] == "delegate_task"



def test_cli_render_prompt_contract(capsys):
    assert main(["render", "Compare variants", "--variant-count", "2"]) == 0
    out = capsys.readouterr().out
    assert "Selected worker pattern: blueprint-fanout" in out
    assert "Primary mechanism: delegate_task" in out
    assert "Proof expectations:" in out



def test_cli_render_delegate_json(capsys):
    assert (
        main(
            [
                "render-delegate",
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
    assert data["mechanism"] == "delegate_task"
    assert data["dry_run"] is True
    assert any(task["role"] == "integrator" for task in data["tasks"])



def test_cli_render_swarm_json(capsys):
    assert (
        main(
            [
                "render-swarm",
                "Implement multi-role fix",
                "--scope",
                "auth",
                "--persistent-workers",
            ]
        )
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["mechanism"] == "swarm_profiles"
    assert data["dry_run"] is True
    assert data["workers"][0]["command_argv"][0] == "hermes"



def test_cli_render_kanban_requires_dry_run():
    with pytest.raises(SystemExit):
        main(["render-kanban", "Ship phased migration", "--dependency", "phase-1"])



def test_cli_render_kanban_dry_run(capsys):
    assert (
        main(
            [
                "render-kanban",
                "Ship phased migration",
                "--dependency",
                "phase-1",
                "--dependency",
                "phase-2",
                "--dependency",
                "phase-3",
                "--dry-run",
            ]
        )
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["mechanism"] == "kanban"
    assert data["dry_run"] is True
    assert data["tasks"][0]["dry_run"] is True
