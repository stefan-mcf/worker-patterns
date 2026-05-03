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


def adapt_to_runtime(request: PatternRequest, selection: PatternSelection, lanes: tuple[PatternLane, ...]) -> RuntimeMapping:
    """Map a selected worker pattern to a runtime-neutral execution mechanism.

    This function deliberately returns instructions only. It does not launch workers,
    create durable tasks, or mutate runtime configuration.
    """
    base = selection.selected_pattern
    lane_count = sum(max(lane.count, 1) for lane in lanes)

    if request.durable or len(request.dependencies) > 2:
        primary = ExecutionMechanism.KANBAN
        fallback = (ExecutionMechanism.GOAL, ExecutionMechanism.SWARM_PROFILES, ExecutionMechanism.DELEGATE_TASK)
        hint = "Use a durable task graph for dependency/wave tracking; assign lanes to an external runtime or profile pool for execution."
    elif request.persistent_workers:
        primary = ExecutionMechanism.SWARM_PROFILES
        fallback = (ExecutionMechanism.DELEGATE_TASK, ExecutionMechanism.GOAL)
        hint = "Use named runtime profiles for role/model-specific lanes, then integrate in the parent session."
    elif base in {WorkerPattern.MODULE_SWARM, WorkerPattern.BLUEPRINT_FANOUT} or lane_count > 2:
        primary = ExecutionMechanism.DELEGATE_TASK
        fallback = (ExecutionMechanism.SWARM_PROFILES, ExecutionMechanism.GOAL)
        hint = "Use delegate_task batch for bounded parallel lanes; preserve scope and role in each subagent context."
    elif base == WorkerPattern.PHASED_ASSEMBLY:
        primary = ExecutionMechanism.GOAL
        fallback = (ExecutionMechanism.KANBAN, ExecutionMechanism.DELEGATE_TASK)
        hint = "Use /goal for cross-turn wave execution; promote to Kanban if it needs durable task tracking."
    elif base in {WorkerPattern.RECOVERY_LANE, WorkerPattern.BRIDGE_LANE}:
        primary = ExecutionMechanism.DIRECT
        fallback = (ExecutionMechanism.GOAL, ExecutionMechanism.SWARM_PROFILES)
        hint = "Use one narrow recovery lane; avoid parallel edits until the failure state is understood."
    else:
        primary = ExecutionMechanism.DIRECT
        fallback = (ExecutionMechanism.GOAL, ExecutionMechanism.DELEGATE_TASK)
        hint = "Handle directly in the current runtime turn unless the task starts spanning multiple turns."

    contract = _prompt_contract(request, selection, lanes, primary, hint)
    return RuntimeMapping(primary, fallback, hint, contract)


def dry_run_execution_plan(plan: PatternPlan) -> RuntimeExecutionPlan:
    """Render an inspectable dry-run execution plan for an adapted plan.

    This adapter entrypoint intentionally delegates to the renderer without
    launching workers, creating durable tasks, or mutating runtime configuration.
    """
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
