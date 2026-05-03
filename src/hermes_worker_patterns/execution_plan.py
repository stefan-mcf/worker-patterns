from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .prompt_renderer import (
    render_delegate_specs,
    render_kanban_spec,
    render_swarm_spec,
)
from .schemas import ExecutionMechanism, PatternLane, PatternPlan


@dataclass(frozen=True)
class HermesExecutionPlan:
    """Dry-run execution plan for Hermes primitives.

    The plan is intentionally inspectable data. It renders commands and task
    specs but never launches processes, creates Kanban tasks, or mutates Hermes
    settings.
    """

    mechanism: str
    lanes: tuple[dict[str, Any], ...]
    commands: tuple[tuple[str, ...], ...] = ()
    delegate_tasks: tuple[dict[str, Any], ...] = ()
    kanban_tasks: tuple[dict[str, Any], ...] = ()
    safety_notes: tuple[str, ...] = ()
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def render_execution_plan(plan: PatternPlan) -> HermesExecutionPlan:
    mechanism = plan.hermes_mapping.primary_mechanism
    lanes = tuple(_lane_summary(lane) for lane in plan.lanes)
    commands: tuple[tuple[str, ...], ...] = ()
    delegate_tasks: tuple[dict[str, Any], ...] = ()
    kanban_tasks: tuple[dict[str, Any], ...] = ()

    if mechanism == ExecutionMechanism.SWARM_PROFILES:
        swarm_spec = render_swarm_spec(plan)
        commands = tuple(
            tuple(worker["command_argv"])
            for worker in swarm_spec["workers"]
        )
    elif mechanism == ExecutionMechanism.DELEGATE_TASK:
        delegate_spec = render_delegate_specs(plan)
        delegate_tasks = tuple(delegate_spec["tasks"])
    elif mechanism == ExecutionMechanism.KANBAN:
        kanban_spec = render_kanban_spec(plan)
        kanban_tasks = tuple(kanban_spec["tasks"])

    return HermesExecutionPlan(
        mechanism=mechanism.value,
        lanes=lanes,
        commands=commands,
        delegate_tasks=delegate_tasks,
        kanban_tasks=kanban_tasks,
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
        "hermes_hint": lane.hermes_hint,
    }


def _safety_notes(plan: PatternPlan) -> list[str]:
    notes = list(plan.safety_notes)
    notes.append(
        "Dry-run only: this execution plan renders commands and task specs but does not execute them."
    )
    notes.append("Reserved --execute flag fails closed until explicit execution support is approved.")
    if plan.module_swarm_scale is not None:
        scale = plan.module_swarm_scale
        notes.append(
            "Module-swarm execution lanes are the default low-cost parallel profile only; premium/review "
            "and default profiles are not module-swarm fallbacks."
        )
        notes.append(
            "Module-swarm scale policy: "
            f"{scale.requested_lane_count} requested lanes as decomposition count, "
            f"{scale.max_active_lanes} max active lanes, "
            f"{scale.waves_required} waves. Requested lanes are not permission "
            "to launch every lane at once."
        )
        if scale.integrator_per_wave:
            notes.append(
                "High-risk or conflicted module swarms reduce active lanes and "
                "require integration cadence/review gates."
            )
    return notes
