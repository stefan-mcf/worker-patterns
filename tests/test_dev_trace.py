import json

import pytest

from worker_patterns.cli import main as cli_main
from worker_patterns.mcp_server import render_execution_plan_bridge
from worker_patterns.runtime_tool import worker_pattern_tool
from worker_patterns.trace import emit_trace, plan_trace_fields, tracing_enabled


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_dev_tracing_is_disabled_by_default(monkeypatch, tmp_path):
    log_path = tmp_path / "trace.jsonl"
    monkeypatch.delenv("WORKER_PATTERNS_DEBUG", raising=False)
    monkeypatch.setenv("WORKER_PATTERNS_LOG", str(log_path))

    assert tracing_enabled() is False

    worker_pattern_tool(
        {
            "objective": "Refactor independent auth and billing modules",
            "scopes": ["auth", "billing"],
            "notes": ["disjoint scopes"],
        }
    )

    assert not log_path.exists()


def test_dev_tracing_writes_bounded_jsonl_selection_event(monkeypatch, tmp_path):
    log_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("WORKER_PATTERNS_DEBUG", "1")
    monkeypatch.setenv("WORKER_PATTERNS_LOG", str(log_path))

    result = worker_pattern_tool(
        {
            "objective": "Refactor independent auth and billing modules with no secrets",
            "scopes": ["auth", "billing"],
            "notes": ["disjoint scopes"],
            "output": "select",
        }
    )

    events = _read_jsonl(log_path)
    assert len(events) == 1
    event = events[0]
    assert event["event"] == "select_worker_pattern"
    assert event["interface"] == "python_api"
    assert event["status"] == "ok"
    assert event["request_id"]
    assert event["dry_run"] is True
    assert event["kind"] == "worker_pattern_selection"
    assert event["selected_pattern"] == result["plan"]["selection"]["selected_pattern"]
    assert event["selection_source"] == result["plan"]["selection"]["selection_source"]
    assert event["primary_mechanism"] == result["plan"]["runtime_mapping"]["primary_mechanism"]
    assert event["lane_count"] == len(result["plan"]["lanes"])
    assert event["lane_profiles"]
    assert event["objective_hash"]
    assert len(event["objective_preview"]) <= 120
    assert "scores" in event
    assert "score_adjustments" in event
    assert "duration_ms" in event


def test_mcp_bridge_dev_tracing_marks_bridge_interface(monkeypatch, tmp_path):
    log_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("WORKER_PATTERNS_DEBUG", "true")
    monkeypatch.setenv("WORKER_PATTERNS_LOG", str(log_path))

    render_execution_plan_bridge(
        {
            "objective": "Keep persistent review and implementation lanes warm",
            "scope": "router",
            "persistent_workers": True,
        }
    )

    [event] = _read_jsonl(log_path)
    assert event["event"] == "render_execution_plan"
    assert event["interface"] == "mcp_bridge"
    assert event["status"] == "ok"
    assert event["kind"] == "worker_pattern_execution_plan"
    assert event["dry_run"] is True
    assert event["primary_mechanism"] == "persistent_workers"


def test_dev_tracing_logs_errors_without_swallowing_exception(monkeypatch, tmp_path):
    log_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("WORKER_PATTERNS_DEBUG", "1")
    monkeypatch.setenv("WORKER_PATTERNS_LOG", str(log_path))

    with pytest.raises(ValueError, match="output must be one of"):
        worker_pattern_tool({"objective": "Do work", "output": "execute"})

    [event] = _read_jsonl(log_path)
    assert event["event"] == "worker_pattern_error"
    assert event["interface"] == "python_api"
    assert event["status"] == "error"
    assert event["error_type"] == "ValueError"
    assert "output must be one of" in event["error"]
    assert event["objective_hash"]


def test_dev_tracing_redacts_common_secret_tokens(monkeypatch, tmp_path):
    log_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("WORKER_PATTERNS_DEBUG", "1")
    monkeypatch.setenv("WORKER_PATTERNS_LOG", str(log_path))

    worker_pattern_tool(
        {
            "objective": "Rotate password=supersecret token abc123 and ship safely",
            "output": "select",
        }
    )

    [event] = _read_jsonl(log_path)
    assert "supersecret" not in event["objective_preview"]
    assert "abc123" not in event["objective_preview"]
    assert "[REDACTED]" in event["objective_preview"]


def test_cli_dev_tracing_uses_stderr_or_file_without_polluting_stdout(monkeypatch, tmp_path, capsys):
    log_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("WORKER_PATTERNS_DEBUG", "1")
    monkeypatch.setenv("WORKER_PATTERNS_LOG", str(log_path))

    exit_code = cli_main(
        [
            "select",
            "Refactor independent auth and billing modules",
            "--scope",
            "auth",
            "--scope",
            "billing",
        ]
    )

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    [event] = _read_jsonl(log_path)
    assert exit_code == 0
    assert captured.err == ""
    assert result["selection"]["selected_pattern"] == "module-swarm"
    assert event["event"] == "select_worker_pattern"
    assert event["interface"] == "cli"
    assert event["status"] == "ok"
    assert event["selected_pattern"] == result["selection"]["selected_pattern"]


def test_dev_tracing_handles_raw_plan_dicts():
    result = worker_pattern_tool(
        {
            "objective": "Refactor independent auth and billing modules",
            "scopes": ["auth", "billing"],
            "notes": ["disjoint scopes"],
            "output": "select",
        }
    )

    fields = plan_trace_fields(result["plan"])

    assert fields["selected_pattern"] == "module-swarm"
    assert fields["primary_mechanism"] == "ephemeral_workers"
    assert fields["lane_count"] == len(result["plan"]["lanes"])
    assert fields["lane_profiles"]


def test_emit_trace_falls_back_to_stderr_when_no_log_file(monkeypatch, capsys):
    monkeypatch.setenv("WORKER_PATTERNS_DEBUG", "1")
    monkeypatch.delenv("WORKER_PATTERNS_LOG", raising=False)

    emit_trace("manual_event", {"value": "ok"})

    captured = capsys.readouterr()
    assert captured.out == ""
    event = json.loads(captured.err.strip())
    assert event["event"] == "manual_event"
    assert event["value"] == "ok"
