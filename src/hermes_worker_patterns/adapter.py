from __future__ import annotations

from .execution_plan import HermesExecutionPlan, render_execution_plan
from .schemas import (
    ExecutionMechanism,
    HermesMapping,
    PatternLane,
    PatternPlan,
    PatternRequest,
    PatternSelection,
    WorkerPattern,
)


def adapt_to_hermes(request: PatternRequest, selection: PatternSelection, lanes: tuple[PatternLane, ...]) -> HermesMapping:
    """Map a selected worker pattern to the most natural Hermes primitive.

    This function deliberately returns instructions only. It does not launch workers,
    create Kanban tasks, or mutate Hermes configuration.
    """
    base = selection.selected_pattern
    lane_count = sum(max(lane.count, 1) for lane in lanes)

    if request.durable or len(request.dependencies) > 2:
        primary = ExecutionMechanism.KANBAN
        fallback = (ExecutionMechanism.GOAL, ExecutionMechanism.SWARM_PROFILES, ExecutionMechanism.DELEGATE_TASK)
        hint = "Create linked Hermes Kanban tasks for dependency/wave tracking; use dispatcher or assigned profiles for execution."
    elif request.persistent_workers:
        primary = ExecutionMechanism.SWARM_PROFILES
        fallback = (ExecutionMechanism.DELEGATE_TASK, ExecutionMechanism.GOAL)
        hint = "Use named Hermes swarm profiles for role/model-specific lanes, then integrate in the main session."
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
        hint = "Use one narrow Hermes lane; avoid parallel edits until the failure state is understood."
    else:
        primary = ExecutionMechanism.DIRECT
        fallback = (ExecutionMechanism.GOAL, ExecutionMechanism.DELEGATE_TASK)
        hint = "Handle directly in the current Hermes turn unless the task starts spanning multiple turns."

    contract = _prompt_contract(request, selection, lanes, primary, hint)
    return HermesMapping(primary, fallback, hint, contract)


def dry_run_execution_plan(plan: PatternPlan) -> HermesExecutionPlan:
    """Render an inspectable dry-run Hermes execution plan for an adapted plan.

    This adapter entrypoint intentionally delegates to the renderer without
    launching workers, creating Kanban tasks, or mutating Hermes configuration.
    """
    return render_execution_plan(plan)


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
            "Dry-run only. Render Hermes-compatible prompts/specs but do not launch workers or mutate Hermes settings.",
        ]
    )
