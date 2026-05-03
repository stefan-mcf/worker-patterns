# Runtime Adapters

Worker Patterns emits an execution-shape contract. A runtime adapter decides how that contract maps onto a concrete execution system.

The package deliberately keeps that boundary explicit: selecting a pattern is not the same as running it.

## Generic adapter contract

A runtime adapter should consume:

- `selection.selected_pattern`: the chosen worker pattern.
- `selection.overlays`: review, recovery, or safety overlays.
- `lanes`: logical roles, scopes, purposes, selected profile hints, and fallback hints.
- `runtime_mapping.primary_mechanism`: the suggested execution mechanism.
- `runtime_mapping.fallback_mechanisms`: acceptable alternatives if the primary is unavailable.
- `runtime_mapping.prompt_contract`: a compact contract to pass to workers or task systems.
- `proof_expectations`: evidence expected before the work is considered complete.
- `safety_notes`: constraints the runtime must preserve.

## Adapter responsibilities

A runtime adapter may:

- map logical lanes to named profiles, workers, containers, queues, or agents;
- translate lanes into durable tasks;
- attach toolsets or model policies;
- decide which rendered commands, if any, are safe to run;
- collect outputs and proof artifacts.

A runtime adapter should not silently change the selected pattern. If it cannot honor the pattern, it should fail closed or ask the operator for a different execution shape.

## Mechanism meanings

- `direct`: run in one bounded lane or current session.
- `goal`: run as an ordered multi-step continuation in runtimes that support goal-style execution.
- `delegate_task`: run bounded parallel sub-lanes.
- `swarm_profiles`: map lanes to persistent named profiles or workers.
- `kanban`: translate lanes/phases into a durable task graph.

These mechanism names are intentionally broad. A runtime does not need to implement all of them; it can use the fallback list or expose only the mechanisms it supports.

## Roster mapping

If a runtime has concrete named workers, provide a roster file and point the selector at it with:

```bash
export HERMES_SWARM_ROSTER_PATH=/path/to/swarm.yaml
```

The environment variable name is kept for compatibility with the original Hermes adapter. The file content is treated as a caller-supplied roster; without it, Worker Patterns emits portable logical profile hints rather than guessing local profile names.

## Safety rule

Adapters should treat the output as a plan, not permission to execute. The caller/runtime must still decide:

- whether the task is authorized;
- whether credentials or side effects are allowed;
- whether the proposed lanes are safe;
- whether human review is required;
- whether outputs satisfy the proof expectations.
