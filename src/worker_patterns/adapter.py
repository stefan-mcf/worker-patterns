from __future__ import annotations

from .execution_plan import RuntimeExecutionPlan, render_execution_plan
from .schemas import (
    ExecutionMechanism,
    PatternLane,
    PatternPlan,
    PatternRequest,
    PatternSelection,
    RuntimeMapping,
    WorkerPattern,
)


def adapt_to_runtime(
    request: PatternRequest,
    selection: PatternSelection,
    lanes: tuple[PatternLane, ...],
) -> RuntimeMapping:
    """Map a selected worker pattern to a runtime-neutral mechanism.

    This function returns inspectable planning instructions only. It never
    launches workers, creates durable tasks, or mutates runtime configuration.
    """

    base = selection.selected_pattern
    lane_count = sum(max(lane.count, 1) for lane in lanes)

    if request.durable or len(request.dependencies) > 2:
        primary = ExecutionMechanism.TASK_GRAPH
        fallback = (
            ExecutionMechanism.CONTINUATION,
            ExecutionMechanism.PERSISTENT_WORKERS,
            ExecutionMechanism.EPHEMERAL_WORKERS,
        )
        hint = (
            "Use a dry-run task graph for dependency/wave tracking; map lanes "
            "to an external runtime only after review."
        )
    elif request.persistent_workers:
        primary = ExecutionMechanism.PERSISTENT_WORKERS
        fallback = (ExecutionMechanism.EPHEMERAL_WORKERS, ExecutionMechanism.CONTINUATION)
        hint = (
            "Use named workers for role/tool-specific lanes, then integrate "
            "the outputs in the parent session."
        )
    elif base in {WorkerPattern.MODULE_SWARM, WorkerPattern.BLUEPRINT_FANOUT} or lane_count > 2:
        primary = ExecutionMechanism.EPHEMERAL_WORKERS
        fallback = (ExecutionMechanism.PERSISTENT_WORKERS, ExecutionMechanism.CONTINUATION)
        hint = (
            "Use ephemeral worker lanes for bounded parallel subtasks; preserve "
            "scope and role in each worker context."
        )
    elif base == WorkerPattern.PHASED_ASSEMBLY:
        primary = ExecutionMechanism.CONTINUATION
        fallback = (ExecutionMechanism.TASK_GRAPH, ExecutionMechanism.EPHEMERAL_WORKERS)
        hint = (
            "Use a managed continuation for cross-turn waves; promote to a task "
            "graph if durable dependency tracking is required."
        )
    elif base in {WorkerPattern.RECOVERY_LANE, WorkerPattern.BRIDGE_LANE}:
        primary = ExecutionMechanism.DIRECT
        fallback = (ExecutionMechanism.CONTINUATION, ExecutionMechanism.PERSISTENT_WORKERS)
        hint = "Use one narrow recovery lane; avoid parallel edits until failure state is understood."
    else:
        primary = ExecutionMechanism.DIRECT
        fallback = (ExecutionMechanism.CONTINUATION, ExecutionMechanism.EPHEMERAL_WORKERS)
        hint = "Handle directly in the current runtime turn unless the task spans multiple turns."

    contract = _prompt_contract(request, selection, lanes, primary, hint)
    return RuntimeMapping(primary, fallback, hint, contract)


def dry_run_execution_plan(plan: PatternPlan) -> RuntimeExecutionPlan:
    return render_execution_plan(plan)


# Backwards-compatible alias for older integrations.
adapt_to_hermes = adapt_to_runtime


def _prompt_contract(
    request: PatternRequest,
    selection: PatternSelection,
    lanes: tuple[PatternLane, ...],
    primary: ExecutionMechanism,
    hint: str,
) -> str:
    overlay = ", ".join(pattern.value for pattern in selection.overlays) or "none"
    lane_sections: list[str] = []
    for lane in lanes:
        scope = ", ".join(lane.scope) or ", ".join(request.scopes) or "bounded task scope only"
        lane_sections.extend(
            [
                f"Role: {lane.role}",
                f"Scope: {scope}",
                f"Purpose: {lane.purpose}",
                f"Allowed edits: only files required for {scope}",
                "Expected output: concise lane summary plus proof artifacts",
            ]
        )
    return "\n".join(
        [
            f"Task objective: {request.objective}",
            f"Selected worker pattern: {selection.selected_pattern.value}",
            f"Primary mechanism: {primary.value}",
            f"Overlays: {overlay}",
            f"Mechanism hint: {hint}",
            "Lanes:",
            *lane_sections,
            "Dry-run only. Render runtime-compatible prompts/specs but do not launch workers or mutate runtime settings.",
        ]
    )
