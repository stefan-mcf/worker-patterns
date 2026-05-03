#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

python -m venv "$TMPDIR/venv"
"$TMPDIR/venv/bin/python" -m pip install -U pip
"$TMPDIR/venv/bin/python" -m pip install -e "$ROOT_DIR"
"$TMPDIR/venv/bin/worker-pattern" select "small docs update" >/dev/null
"$TMPDIR/venv/bin/worker-pattern" render "small docs update" >/dev/null
WORKER_PATTERN_MCP="$TMPDIR/venv/bin/worker-pattern-mcp" "$TMPDIR/venv/bin/python" - <<'PY'
import json
import os
import subprocess

request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
proc = subprocess.run(
    [os.environ["WORKER_PATTERN_MCP"]],
    input=json.dumps(request) + "\n",
    text=True,
    capture_output=True,
    check=True,
    timeout=10,
)
assert proc.stderr == ""
response = json.loads(proc.stdout.splitlines()[0])
assert {tool["name"] for tool in response["result"]["tools"]} == {"select_worker_pattern", "render_execution_plan"}
PY
"$TMPDIR/venv/bin/python" - <<'PY'
from worker_patterns import PatternRequest, select_worker_pattern
from worker_patterns.mcp_server import render_execution_plan_bridge, select_worker_pattern_bridge, tool_names

plan = select_worker_pattern(PatternRequest(objective="small docs update"))
assert plan.selection.selected_pattern.value == "sequential"
assert select_worker_pattern_bridge({"objective": "small docs update"})["dry_run"] is True
assert render_execution_plan_bridge({"objective": "small docs update"})["execution_plan"]["dry_run"] is True
assert set(tool_names()) == {"select_worker_pattern", "render_execution_plan"}
PY
