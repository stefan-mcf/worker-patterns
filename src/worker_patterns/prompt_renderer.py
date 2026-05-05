from __future__ import annotations

from dataclasses import asdict

from .schemas import ExecutionMechanism, PatternLane, PatternPlan

ROLE_OUTPUTS = {
    "builder": "changed files, implementation summary, and validation evidence",
    "variant-designer": "alternative approach summary with tradeoffs",
    "curator": "ranked comparison and selected recommendation",
    "integrator": "merged outcome summary, touched scopes, and integration risks",
    "phase-worker": "phase completion summary and handoff notes for dependent work",
    "recovery-worker": "root-cause summary, narrow repair diff, and resume guidance",
    "reviewer": "independent review verdict, regressions found, and proof check",
}


def render_prompt_contract(plan: PatternPlan) -> str:
    prompt_bundle = render_prompt_bundle(plan)
    lane_sections: list[str] = []
    for lane in prompt_bundle["lanes"]:
        lane_sections.extend(
            [
                f"Role: {lane['role']}",
                f"Scope: {lane['scope_summary']}",
                f"Allowed edits: {lane['allowed_edits']}",
                f"Expected output: {lane['expected_output']}",
                "Proof expectations:",
                *[f"- {item}" for item in lane["proof_expectations"]],
            ]
        )

    return "\n".join(
        [
            f"Task objective: {prompt_bundle['task_objective']}",
            f"Selected worker pattern: {prompt_bundle['selected_pattern']}",
            f"Primary mechanism: {prompt_bundle['primary_mechanism']}",
            f"Overlays: {prompt_bundle['overlays_summary']}",
            f"Mechanism hint: {prompt_bundle['invocation_hint']}",
            "Lanes:",
            *lane_sections,
            "Dry-run only: render runtime-compatible prompts/specs, but do not launch workers, create tasks, or mutate runtime settings.",
        ]
    )


def render_prompt_bundle(plan: PatternPlan) -> dict[str, object]:
    return {
        "task_objective": plan.request.objective,
        "selected_pattern": plan.selection.selected_pattern.value,
        "primary_mechanism": plan.runtime_mapping.primary_mechanism.value,
        "fallback_mechanisms": [mechanism.value for mechanism in plan.runtime_mapping.fallback_mechanisms],
        "overlays_summary": _overlays_summary(plan),
        "invocation_hint": plan.runtime_mapping.invocation_hint,
        "proof_expectations": list(plan.proof_expectations),
        "safety_notes": list(plan.safety_notes),
        "lanes": [_render_lane_prompt(plan, lane) for lane in plan.lanes],
    }


def render_ephemeral_worker_specs(plan: PatternPlan) -> dict[str, object]:
    return {
        "mechanism": ExecutionMechanism.EPHEMERAL_WORKERS.value,
        "dry_run": True,
        "selected_pattern": plan.selection.selected_pattern.value,
        "workers": [_render_ephemeral_worker(plan, lane) for lane in plan.lanes],
        "tasks": [_render_ephemeral_worker(plan, lane) for lane in plan.lanes],
        "safety_notes": list(plan.safety_notes),
    }


# Deprecated compatibility alias.
def render_delegate_specs(plan: PatternPlan) -> dict[str, object]:
    return render_ephemeral_worker_specs(plan)


def render_persistent_worker_spec(plan: PatternPlan) -> dict[str, object]:
    workers = []
    for lane in plan.lanes:
        prompt = _lane_prompt_text(plan, lane)
        workers.append(
            {
                "role": lane.role,
                "worker_profile": lane.selected_profile,
                "profile": lane.selected_profile,
                "fallback_profiles": list(lane.fallback_profiles),
                "toolsets": list(lane.toolsets),
                "prompt": prompt,
                "adapter_command": None,
                "adapter_hint": "Map this logical worker profile to your runtime before execution.",
            }
        )
    return {
        "mechanism": ExecutionMechanism.PERSISTENT_WORKERS.value,
        "dry_run": True,
        "selected_pattern": plan.selection.selected_pattern.value,
        "workers": workers,
        "safety_notes": list(plan.safety_notes),
    }


# Deprecated compatibility alias.
def render_swarm_spec(plan: PatternPlan) -> dict[str, object]:
    return render_persistent_worker_spec(plan)


def render_task_graph_spec(plan: PatternPlan) -> dict[str, object]:
    nodes: list[dict[str, object]] = []
    non_reviewer_ids: list[str] = []
    previous_phase_id = ""
    integrator_ids: list[str] = []

    for index, lane in enumerate(plan.lanes, start=1):
        task_id = f"lane-{index}-{lane.role}"
        depends_on: list[str] = []
        if lane.role == "phase-worker" and previous_phase_id:
            depends_on = [previous_phase_id]
        elif lane.role == "integrator":
            depends_on = list(non_reviewer_ids)
            integrator_ids.append(task_id)
        elif lane.role == "reviewer":
            depends_on = list(integrator_ids or non_reviewer_ids)

        node = {
            "id": task_id,
            "title": _task_title(lane),
            "role": lane.role,
            "scope": list(lane.scope),
            "depends_on": depends_on,
            "selected_profile": lane.selected_profile,
            "prompt": _lane_prompt_text(plan, lane),
            "dry_run": True,
        }
        nodes.append(node)
        if lane.role == "phase-worker":
            previous_phase_id = task_id
        if lane.role != "reviewer":
            non_reviewer_ids.append(task_id)

    return {
        "mechanism": ExecutionMechanism.TASK_GRAPH.value,
        "dry_run": True,
        "selected_pattern": plan.selection.selected_pattern.value,
        "tasks": nodes,
        "safety_notes": list(plan.safety_notes)
        + ["Inspect dependencies before creating tasks; this renderer only emits a dry-run task graph."],
    }


