from pathlib import Path

import pytest
from worker_patterns.profile_policy import WorkerProfilesPolicy
from worker_patterns.schemas import PatternLane

ROOT = Path(__file__).resolve().parents[1]
LIVE_POLICY = ROOT / "policies" / "worker_profiles.yaml"


@pytest.fixture
def policy_path(tmp_path):
    # Create a dummy worker_profiles.yaml for testing
    content = """
    roles:
      planner-worker:
        preferred_profile: planner-premium
        fallback_profiles: [default]
        model_policy:
          disable_reasoning: false
        toolsets: [terminal, file, web, session_search, skills, delegation]

      code-worker:
        preferred_profile: worker-code-fast
        fallback_profiles: [worker-code-premium, worker-general-premium]
        model_policy:
          disable_reasoning: true
        toolsets: [terminal, file, web, session_search, skills]

      test-worker:
        preferred_profile: worker-code-fast
        fallback_profiles: [worker-general-premium, default]
        model_policy:
          disable_reasoning: true
        toolsets: [terminal, file, web, session_search, skills]

      review-worker:
        preferred_profile: worker-review-premium
        fallback_profiles: [worker-general-premium, default]
        model_policy:
          disable_reasoning: false
        toolsets: [terminal, file, web, session_search, skills, github]

      integrator-worker:
        preferred_profile: worker-general-premium
        fallback_profiles: [default]
        model_policy:
          disable_reasoning: false
        toolsets: [terminal, file, web, session_search, skills, github, delegation]

      unknown-role:
        preferred_profile: default
        fallback_profiles: []
        model_policy:
          disable_reasoning: false
        toolsets: []

    escalation_policy:
      premium_escalation_profile: worker-general-premium
      module_swarm_default_profile: worker-code-fast
      code_heavy_profile: worker-code-premium
      premium_code_cap: 3
    """
    file_path = tmp_path / "worker_profiles.yaml"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def worker_profiles_policy(policy_path):
    return WorkerProfilesPolicy.load_from_yaml(policy_path)


def test_load_from_yaml(worker_profiles_policy):
    assert "planner-worker" in worker_profiles_policy.roles
    assert worker_profiles_policy.roles["planner-worker"].preferred_profile == "planner-premium"
    assert worker_profiles_policy.roles["planner-worker"].fallback_profiles == ["default"]
    assert "premium_escalation_profile" in worker_profiles_policy.escalation_policy.__dict__
    assert worker_profiles_policy.escalation_policy.premium_escalation_profile == "worker-general-premium"
    assert worker_profiles_policy.escalation_policy.premium_code_cap == 3


def test_select_profile_for_role_default(worker_profiles_policy):
    lane = worker_profiles_policy.select_profile_for_role("code-worker")
    assert lane.role == "code-worker"
    assert lane.selected_profile == "worker-code-fast"
    assert lane.fallback_profiles == ("worker-code-premium", "worker-general-premium")
    assert lane.toolsets == ("terminal", "file", "web", "session_search", "skills")
    assert lane.model_policy.disable_reasoning is True


def test_select_profile_for_role_premium_escalation(worker_profiles_policy):
    lane = worker_profiles_policy.select_profile_for_role("code-worker", is_premium_escalation=True)
    assert lane.selected_profile == "worker-general-premium"
    assert lane.fallback_profiles == ("worker-code-premium",)


def test_select_profile_for_role_module_swarm(worker_profiles_policy):
    lane = worker_profiles_policy.select_profile_for_role("code-worker", is_module_swarm=True)
    assert lane.selected_profile == "worker-code-fast"
    assert lane.fallback_profiles == ()
    assert lane.model_policy.disable_reasoning is True


def test_select_profile_for_role_code_heavy(worker_profiles_policy):
    lane = worker_profiles_policy.select_profile_for_role("planner-worker", is_code_heavy=True)
    assert lane.selected_profile == "worker-code-premium"
    assert lane.fallback_profiles == ("default",)


def test_select_profile_for_role_missing_role(worker_profiles_policy):
    lane = worker_profiles_policy.select_profile_for_role("non-existent-role")
    assert lane.role == "non-existent-role"
    assert lane.selected_profile == "default"
    assert lane.fallback_profiles == ()
    assert lane.toolsets == ()
    assert lane.model_policy.disable_reasoning is False


def test_select_profile_for_role_multiple_escalation_precedence(worker_profiles_policy):
    # Module-swarm execution takes precedence over premium and code-heavy
    # escalation so it remains the default low-cost parallel profile only and fails closed.
    lane = worker_profiles_policy.select_profile_for_role(
        "code-worker",
        is_premium_escalation=True,
        is_module_swarm=True,
        is_code_heavy=True,
    )
    assert lane.selected_profile == "worker-code-fast"
    assert lane.fallback_profiles == ()
    assert lane.model_policy.disable_reasoning is True

    lane = worker_profiles_policy.select_profile_for_role(
        "code-worker",
        is_module_swarm=True,
        is_code_heavy=True,
    )
    assert lane.selected_profile == "worker-code-fast"
    assert lane.fallback_profiles == ()
    assert lane.model_policy.disable_reasoning is True


