from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping, Sequence
from typing import Any, TextIO

from .hermes_tool import worker_pattern_tool

JsonArgs = str | bytes | bytearray | Mapping[str, Any]
TOOL_NAMES = ("select_worker_pattern", "render_execution_plan")

def select_worker_pattern_bridge(args: JsonArgs) -> dict[str, Any]:
    """Return the worker-pattern selection as JSON-safe data.

    This is the small bridge surface intended for MCP registration. It is
    intentionally pure: no worker launch, no Kanban writes, no Hermes config
    mutation, and no dependency on a local Hermes checkout.
    """

    payload = _payload_with_output(args, "select")
    return worker_pattern_tool(
        payload,
        trace_interface="mcp_bridge",
        trace_event="select_worker_pattern",
    )


def render_execution_plan_bridge(args: JsonArgs) -> dict[str, Any]:
    """Return the dry-run Hermes execution plan as JSON-safe data.

    The rendered commands and task specs are inspectable only; callers must not
    treat this bridge as an executor.
    """

    payload = _payload_with_output(args, "execution_plan")
    return worker_pattern_tool(
        payload,
        trace_interface="mcp_bridge",
        trace_event="render_execution_plan",
    )


def create_mcp_server() -> Any:
    """Create a minimal FastMCP server for the bridge tools.

    The MCP SDK is optional so normal package imports and tests do not require
    it. If it is unavailable, ``main()`` falls back to a tiny JSON-RPC stdio
    server that supports MCP smoke-test methods only.
    """

    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError(
            "MCP bridge requires the optional 'mcp' package; install it in the "
            "environment that will host the FastMCP server, or use the built-in "
            "JSON-RPC stdio smoke fallback."
        ) from exc

    server = FastMCP("hermes-worker-patterns")

    @server.tool(name="select_worker_pattern")
    def select_worker_pattern_tool(
        objective: str,
        scopes: list[str] | None = None,
        dependencies: list[str] | None = None,
        risk_level: str = "normal",
        review_required: bool = True,
        tests_required: bool = False,
        variants_requested: int = 0,
        durable: bool = False,
        persistent_workers: bool = False,
        recovery: bool = False,
        max_parallel_lanes: int = 4,
        notes: list[str] | None = None,
    ) -> dict[str, Any]:
        return select_worker_pattern_bridge(
            _tool_payload(
                objective=objective,
                scopes=scopes,
                dependencies=dependencies,
                risk_level=risk_level,
                review_required=review_required,
                tests_required=tests_required,
                variants_requested=variants_requested,
                durable=durable,
                persistent_workers=persistent_workers,
                recovery=recovery,
                max_parallel_lanes=max_parallel_lanes,
                notes=notes,
            )
        )

    @server.tool(name="render_execution_plan")
    def render_execution_plan_tool(
        objective: str,
        scopes: list[str] | None = None,
        dependencies: list[str] | None = None,
        risk_level: str = "normal",
        review_required: bool = True,
        tests_required: bool = False,
        variants_requested: int = 0,
        durable: bool = False,
        persistent_workers: bool = False,
        recovery: bool = False,
        max_parallel_lanes: int = 4,
        notes: list[str] | None = None,
    ) -> dict[str, Any]:
        return render_execution_plan_bridge(
            _tool_payload(
                objective=objective,
                scopes=scopes,
                dependencies=dependencies,
                risk_level=risk_level,
                review_required=review_required,
                tests_required=tests_required,
                variants_requested=variants_requested,
                durable=durable,
                persistent_workers=persistent_workers,
                recovery=recovery,
                max_parallel_lanes=max_parallel_lanes,
                notes=notes,
            )
        )

    return server


def tool_names() -> tuple[str, ...]:
    """Return advertised MCP bridge tool names without importing MCP SDK."""

    return TOOL_NAMES


