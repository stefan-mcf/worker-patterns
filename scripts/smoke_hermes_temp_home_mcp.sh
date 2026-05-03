#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT
export HERMES_HOME="$TMPDIR/hermes-home"
mkdir -p "$HERMES_HOME"

python -m venv "$TMPDIR/venv"
"$TMPDIR/venv/bin/python" -m pip install -U pip >/dev/null
"$TMPDIR/venv/bin/python" -m pip install -e "$ROOT_DIR" >/dev/null

"$TMPDIR/venv/bin/python" - <<'PY'
import json
import subprocess
import sys

request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
proc = subprocess.run(
    [sys.executable, "-m", "hermes_worker_patterns.mcp_server"],
    input=json.dumps(request) + "\n",
    text=True,
    capture_output=True,
    check=True,
    timeout=10,
)
assert proc.stderr == ""
response = json.loads(proc.stdout.splitlines()[0])
names = {tool["name"] for tool in response["result"]["tools"]}
assert names == {"select_worker_pattern", "render_execution_plan"}
PY

if command -v hermes >/dev/null 2>&1; then
  HERMES_HOME="$HERMES_HOME" hermes profile list >/dev/null || {
    echo "SKIPPED: hermes CLI present but profile list is unavailable with temporary HERMES_HOME"
    exit 0
  }
  echo "OK: MCP stdio smoke passed with temporary HERMES_HOME=$HERMES_HOME"
else
  echo "SKIPPED: hermes CLI not available"
fi
