---
name: worker-patterns
description: "Choose worker-pattern execution shapes for agent runtimes: sequential, module-swarm, fanout, phased, inspection, recovery, or bridge lanes."
version: 0.3.0
author: Stefan McFeeters
license: MIT
metadata:
  hermes:
    tags: [worker-patterns, agents, delegation, swarm, planning]
---

# Worker Patterns

Use this skill when a user asks how agent work should be shaped before execution: whether it should be direct, decomposed into parallel lanes, split into competing variants, phased, independently reviewed, recovered, or bridged through a high-risk landing lane.

The selector chooses execution shape only. The caller/runtime remains responsible for launching workers, coordinating outputs, and judging completion.

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
PYTHONPATH=src python -m worker_patterns.cli select "<objective>" --scope "<scope>" --text
```

## Decision rule

1. Small, bounded, single scope -> `sequential` -> one current-session lane.
2. Disjoint modules/files/scopes -> `module-swarm` -> bounded parallel lanes or persistent profiles when the operator explicitly wants persistent workers.
3. Competing approaches -> `blueprint-fanout` -> variants plus curator.
4. Dependency waves or migrations -> `phased-assembly` -> ordered phases or durable task graph.
5. Needs independent review/test/security proof -> overlay `twin-inspection`.
6. Failed/stale/blocked continuation -> `recovery-lane`.
7. Critical canonical landing -> `bridge_lane`.

## Persistent profiles

If the caller wants concrete persistent profile mapping, provide a roster file and set the compatible roster variable:

```bash
export HERMES_SWARM_ROSTER_PATH=/path/to/swarm.yaml
```

Without a roster path, the selector emits portable logical profile hints.

## Review expectations

- Keep reviewer lanes independent from builder lanes.
- State checks/tests/review evidence in the final response.
- If evidence is missing, say so and recommend the next runtime mechanism.

## Boundaries

This skill and package do not own queues, launchers, task completion, browser automation, global runtime configuration, package publishing, branch pushes, or external mutations. They select and render dry-run plans only.
