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
2. Disjoint modules/files/scopes -> `module-swarm` -> many coordinated lanes over disjoint bounded scopes under one shared objective, then bounded active concurrency/waves/integration gates. Keep the name because “swarm” conveys the large-worker shape, but distinguish it from runtime-specific persistent profiles, which are identities that may execute lanes.
3. Competing approaches -> `blueprint-fanout` -> variants plus curator.
4. Dependency waves or migrations -> `phased-assembly` -> ordered phases or durable task graph.
5. Needs independent review/test/security proof -> overlay `twin-inspection`.
6. Failed/stale/blocked continuation -> `recovery-lane`.
7. Critical canonical landing -> `bridge_lane`.

## Persistent profiles

If the caller wants concrete persistent profile mapping, provide a roster file, set the compatible roster variable, and pass the explicit persistent-worker flag:

```bash
export HERMES_SWARM_ROSTER_PATH=/path/to/swarm.yaml
worker-pattern select "<objective>" --scope backend --scope frontend --persistent-workers --tests-required --text
```

Pitfall: mentioning persistent workers in the objective text is not enough. Without `--persistent-workers`, the selector intentionally emits portable logical aliases such as `worker-code-fast`; with `--persistent-workers` plus `HERMES_SWARM_ROSTER_PATH`, it maps lanes onto concrete runtime profiles from the supplied roster.

Smoke-test local persistent mapping with a harmless dry-run before claiming setup is complete:

```bash
HERMES_SWARM_ROSTER_PATH=/path/to/swarm.yaml \
  worker-pattern select "implement backend frontend docs review in parallel" \
  --scope backend --scope frontend --scope docs --scope review \
  --persistent-workers --tests-required --text
```

Without a roster path and `--persistent-workers`, the selector emits portable logical profile hints.

Policy naming split to remember:
- Public policy files use runtime-agnostic aliases such as `worker-code-fast`, `worker-code-premium`, `worker-general-premium`, and `premium_code_cap`.
- Private/local policy overlays may contain actual runtime profile names, model names, provider names, or machine-specific rosters; keep those files outside git or under ignored `*.local.yaml`/`*.private.yaml` paths.
- If asked whether a specific local model/profile is active, inspect the operator's private roster/config and the installed editable package pointer before answering; do not hardcode private model/profile names into public policy.

For persistent runtime workers, smoke-test provider-risky lanes before critical assignment and keep fallbacks ready for transient provider/capacity failures. If a lane must be swapped, preserve the user's scope boundary, verify provider auth/config, and run a one-shot marker smoke before reuse.

Before relying on background worker processes, verify each process actually starts and has the skills/tools named in the prompt. Profile-local skill registries can differ from the coordinator; workers may exit immediately with `Unknown skill(s)` and produce no useful output. Capture exit status/stdout/stderr and require an explicit artifact or report before counting the lane as contribution. If workers fail to launch, continue in the controller lane and use a later reviewer lane rather than claiming worker coverage happened.

Observed hardening fix: persistent profiles can have isolated skill stores. A skill that exists in the coordinator/default profile may be unknown inside a worker profile. If you plan to pass `--skills ...` to persistent profiles, preflight with a cheap marker run and, when appropriate, sync only the required local skills into the target profiles using the runtime's profile-management command or an operator-local script.

Then verify exact profile+skill loading before assigning work:

```bash
hermes --profile <profile> --skills worker-patterns chat -Q --max-turns 2 -q 'Reply exactly: WORKER_SKILL_OK'
```

If the marker does not appear with exit code 0, do not launch that lane with those skills. Either fix the profile-local skill store or remove `--skills` and put the required procedure directly in the worker prompt.

## Review expectations

- Keep reviewer lanes independent from builder lanes.
- State checks/tests/review evidence in the final response.
- If evidence is missing, say so and recommend the next runtime mechanism.
- For exact-tranche implementation requests, run the selector first and obey the selected shape instead of forcing a swarm because the user mentioned workers. If the selector returns `sequential` with `twin-inspection`, implement in the controller/builder lane, then run an independent reviewer lane for spec and quality. Do not claim persistent worker usage unless real worker processes were launched.
- When an independent reviewer finds a minor fix before commit, apply it and rerun the focused/full checks before the final tranche commit.

## Boundaries

This skill and package do not own queues, launchers, task completion, browser automation, global runtime configuration, package publishing, branch pushes, or external mutations. They select and render dry-run plans only.