def main() -> None:
    """Run the stdio MCP server.

    Prefer FastMCP when installed. Otherwise serve a minimal JSON-RPC subset
    sufficient for local stdio launch validation: initialize, tools/list, and
    tools/call. The fallback writes only protocol JSON to stdout.
    """

    if os.getenv("HERMES_WORKER_PATTERNS_FORCE_STDIO_FALLBACK") == "1":
        _run_json_rpc_stdio(sys.stdin, sys.stdout)
        return

    try:
        server = create_mcp_server()
    except RuntimeError:
        _run_json_rpc_stdio(sys.stdin, sys.stdout)
        return
    server.run()


def _run_json_rpc_stdio(stdin: TextIO, stdout: TextIO) -> None:
    for line in stdin:
        if not line.strip():
            continue
        response = _handle_json_rpc_message(json.loads(line))
        if response is not None:
            stdout.write(json.dumps(response, sort_keys=True) + "\n")
            stdout.flush()


def _handle_json_rpc_message(message: dict[str, Any]) -> dict[str, Any] | None:
    request_id = message.get("id")
    method = message.get("method")
    try:
        if method == "initialize":
            return _json_rpc_result(
                request_id,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "hermes-worker-patterns", "version": "0.1.0"},
                    "capabilities": {"tools": {}},
                },
            )
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return _json_rpc_result(request_id, {"tools": _tool_descriptors()})
        if method == "tools/call":
            params = message.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if name == "select_worker_pattern":
                payload = select_worker_pattern_bridge(arguments)
            elif name == "render_execution_plan":
                payload = render_execution_plan_bridge(arguments)
            else:
                raise ValueError(f"unknown tool: {name}")
            return _json_rpc_result(
                request_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(payload, sort_keys=True),
                        }
                    ],
                    "isError": False,
                },
            )
        raise ValueError(f"unsupported method: {method}")
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": str(exc)},
        }


def _json_rpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _tool_descriptors() -> list[dict[str, Any]]:
    schema = {
        "type": "object",
        "required": ["objective"],
        "properties": {
            "objective": {"type": "string"},
            "scopes": {"type": "array", "items": {"type": "string"}},
            "dependencies": {"type": "array", "items": {"type": "string"}},
            "risk_level": {"type": "string"},
            "review_required": {"type": "boolean"},
            "tests_required": {"type": "boolean"},
            "variants_requested": {"type": "integer"},
            "durable": {"type": "boolean"},
            "persistent_workers": {"type": "boolean"},
            "recovery": {"type": "boolean"},
            "max_parallel_lanes": {"type": "integer"},
            "notes": {"type": "array", "items": {"type": "string"}},
        },
    }
    return [
        {
            "name": "select_worker_pattern",
            "description": "Select a dry-run-safe Hermes worker pattern.",
            "inputSchema": schema,
        },
        {
            "name": "render_execution_plan",
            "description": "Render a dry-run Hermes execution plan for a selected worker pattern.",
            "inputSchema": schema,
        },
    ]


def _payload_with_output(args: JsonArgs, output: str) -> dict[str, Any]:
    payload = _load_payload(args)
    payload["output"] = output
    return payload


def _load_payload(args: JsonArgs) -> dict[str, Any]:
    if isinstance(args, Mapping):
        return dict(args)
    if isinstance(args, (str, bytes, bytearray)):
        decoded = json.loads(args)
        if not isinstance(decoded, dict):
            raise ValueError("args must decode to a JSON object")
        return decoded
    raise TypeError("args must be a JSON object string or mapping")


def _tool_payload(
    *,
    objective: str,
    scopes: Sequence[str] | None,
    dependencies: Sequence[str] | None,
    risk_level: str,
    review_required: bool,
    tests_required: bool,
    variants_requested: int,
    durable: bool,
    persistent_workers: bool,
    recovery: bool,
    max_parallel_lanes: int,
    notes: Sequence[str] | None,
) -> dict[str, Any]:
    return {
        "objective": objective,
        "scopes": list(scopes or ()),
        "dependencies": list(dependencies or ()),
        "risk_level": risk_level,
        "review_required": review_required,
        "tests_required": tests_required,
        "variants_requested": variants_requested,
        "durable": durable,
        "persistent_workers": persistent_workers,
        "recovery": recovery,
        "max_parallel_lanes": max_parallel_lanes,
        "notes": list(notes or ()),
    }


if __name__ == "__main__":  # pragma: no cover
    main()