def test_persistent_swarm_roster_maps_lanes_and_skips_parked(policy_path, tmp_path, monkeypatch):
    roster_path = tmp_path / "swarm.yaml"
    roster_path.write_text(
        """
workers:
  - id: swarm1
    name: Overflow
    role: Parked lane
    model: the default low-cost parallel profile
    preferredTaskTypes: [implementation]
    acceptsBroadcast: false
  - id: swarm5
    name: Builder
    role: Primary Builder
    model: provider-specific 2.5 Flash
    preferredTaskTypes: [implementation, feature]
    acceptsBroadcast: true
  - id: swarm6
    name: Reviewer
    role: Reviewer / Merge Gate
    model: premium
    preferredTaskTypes: [review, qa, verification]
    acceptsBroadcast: true
"""
    )
    monkeypatch.setenv("HERMES_SWARM_ROSTER_PATH", str(roster_path))
    policy = WorkerProfilesPolicy.load_from_yaml(policy_path)

    mapped, notes = policy.apply_canonical_swarm_roster(
        (
            PatternLane(role="builder", selected_profile="worker-code-fast"),
            PatternLane(role="reviewer", selected_profile="worker-review-premium"),
        )
    )

    assert [lane.selected_profile for lane in mapped] == ["swarm5", "swarm6"]
    assert "swarm1" not in [lane.selected_profile for lane in mapped]
    assert any("swarm.yaml remains worker identity" in note for note in notes)


def test_persistent_swarm_roster_skips_temporarily_unhealthy_profiles(policy_path, tmp_path, monkeypatch):
    roster_path = tmp_path / "swarm.yaml"
    roster_path.write_text(
        """
workers:
  - id: swarm6
    name: Reviewer
    role: Reviewer / Merge Gate
    preferredTaskTypes: [review, qa, verification]
    acceptsBroadcast: true
  - id: swarm11
    name: QA
    role: Secondary QA
    preferredTaskTypes: [review, qa, verification]
    acceptsBroadcast: true
"""
    )
    monkeypatch.setenv("HERMES_SWARM_ROSTER_PATH", str(roster_path))
    monkeypatch.setenv("HERMES_SWARM_UNHEALTHY_PROFILES", "swarm6")
    policy = WorkerProfilesPolicy.load_from_yaml(policy_path)

    mapped, notes = policy.apply_canonical_swarm_roster(
        (PatternLane(role="reviewer", selected_profile="worker-review-premium"),)
    )

    assert mapped[0].selected_profile == "swarm11"
    assert any("Skipped temporarily unhealthy swarm profiles: swarm6" in note for note in notes)


def test_persistent_swarm_roster_skips_provider_blocked_profile_alias(policy_path, tmp_path, monkeypatch):
    roster_path = tmp_path / "swarm.yaml"
    roster_path.write_text(
        """
workers:
  - id: swarm5
    name: Builder
    role: Primary Builder
    preferredTaskTypes: [implementation, feature]
    acceptsBroadcast: true
  - id: swarm10
    name: Sidekick
    role: Secondary Builder / Fast Patch Lane
    preferredTaskTypes: [implementation, patch]
    acceptsBroadcast: true
"""
    )
    monkeypatch.setenv("HERMES_SWARM_ROSTER_PATH", str(roster_path))
    monkeypatch.setenv("HERMES_SWARM_PROVIDER_BLOCKED_PROFILES", "swarm5")
    policy = WorkerProfilesPolicy.load_from_yaml(policy_path)

    mapped, notes = policy.apply_canonical_swarm_roster(
        (PatternLane(role="builder", selected_profile="worker-code-fast"),)
    )

    assert mapped[0].selected_profile == "swarm10"
    assert any("Skipped temporarily unhealthy swarm profiles: swarm5" in note for note in notes)


def test_live_policy_uses_public_profile_names_only():
    policy = WorkerProfilesPolicy.load_from_yaml(LIVE_POLICY)
    referenced_profiles = []
    for role_policy in policy.roles.values():
        referenced_profiles.append(role_policy.preferred_profile)
        referenced_profiles.extend(role_policy.fallback_profiles)
    referenced_profiles.extend(
        [
            policy.escalation_policy.premium_escalation_profile,
            policy.escalation_policy.code_heavy_profile,
            policy.escalation_policy.module_swarm_default_profile,
        ]
    )

    assert "worker-legacy-premium" not in referenced_profiles
    assert "planner-legacy-premium" not in referenced_profiles
