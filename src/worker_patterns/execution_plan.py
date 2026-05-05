from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .prompt_renderer import (
    render_ephemeral_worker_specs,
    render_persistent_worker_spec,
    render_task_graph_spec,
)
from .schemas import ExecutionMechanism, PatternLane, PatternPlan


@dataclass(frozen=True)
class RuntimeExecutionPlan:
    """Dry-run execution plan for external runtime primitives."""

    mechanism: str
    lanes: tuple[dict[str, Any], ...]
    commands: tuple[tuple[str, ...], ...] = ()
    ephemeral_worker_tasks: tuple[dict[str, Any], ...] = ()
    worker_specs: tuple[dict[str, Any], ...] = ()
    task_graph_tasks: tuple[dict[str, Any], ...] = ()
    # Deprecated compatibility fields retained for older integrations.
    delegate_tasks: tuple[dict[str, Any], ...] = ()
    kanban_tasks: tuple[dict[str, Any], ...] = ()
    safety_notes: tuple[str, ...] = ()
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def render_execution_plan(plan: PatternPlan) -> RuntimeExecutionPlan:
    mechanism = plan.runtime_mapping.primary_mechanism
    lanes = tuple(_lane_summary(lane) for lane in plan.lanes)
    ephemeral_tasks: tuple[dict[str, Any], ...] = ()
    persistent_workers: tuple[dict[str, Any], ...] = ()
    task_graph_tasks: tuple[dict[str, Any], ...] = ()

    if mechanism == ExecutionMechanism.PERSISTENT_WORKERS:
        worker_spec = render_persistent_worker_spec(plan)
        persistent_workers = tuple(worker_spec["workers"])
    elif mechanism == ExecutionMechanism.EPHEMERAL_WORKERS:
        ephemeral_spec = render_ephemeral_worker_specs(plan)
        ephemeral_tasks = tuple(ephemeral_spec["workers"])
    elif mechanism == ExecutionMechanism.TASK_GRAPH:
        task_graph_spec = render_task_graph_spec(plan)
        task_graph_tasks = tuple(task_graph_spec["tasks"])

    return RuntimeExecutionPlan(
        mechanism=mechanism.value,
        lanes=lanes,
        commands=(),
        ephemeral_worker_tasks=ephemeral_tasks,
        worker_specs=persistent_workers,
        task_graph_tasks=task_graph_tasks,
        delegate_tasks=ephemeral_tasks,
        kanban_tasks=task_graph_tasks,
        safety_notes=tuple(_safety_notes(plan)),
    )


def _lane_summary(lane: PatternLane) -> dict[str, Any]:
    return {
        "role": lane.role,
        "count": lane.count,
        "scope": list(lane.scope),
        "purpose": lane.purpose,
        "selected_profile": lane.selected_profile,
        "fallback_profiles": list(lane.fallback_profiles),
        "toolsets": list(lane.toolsets),
        "runtime_hint": lane.runtime_hint,
    }


def _safety_notes(plan: PatternPlan) -> list[str]:
    notes = list(plan.safety_notes)
    notes.append(
        "Dry-run only: this execution plan renders worker and task specs but does not execute them."
    )
    notes.append("Reserved --execute flag fails closed until explicit execution support is approved.")
    if plan.module_swarm_scale is not None:
        scale = plan.module_swarm_scale
        notes.append(
            "Module-swarm execution lanes are logical decomposition lanes; runtime adapters decide how to map them."
        )
        notes.append(
            "Module-swarm scale policy: "
            f"{scale.requested_lane_count} requested lanes as decomposition count, "
            f"{scale.max_active_lanes} max active lanes, {scale.waves_required} waves."
        )
        if scale.integrator_per_wave:
            notes.append(
                "High-risk or conflicted module-swarm runs reduce active lanes and require integration gates."
            )
    return notes