# Deprecated compatibility alias.
def render_kanban_spec(plan: PatternPlan) -> dict[str, object]:
    return render_task_graph_spec(plan)


def _render_lane_prompt(plan: PatternPlan, lane: PatternLane) -> dict[str, object]:
    return {
        "role": lane.role,
        "purpose": lane.purpose,
        "scope": list(lane.scope),
        "scope_summary": _scope_summary(plan, lane),
        "selected_profile": lane.selected_profile,
        "fallback_profiles": list(lane.fallback_profiles),
        "toolsets": list(lane.toolsets),
        "allowed_edits": _allowed_edits(plan, lane),
        "expected_output": _expected_output(lane),
        "proof_expectations": list(_lane_proof_expectations(plan, lane)),
        "prompt": _lane_prompt_text(plan, lane),
        "model_policy": asdict(lane.model_policy),
    }


def _render_ephemeral_worker(plan: PatternPlan, lane: PatternLane) -> dict[str, object]:
    return {
        "goal": _ephemeral_worker_goal(plan, lane),
        "context": _ephemeral_worker_context(plan, lane),
        "toolsets": list(lane.toolsets),
        "role": lane.role,
        "selected_profile": lane.selected_profile,
        "fallback_profiles": list(lane.fallback_profiles),
    }


def _ephemeral_worker_goal(plan: PatternPlan, lane: PatternLane) -> str:
    return (
        f"Act as the {lane.role} lane for objective: {plan.request.objective}. "
        f"Selected worker pattern: {plan.selection.selected_pattern.value}. "
        f"Deliver {_expected_output(lane)}."
    )


def _ephemeral_worker_context(plan: PatternPlan, lane: PatternLane) -> str:
    proof_lines = "; ".join(_lane_proof_expectations(plan, lane))
    return (
        f"Scope: {_scope_summary(plan, lane)}. "
        f"Allowed edits: {_allowed_edits(plan, lane)}. "
        f"Purpose: {lane.purpose}. "
        f"Proof expectations: {proof_lines}. "
        "Dry-run adapter contract only; do not launch external workers or mutate runtime configuration."
    )


def _lane_prompt_text(plan: PatternPlan, lane: PatternLane) -> str:
    proof_lines = "\n".join(f"- {item}" for item in _lane_proof_expectations(plan, lane))
    return (
        f"Role: {lane.role}\n"
        f"Task objective: {plan.request.objective}\n"
        f"Selected worker pattern: {plan.selection.selected_pattern.value}\n"
        f"Lane purpose: {lane.purpose}\n"
        f"Scope: {_scope_summary(plan, lane)}\n"
        f"Allowed edits: {_allowed_edits(plan, lane)}\n"
        f"Expected output: {_expected_output(lane)}\n"
        f"Proof expectations:\n{proof_lines}\n"
        "Dry-run only. Stay within assigned scope and do not create separate runtime machinery."
    )


def _lane_proof_expectations(plan: PatternPlan, lane: PatternLane) -> tuple[str, ...]:
    lane_specific = []
    if lane.role == "reviewer":
        lane_specific.append("independent verdict with explicit regressions or none")
    elif lane.role == "integrator":
        lane_specific.append("integration summary names merged scopes and unresolved risks")
    elif lane.role == "variant-designer":
        lane_specific.append("variant rationale explains why it differs from alternatives")
    return tuple(dict.fromkeys([*plan.proof_expectations, *lane_specific]))


def _scope_summary(plan: PatternPlan, lane: PatternLane) -> str:
    if lane.scope:
        return ", ".join(lane.scope)
    if plan.request.scopes:
        return ", ".join(plan.request.scopes)
    return "bounded task scope only"


def _allowed_edits(plan: PatternPlan, lane: PatternLane) -> str:
    if lane.scope:
        return f"Only files required for scope: {', '.join(lane.scope)}"
    if plan.request.scopes:
        return f"Only files required for scopes: {', '.join(plan.request.scopes)}"
    return "Only files directly required to complete the stated objective"


def _expected_output(lane: PatternLane) -> str:
    return ROLE_OUTPUTS.get(lane.role, "task summary and proof artifacts")


def _task_title(lane: PatternLane) -> str:
    scope = ", ".join(lane.scope) if lane.scope else lane.role
    return f"{lane.role}: {scope}"


def _overlays_summary(plan: PatternPlan) -> str:
    if not plan.selection.overlays:
        return "none"
    return ", ".join(overlay.value for overlay in plan.selection.overlays)
