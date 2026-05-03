from pathlib import Path


def test_install_smoke_script_contract():
    script = Path("scripts/smoke_install.sh")
    assert script.exists()
    assert script.stat().st_mode & 0o111
    text = script.read_text()
    assert "set -euo pipefail" in text
    assert "mktemp -d" in text
    assert "python -m venv" in text
    assert "pip install -e" in text
    assert 'worker-pattern" select' in text
    assert 'worker-pattern" render' in text
    assert "worker_patterns" in text
    forbidden_home = "/".join(["", "Users", "stefan", ".hermes"])
    assert forbidden_home not in text
