"""Worker-pattern selector and runtime adapter."""

from .adapter import adapt_to_runtime, dry_run_execution_plan
from .execution_plan import RuntimeExecutionPlan, render_execution_plan
from .runtime_tool import worker_pattern_tool, worker_pattern_tool_json
from .schemas import ExecutionMechanism, PatternPlan, PatternRequest, WorkerPattern
from .selector import select_worker_pattern

__all__ = [
    "ExecutionMechanism",
    "PatternPlan",
    "PatternRequest",
    "WorkerPattern",
    "RuntimeExecutionPlan",
    "adapt_to_runtime",
    "dry_run_execution_plan",
    "render_execution_plan",
    "render_execution_plan_bridge",
    "select_worker_pattern",
    "select_worker_pattern_bridge",
    "worker_pattern_tool",
    "worker_pattern_tool_json",
    # Backwards-compatible names.
    "HermesExecutionPlan",
    "adapt_to_hermes",
]


HermesExecutionPlan = RuntimeExecutionPlan
adapt_to_hermes = adapt_to_runtime


def __getattr__(name: str):
    if name in {"render_execution_plan_bridge", "select_worker_pattern_bridge"}:
        from .mcp_server import render_execution_plan_bridge, select_worker_pattern_bridge

        return {
            "render_execution_plan_bridge": render_execution_plan_bridge,
            "select_worker_pattern_bridge": select_worker_pattern_bridge,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
