from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class WorkerPattern(str, Enum):
    SEQUENTIAL = "sequential"
    MODULE_SWARM = "module-swarm"
    BLUEPRINT_FANOUT = "blueprint-fanout"
    PHASED_ASSEMBLY = "phased-assembly"
    TWIN_INSPECTION = "twin-inspection"
    RECOVERY_LANE = "recovery-lane"
    BRIDGE_LANE = "bridge_lane"


class ExecutionMechanism(str, Enum):
    DIRECT = "direct"
    GOAL = "goal"
    DELEGATE_TASK = "delegate_task"
    SWARM_PROFILES = "swarm_profiles"
    KANBAN = "kanban"


@dataclass(frozen=True)
class PatternRequest:
    objective: str
    scopes: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    risk_level: str = "normal"
    review_required: bool = True
    tests_required: bool = False
    variants_requested: int = 0
    durable: bool = False
    persistent_workers: bool = False
    recovery: bool = False
    max_parallel_lanes: int = 4
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.objective.strip():
            raise ValueError("objective is required")
        if self.max_parallel_lanes < 1:
            raise ValueError("max_parallel_lanes must be >= 1")


@dataclass(frozen=True)
class ModelPolicy:
    disable_reasoning: bool = False


@dataclass(frozen=True)
class PatternLane:
    role: str
    count: int = 1
    scope: tuple[str, ...] = ()
    purpose: str = ""
    runtime_hint: str = ""
    selected_profile: str = ""  # New field
    fallback_profiles: tuple[str, ...] = ()  # New field
    toolsets: tuple[str, ...] = ()  # New field
    model_policy: ModelPolicy = field(default_factory=ModelPolicy)  # New field


@dataclass(frozen=True)
class PatternSelection:
    selected_pattern: WorkerPattern
    overlays: tuple[WorkerPattern, ...] = ()
    reason: str = ""
    dimensions: dict[str, int] = field(default_factory=dict)
    matched_signals: tuple[str, ...] = ()
    scores: dict[str, int] = field(default_factory=dict)
    score_adjustments: dict[str, int] = field(default_factory=dict)
    selection_source: str = ""
    selector_version: str = ""
    override: str = ""
    override_requested_by: str = ""
    override_reason: str = ""
    invalid_override_reason: str = ""


@dataclass(frozen=True)
class RuntimeMapping:
    primary_mechanism: ExecutionMechanism
    fallback_mechanisms: tuple[ExecutionMechanism, ...]
    invocation_hint: str
    prompt_contract: str


@dataclass(frozen=True)
class ModuleSwarmScalePolicy:
    """Scale policy for large module-swarm decompositions.

    Preserves high-lane module-swarm testing as safe policy
    rather than executable concurrency.
    requested vs. how many should run concurrently, organized into
    waves with integrator placement.
    """
    requested_lane_count: int
    max_active_lanes: int
    waves_required: int
    wave_size: int
    profile_pool_strategy: str
    integrator_per_wave: bool


@dataclass(frozen=True)
class PatternPlan:
    request: PatternRequest
    selection: PatternSelection
    lanes: tuple[PatternLane, ...]
    runtime_mapping: RuntimeMapping
    proof_expectations: tuple[str, ...]
    safety_notes: tuple[str, ...] = ()
    role_rules: dict[str, Any] = field(default_factory=dict) # New field
    profile_mapping: dict[str, Any] = field(default_factory=dict) # New field
    module_swarm_scale: ModuleSwarmScalePolicy | None = None  # New field

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Backwards-compatible aliases for older integrations.
HermesMapping = RuntimeMapping
