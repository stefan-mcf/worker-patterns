from __future__ import annotations

import json
from typing import Any

from .execution_plan import render_execution_plan
from .prompt_renderer import (
    render_delegate_specs,
    render_kanban_spec,
    render_prompt_bundle,
    render_swarm_spec,
)
from .schemas import PatternRequest
from .selector import select_worker_pattern
from .trace import (
    emit_trace,
    error_trace_fields,
    monotonic_ms,
    new_request_id,
    plan_trace_fields,
    request_trace_fields,
)

JsonArgs = str | bytes | bytearray | dict[str, Any]

_ALLOWED_OUTPUTS = {
    "select",
    "execution_plan",
    "prompt_bundle",
    "delegate",
    "swarm",
    "kanban",
}


def worker_pattern_tool(
    args: JsonArgs,
    *,
    trace_interface: str = "python_api",
    trace_event: str = "select_worker_pattern",
) -> dict[str, Any]:
    """Tool-compatible pure Python entrypoint for Hermes worker-pattern selection.

    Accepts a JSON object as a string/bytes payload or an already-decoded dict.
    Returns JSON-serializable plan output and never shells out, spawns workers,
    creates Kanban tasks, or mutates Hermes config.
    """

    request_id = new_request_id()
    started_ms = monotonic_ms()
    payload: dict[str, Any] = {}
    try:
        payload = _load_args(args)
        output = str(payload.get("output", "execution_plan"))
        if output not in _ALLOWED_OUTPUTS:
            allowed = ", ".join(sorted(_ALLOWED_OUTPUTS))
            raise ValueError(f"output must be one of: {allowed}")

        plan = select_worker_pattern(_request_from_payload(payload))
        result = _json_safe(_render_tool_output(plan, output))
        emit_trace(
            trace_event,
            {
                "request_id": request_id,
                "interface": trace_interface,
                "status": "ok",
                "duration_ms": round(monotonic_ms() - started_ms, 3),
                **request_trace_fields(payload),
                **plan_trace_fields(result),
            },
        )
        return result
    except Exception as exc:
        emit_trace(
            "worker_pattern_error",
            {
                "request_id": request_id,
                "interface": trace_interface,
                "status": "error",
                "duration_ms": round(monotonic_ms() - started_ms, 3),
                **request_trace_fields(payload),
                **error_trace_fields(exc),
            },
        )
        raise


def worker_pattern_tool_json(args: JsonArgs) -> str:
    """Return the tool output as a JSON string for tool hosts that expect text."""

    return json.dumps(worker_pattern_tool(args), indent=2, sort_keys=True)


def _json_safe(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(
        json.dumps(payload, default=lambda obj: getattr(obj, "value", str(obj)))
    )


def _load_args(args: JsonArgs) -> dict[str, Any]:
    if isinstance(args, dict):
        payload = args
    elif isinstance(args, (str, bytes, bytearray)):
        payload = json.loads(args)
    else:
        raise TypeError("args must be a JSON object string or dict")
    if not isinstance(payload, dict):
        raise ValueError("args must decode to a JSON object")
    return payload


def _request_from_payload(payload: dict[str, Any]) -> PatternRequest:
    objective = str(payload.get("objective", ""))
    review_required = bool(payload.get("review_required", True))
    if bool(payload.get("no_review", False)):
        review_required = False

    return PatternRequest(
        objective=objective,
        scopes=_tuple_of_strings(payload.get("scopes", payload.get("scope", ()))),
        dependencies=_tuple_of_strings(
            payload.get("dependencies", payload.get("dependency", ()))
        ),
        risk_level=str(payload.get("risk_level", payload.get("risk", "normal"))),
        review_required=review_required,
        tests_required=bool(payload.get("tests_required", False)),
        variants_requested=int(payload.get("variants_requested", payload.get("variant_count", 0))),
        durable=bool(payload.get("durable", False)),
        persistent_workers=bool(payload.get("persistent_workers", False)),
        recovery=bool(payload.get("recovery", False)),
        max_parallel_lanes=int(payload.get("max_parallel_lanes", 4)),
        notes=_tuple_of_strings(payload.get("notes", payload.get("note", ()))),
    )


def _tuple_of_strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def _render_tool_output(plan, output: str) -> dict[str, Any]:
    if output == "select":
        return {
            "dry_run": True,
            "kind": "worker_pattern_selection",
            "plan": plan.to_dict(),
        }
    if output == "execution_plan":
        return {
            "dry_run": True,
            "kind": "worker_pattern_execution_plan",
            "plan": plan.to_dict(),
            "execution_plan": render_execution_plan(plan).to_dict(),
        }
    if output == "prompt_bundle":
        return {
            "dry_run": True,
            "kind": "worker_pattern_prompt_bundle",
            "prompt_bundle": render_prompt_bundle(plan),
        }
    if output == "delegate":
        return {
            "dry_run": True,
            "kind": "worker_pattern_delegate_spec",
            "delegate": render_delegate_specs(plan),
        }
    if output == "swarm":
        return {
            "dry_run": True,
            "kind": "worker_pattern_swarm_spec",
            "swarm": render_swarm_spec(plan),
        }
    if output == "kanban":
        return {
            "dry_run": True,
            "kind": "worker_pattern_kanban_spec",
            "kanban": render_kanban_spec(plan),
        }
    raise AssertionError(f"unsupported output: {output}")
