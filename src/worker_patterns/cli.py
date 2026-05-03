from __future__ import annotations

import argparse
import json
from typing import Any

from .execution_plan import render_execution_plan
from .prompt_renderer import (
    render_delegate_specs,
    render_kanban_spec,
    render_prompt_bundle,
    render_prompt_contract,
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

REQUEST_COMMANDS = {
    "select",
    "render",
    "render-prompts",
    "render-delegate",
    "render-swarm",
    "render-kanban",
    "render-execution-plan",
}



def _json_dumps(payload: Any) -> str:
    return json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        default=lambda obj: getattr(obj, "value", str(obj)),
    )



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select worker patterns and render dry-run runtime specs."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name in REQUEST_COMMANDS:
        help_text = "select a worker pattern and runtime mapping"
        if name.startswith("render-") or name == "render":
            help_text = "render dry-run prompt/spec output"
        p = sub.add_parser(name, help=help_text)
        p.add_argument("objective")
        p.add_argument("--scope", action="append", default=[])
        p.add_argument("--dependency", action="append", default=[])
        p.add_argument(
            "--risk",
            default="normal",
            choices=("low", "normal", "high", "critical"),
        )
        p.add_argument("--review-required", action="store_true", default=False)
        p.add_argument("--no-review", action="store_true", default=False)
        p.add_argument("--tests-required", action="store_true", default=False)
        p.add_argument("--variant-count", type=int, default=0)
        p.add_argument("--durable", action="store_true")
        p.add_argument("--persistent-workers", action="store_true")
        p.add_argument("--recovery", action="store_true")
        p.add_argument("--max-parallel-lanes", type=int, default=4)
        p.add_argument("--note", action="append", default=[])
        p.add_argument(
            "--text",
            action="store_true",
            help="render concise text instead of JSON where supported",
        )
        p.add_argument(
            "--execute",
            action="store_true",
            default=False,
            help="reserved for future execution support; currently fails closed",
        )
        if name == "render-kanban":
            p.add_argument("--dry-run", action="store_true", default=False)
    return parser



def _payload_from_args(args: argparse.Namespace) -> dict[str, Any]:
    review_required = True
    if args.no_review:
        review_required = False
    elif args.review_required:
        review_required = True
    return {
        "objective": args.objective,
        "scopes": list(args.scope),
        "dependencies": list(args.dependency),
        "risk_level": args.risk,
        "review_required": review_required,
        "tests_required": args.tests_required,
        "variants_requested": args.variant_count,
        "durable": args.durable,
        "persistent_workers": args.persistent_workers,
        "recovery": args.recovery,
        "max_parallel_lanes": args.max_parallel_lanes,
        "notes": list(args.note),
    }


def _request_from_payload(payload: dict[str, Any]) -> PatternRequest:
    return PatternRequest(
        objective=str(payload["objective"]),
        scopes=tuple(payload["scopes"]),
        dependencies=tuple(payload["dependencies"]),
        risk_level=str(payload["risk_level"]),
        review_required=bool(payload["review_required"]),
        tests_required=bool(payload["tests_required"]),
        variants_requested=int(payload["variants_requested"]),
        durable=bool(payload["durable"]),
        persistent_workers=bool(payload["persistent_workers"]),
        recovery=bool(payload["recovery"]),
        max_parallel_lanes=int(payload["max_parallel_lanes"]),
        notes=tuple(payload["notes"]),
    )


def _request_from_args(args: argparse.Namespace) -> PatternRequest:
    return _request_from_payload(_payload_from_args(args))



def _render_text(plan) -> str:
    selection = plan.selection
    mapping = plan.runtime_mapping
    overlays = ", ".join(pattern.value for pattern in selection.overlays) or "none"
    lanes = "\n".join(
        (
            f"  - {lane.role}: {lane.purpose} "
            f"[{', '.join(lane.scope) or 'n/a'}] -> {lane.selected_profile}"
        )
        for lane in plan.lanes
    )
    proof = "\n".join(f"  - {item}" for item in plan.proof_expectations)
    return f"""selected_pattern: {selection.selected_pattern.value}
overlays: {overlays}
reason: {selection.reason}
runtime_primary: {mapping.primary_mechanism.value}
runtime_hint: {mapping.invocation_hint}
lanes:
{lanes}
proof_expectations:
{proof}
""".rstrip() + "\n"



def _render_output(command: str, plan, text: bool) -> str:
    if command == "select":
        return _render_text(plan) if text else _json_dumps(plan.to_dict())
    if command == "render":
        return render_prompt_contract(plan)
    if command == "render-prompts":
        return render_prompt_contract(plan) if text else _json_dumps(render_prompt_bundle(plan))
    if command == "render-delegate":
        return _json_dumps(render_delegate_specs(plan))
    if command == "render-swarm":
        return _json_dumps(render_swarm_spec(plan))
    if command == "render-kanban":
        return _json_dumps(render_kanban_spec(plan))
    if command == "render-execution-plan":
        return _json_dumps(render_execution_plan(plan).to_dict())
    raise ValueError(f"unsupported command: {command}")



def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    request_id = new_request_id()
    started_ms = monotonic_ms()
    payload: dict[str, Any] = {}
    try:
        if args.execute:
            parser.error("--execute is reserved and fails closed; execution is not implemented")
        if args.command == "render-kanban" and not args.dry_run:
            parser.error("render-kanban requires --dry-run; execution is not implemented")
        payload = _payload_from_args(args)
        plan = select_worker_pattern(_request_from_payload(payload))
        output = _render_output(args.command, plan, getattr(args, "text", False))
        emit_trace(
            _trace_event_for_command(args.command),
            {
                "request_id": request_id,
                "interface": "cli",
                "status": "ok",
                "duration_ms": round(monotonic_ms() - started_ms, 3),
                **request_trace_fields(payload),
                **plan_trace_fields(
                    {
                        "dry_run": True,
                        "kind": _trace_kind_for_command(args.command),
                        "plan": plan.to_dict(),
                    }
                ),
            },
        )
        print(output, end="")
        return 0
    except Exception as exc:
        emit_trace(
            "worker_pattern_error",
            {
                "request_id": request_id,
                "interface": "cli",
                "status": "error",
                "duration_ms": round(monotonic_ms() - started_ms, 3),
                **request_trace_fields(payload),
                **error_trace_fields(exc),
            },
        )
        raise


def _trace_event_for_command(command: str) -> str:
    if command in {"render", "render-prompts", "render-delegate", "render-swarm", "render-kanban", "render-execution-plan"}:
        return "render_execution_plan"
    return "select_worker_pattern"


def _trace_kind_for_command(command: str) -> str:
    return {
        "select": "worker_pattern_selection",
        "render": "worker_pattern_prompt_contract",
        "render-prompts": "worker_pattern_prompt_bundle",
        "render-delegate": "worker_pattern_delegate_spec",
        "render-swarm": "worker_pattern_swarm_spec",
        "render-kanban": "worker_pattern_kanban_spec",
        "render-execution-plan": "worker_pattern_execution_plan",
    }[command]


if __name__ == "__main__":
    raise SystemExit(main())
