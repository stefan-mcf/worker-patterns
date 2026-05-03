import json

from worker_patterns.prompt_renderer import (
    render_delegate_specs,
    render_kanban_spec,
    render_prompt_bundle,
    render_prompt_contract,
    render_swarm_spec,
)
from worker_patterns.schemas import PatternRequest
from worker_patterns.selector import select_worker_pattern


def test_render_prompt_bundle_contains_role_scope_and_proof():
    plan = select_worker_pattern(
        PatternRequest(
            objective="Refactor auth and billing modules",
            scopes=("auth", "billing"),
            tests_required=True,
        )
    )

    rendered = render_prompt_bundle(plan)

    assert rendered["selected_pattern"] == "module-swarm"
    assert rendered["primary_mechanism"] == "delegate_task"
    assert rendered["proof_expectations"]
    assert all(lane["role"] for lane in rendered["lanes"])
    assert all(lane["scope_summary"] for lane in rendered["lanes"])
    assert all(lane["proof_expectations"] for lane in rendered["lanes"])



def test_render_prompt_contract_does_not_leak_paths_or_secrets():
    plan = select_worker_pattern(
        PatternRequest(
            objective="Compare two implementation approaches",
            variants_requested=2,
            notes=("api_key='should-not-appear'",),
        )
    )

    contract = render_prompt_contract(plan)

    assert "Role:" in contract
    assert "Scope:" in contract
    assert "Proof expectations:" in contract
    forbidden_user_path = "/".join(["", "Users", "stefan"])
    assert forbidden_user_path not in contract
    assert "should-not-appear" not in contract
    assert "api_key" not in contract.lower()



def test_render_delegate_specs_are_json_safe():
    plan = select_worker_pattern(
        PatternRequest(
            objective="Refactor auth and billing modules",
            scopes=("auth", "billing"),
        )
    )

    rendered = render_delegate_specs(plan)
    payload = json.dumps(rendered, sort_keys=True)

    assert '"mechanism": "delegate_task"' in payload
    assert all(task["goal"] for task in rendered["tasks"])
    assert all(task["context"] for task in rendered["tasks"])



def test_render_swarm_spec_is_dry_run_and_structured_first():
    plan = select_worker_pattern(
        PatternRequest(
            objective="Implement persistent review lane",
            scopes=("docs",),
            persistent_workers=True,
        )
    )

    rendered = render_swarm_spec(plan)

    assert rendered["mechanism"] == "swarm_profiles"
    assert rendered["dry_run"] is True
    assert rendered["workers"]
    assert all(worker["profile"] for worker in rendered["workers"])
    assert all(worker["command_argv"][:3] == ["hermes", "--profile", worker["profile"]] for worker in rendered["workers"])



def test_render_kanban_spec_builds_dependency_graph_for_durable_work():
    plan = select_worker_pattern(
        PatternRequest(
            objective="Ship phased migration",
            dependencies=("schema", "api", "cutover"),
            durable=True,
        )
    )

    rendered = render_kanban_spec(plan)

    assert rendered["mechanism"] == "kanban"
    assert rendered["dry_run"] is True
    assert [task["id"] for task in rendered["tasks"][:3]] == [
        "lane-1-phase-worker",
        "lane-2-phase-worker",
        "lane-3-phase-worker",
    ]
    assert rendered["tasks"][1]["depends_on"] == ["lane-1-phase-worker"]
    assert rendered["tasks"][2]["depends_on"] == ["lane-2-phase-worker"]
