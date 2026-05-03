from pathlib import Path


def test_temp_hermes_home_smoke_script_contract():
    script = Path("scripts/smoke_hermes_temp_home_mcp.sh")
    assert script.exists()
    assert script.stat().st_mode & 0o111
    text = script.read_text()
    assert "set -euo pipefail" in text
    assert "mktemp -d" in text
    assert 'HERMES_HOME="$TMPDIR/hermes-home"' in text
    assert "worker_patterns.mcp_server" in text
    assert "tools/list" in text
    assert "SKIPPED: hermes CLI not available" in text
    forbidden_home = "/".join(["", "Users", "stefan", ".hermes"])
    assert forbidden_home not in text
