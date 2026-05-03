import json
import os
import subprocess
import sys

from worker_patterns.mcp_server import main, tool_names


def _rpc(method, params=None, request_id=1, extra_env=None):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src" + os.pathsep + env.get("PYTHONPATH", "")
    env["HERMES_WORKER_PATTERNS_FORCE_STDIO_FALLBACK"] = "1"
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, "-m", "worker_patterns.mcp_server"],
        input=json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}) + "\n",
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
        env=env,
    )
    assert proc.stderr == ""
    return json.loads(proc.stdout.splitlines()[0])


def test_mcp_module_exposes_main():
    assert callable(main)


def test_mcp_advertises_expected_tools():
    assert set(tool_names()) == {"select_worker_pattern", "render_execution_plan"}
    response = _rpc("tools/list")
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert names == set(tool_names())


def test_mcp_tools_call_returns_protocol_clean_stdout():
    response = _rpc(
        "tools/call",
        {"name": "select_worker_pattern", "arguments": {"objective": "small docs update"}},
    )
    content = response["result"]["content"][0]
    payload = json.loads(content["text"])
    assert payload["dry_run"] is True
    assert payload["kind"] == "worker_pattern_selection"


def test_mcp_stdout_remains_protocol_clean_with_trace_env(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    response = _rpc(
        "tools/call",
        {"name": "render_execution_plan", "arguments": {"objective": "small docs update"}},
        extra_env={"HERMES_WORKER_PATTERNS_LOG": str(trace_path)},
    )
    assert response["result"]["isError"] is False
    content = response["result"]["content"][0]
    payload = json.loads(content["text"])
    assert payload["execution_plan"]["dry_run"] is True
