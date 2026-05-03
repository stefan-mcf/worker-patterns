from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

DEBUG_ENV = "HERMES_WORKER_PATTERNS_DEBUG"
LOG_ENV = "HERMES_WORKER_PATTERNS_LOG"
_OBJECTIVE_PREVIEW_LIMIT = 120
_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(password|passwd|pwd|token|api[_-]?key|secret)\s*[:=]\s*\S+"),
    re.compile(r"(?i)\b(token|api[_-]?key|secret)\s+\S+"),
)
_TRUTHY = {"1", "true", "yes", "on", "debug"}
_FALSEY = {"", "0", "false", "no", "off"}


def tracing_enabled() -> bool:
    """Return whether opt-in worker-pattern development tracing is enabled."""

    value = os.getenv(DEBUG_ENV, "")
    normalized = value.strip().lower()
    if normalized in _TRUTHY:
        return True
    if normalized in _FALSEY:
        return False
    return False


def new_request_id() -> str:
    """Create a compact request id for correlating bridge/tool events."""

    return uuid.uuid4().hex[:12]


def monotonic_ms() -> float:
    """Expose a testable monotonic clock in milliseconds."""

    return time.perf_counter() * 1000


def emit_trace(event: str, fields: Mapping[str, Any]) -> None:
    """Emit a JSONL trace event to the configured sink when tracing is enabled.

    Defaults to stderr so MCP stdio protocol stdout is never polluted. If
    HERMES_WORKER_PATTERNS_LOG is set, the event is appended to that JSONL file.
    Trace failures are intentionally swallowed because tracing must not change
    router behavior.
    """

    if not tracing_enabled():
        return

    payload = _json_safe(
        {
            "event": event,
            "timestamp": _utc_timestamp(),
            **dict(fields),
        }
    )
    line = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    try:
        log_path = os.getenv(LOG_ENV, "").strip()
        if log_path:
            path = Path(log_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)
        else:
            sys.stderr.write(line)
            sys.stderr.flush()
    except OSError:
        return


def request_trace_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return bounded, non-secret request metadata for trace events."""

    objective = str(payload.get("objective", ""))
    preview = _redact_objective(objective)[:_OBJECTIVE_PREVIEW_LIMIT]
    return {
        "objective_hash": hashlib.sha256(objective.encode("utf-8")).hexdigest()[:16],
        "objective_preview": preview,
        "scopes": _bounded_strings(payload.get("scopes", payload.get("scope", ()))),
        "dependencies": _bounded_strings(payload.get("dependencies", payload.get("dependency", ()))),
        "risk_level": str(payload.get("risk_level", payload.get("risk", "normal")))[:40],
        "review_required": _review_required(payload),
        "tests_required": bool(payload.get("tests_required", False)),
        "durable": bool(payload.get("durable", False)),
        "persistent_workers": bool(payload.get("persistent_workers", False)),
        "recovery": bool(payload.get("recovery", False)),
        "max_parallel_lanes": _safe_int(payload.get("max_parallel_lanes", 4), default=4),
    }


def plan_trace_fields(result: Mapping[str, Any]) -> dict[str, Any]:
    """Return selection/mapping metadata from a worker-pattern result.

    Accepts either the full tool result (with ``plan`` and optional
    ``execution_plan`` keys) or a raw plan dict. Keeping this tolerant matters
    for CLI/MCP smoke debugging where stale installs or direct library calls may
    pass slightly different render shapes.
    """

    plan = result.get("plan") if isinstance(result.get("plan"), Mapping) else result
    selection = plan.get("selection") if isinstance(plan.get("selection"), Mapping) else {}
    mapping = plan.get("runtime_mapping") if isinstance(plan.get("runtime_mapping"), Mapping) else {}
    lanes = _trace_lanes(plan, result)
    return {
        "dry_run": bool(result.get("dry_run", True)),
        "kind": str(result.get("kind", "")),
        "selected_pattern": _string_value(selection.get("selected_pattern", "")),
        "selection_source": _string_value(selection.get("selection_source", "")),
        "matched_signals": _bounded_strings(selection.get("matched_signals", ())),
        "scores": _bounded_mapping(selection.get("scores", {})),
        "score_adjustments": _bounded_mapping(selection.get("score_adjustments", {})),
        "primary_mechanism": _string_value(mapping.get("primary_mechanism", "")),
        "lane_count": len(lanes),
        "lane_profiles": _lane_profiles(lanes),
    }


def _trace_lanes(plan: Mapping[str, Any], result: Mapping[str, Any]) -> list[Any]:
    raw_lanes = plan.get("lanes")
    if isinstance(raw_lanes, Sequence) and not isinstance(raw_lanes, str | bytes | bytearray):
        return list(raw_lanes)
    execution_plan = result.get("execution_plan") if isinstance(result.get("execution_plan"), Mapping) else {}
    execution_lanes = execution_plan.get("lanes") if isinstance(execution_plan, Mapping) else None
    if isinstance(execution_lanes, Sequence) and not isinstance(execution_lanes, str | bytes | bytearray):
        return list(execution_lanes)
    return []


def error_trace_fields(exc: BaseException) -> dict[str, str]:
    """Return bounded exception metadata for trace events."""

    return {
        "error_type": type(exc).__name__,
        "error": str(exc)[:500],
    }


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _json_safe(payload: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(dict(payload), default=lambda obj: getattr(obj, "value", str(obj))))


def _redact_objective(objective: str) -> str:
    redacted = objective
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    return redacted


def _review_required(payload: Mapping[str, Any]) -> bool:
    if bool(payload.get("no_review", False)):
        return False
    return bool(payload.get("review_required", True))


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bounded_strings(value: Any, *, limit: int = 16, item_limit: int = 120) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    else:
        try:
            items = list(value)
        except TypeError:
            items = [value]
    return [str(item)[:item_limit] for item in items[:limit]]


def _bounded_mapping(value: Any, *, limit: int = 32) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key)[:120]: val for key, val in list(value.items())[:limit]}


def _string_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _lane_profiles(lanes: list[Any]) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for lane in lanes[:16]:
        if not isinstance(lane, Mapping):
            continue
        profiles.append(
            {
                "role": str(lane.get("role", ""))[:80],
                "selected_profile": str(lane.get("selected_profile", ""))[:120],
                "fallback_profiles": _bounded_strings(lane.get("fallback_profiles", ()), limit=8),
            }
        )
    return profiles
