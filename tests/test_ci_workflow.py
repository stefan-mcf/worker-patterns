from pathlib import Path

import yaml


def test_ci_workflow_structure():
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text())
    assert workflow["jobs"]["validate"]["strategy"]["matrix"]["python-version"] == ["3.10", "3.11", "3.12"]
    steps = workflow["jobs"]["validate"]["steps"]
    runs = "\n".join(step.get("run", "") for step in steps)
    assert "python -m pip install -e .[dev]" in runs
    assert "python -m pytest" in runs
    assert "python -m ruff check ." in runs
    assert "scripts/smoke_install.sh" in runs
    assert "scripts/smoke_hermes_temp_home_mcp.sh" in runs
    assert "python -m build" in runs
