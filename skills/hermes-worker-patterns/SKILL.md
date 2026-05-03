---
name: hermes-worker-patterns
description: "Choose Hermes execution shapes: direct, /goal, delegate_task, persistent profiles, or durable task graphs."
version: 0.2.0
author: Stefan McFeeters
license: MIT
metadata:
  hermes:
    tags: [hermes, worker-patterns, delegation, swarm, goal, kanban]
---

# Hermes Worker Patterns

Use this skill when a user asks for the best Hermes worker pattern, wants work split into Hermes lanes, or asks whether to use direct execution, `/goal`, `delegate_task`, persistent profiles, or a durable task graph.

The selector chooses execution shape only. Hermes and the operator remain responsible for execution.

## Local package

From a source checkout:

```bash
python -m pip install -e .[dev]
```

Prefer the installed console script:

```bash
worker-pattern select "<objective>" --scope "<scope>" --tests-required
worker-pattern render-execution-plan "<objective>" --scope "<scope>"
```

Fallback from source:

```bash
PYTHONPATH=src python -m hermes_worker_patterns.cli select "<objective>" --scope "<scope>" --text
```

## Decision rule

1. Small, bounded, single scope -> `sequential` -> current Hermes turn; promote to `/goal` if it spans turns.
2. Disjoint modules/files/scopes -> `module-swarm` -> bounded parallel lanes or persistent profiles when the operator explicitly wants persistent workers.
3. Competing approaches -> `blueprint-fanout` -> variants plus curator.
4. Dependency waves or migrations -> `phased-assembly` -> ordered phases or durable task graph.
5. Needs independent review/test/security proof -> overlay `twin-inspection`.
6. Failed/stale/blocked continuation -> `recovery-lane`.
7. Critical canonical landing -> `bridge_lane`.

## Persistent profiles

If the caller wants concrete persistent profile mapping, set:

```bash
export HERMES_SWARM_ROSTER_PATH=/path/to/swarm.yaml
```

Without a roster path, the selector emits portable logical profile hints.

## Review expectations

- Keep reviewer lanes independent from builder lanes.
- State checks/tests/review evidence in the final response.
- If evidence is missing, say so and recommend the next Hermes primitive.

## Boundaries

This skill and package do not own queues, launchers, task completion, browser automation, global Hermes configuration, package publishing, branch pushes, or external mutations. They select and render dry-run plans only.
