# Worker Patterns

Worker patterns describe the shape of agent work. They do not execute work; they tell a caller how work should be organized before the caller chooses workers, models, tools, or task systems.

## Pattern taxonomy

### `sequential`

Use for small, bounded work with one clear scope and low coordination cost.

Typical mapping: one current-session lane, optionally promoted to a multi-step continuation if it spans turns.

### `module-swarm`

Use when work can be split by disjoint scopes such as independent packages, modules, services, or documentation sections.

This is the same core concept that existed under Antaeus: a module-swarm is a **decomposition contract** for many independent lanes, not just a small parallel-task shortcut. A request with 32 independent modules can produce 32 builder lanes while still limiting how many lanes are active at once.

Typical mapping: bounded parallel lanes or persistent profiles, followed by integration/review.

Scale behavior:

- requested lanes represent the decomposition count;
- `max_parallel_lanes` represents the active concurrency cap requested by the caller/runtime;
- low-risk, explicitly disjoint scopes can run larger active waves, e.g. 32 requested lanes with 8 active at a time -> 4 waves;
- high-risk or ambiguous scope ownership falls back to conservative waves, e.g. 32 requested lanes with 4 active at a time -> 8 waves;
- integration and review remain separate from builder lanes, with per-wave integration when risk is high.

### `blueprint-fanout`

Use when the task benefits from multiple competing approaches before choosing one.

Typical mapping: variant lanes plus curator lane.

### `phased-assembly`

Use for dependency-ordered work where one phase must land before the next.

Typical mapping: ordered phases or a durable task graph.

### `twin-inspection`

Use as an overlay when independent review or test verification matters.

Typical mapping: implementation lane plus independent reviewer/tester lane.

### `recovery-lane`

Use for stalled, failed, or stale work that needs narrow diagnosis before more edits.

Typical mapping: one strong recovery lane, then normal planning after cause is known.

### `bridge_lane`

Use for high-risk canonical landing work where the final handoff needs explicit acceptance criteria.

Typical mapping: narrow landing lane with review evidence.

## Selection inputs

Important request fields include:

- objective text;
- scopes;
- dependencies;
- risk level;
- review/test requirements;
- requested variants;
- durable/persistent-worker flags;
- recovery flag;
- max parallel lane count.

## Example

```bash
worker-pattern select \
  "Refactor auth and billing modules, then run tests" \
  --scope auth \
  --scope billing \
  --review-required
```

The selector should prefer a decomposed pattern because the scopes are independent and review is required.

## Boundary

The output is advisory and dry-run safe. It may include command previews or runtime hints, but it does not run them.
