# Hermes Integration

Hermes Worker Patterns is intended to be consumed by Hermes users as a planning and routing adapter.

## Integration modes

1. CLI: call `worker-pattern select` or `worker-pattern render-execution-plan` and paste/use the output as context.
2. MCP: run `worker-pattern-mcp` as a stdio MCP server and call its tools from a compatible client.
3. Optional skill: install `skills/hermes-worker-patterns/SKILL.md` into a Hermes profile if you want Hermes to remember the selector workflow.

## What the adapter owns

- pattern selection;
- lane/profile hints;
- prompt rendering;
- dry-run execution-plan rendering;
- opt-in trace evidence.

## What Hermes or the caller owns

- actually launching workers;
- coordinating long-running profiles;
- deciding whether rendered commands are safe;
- creating durable tasks;
- committing, pushing, publishing, or deploying.

## Persistent swarm roster

If a caller wants logical lanes mapped to a concrete Hermes swarm roster, set:

```bash
export HERMES_SWARM_ROSTER_PATH=/path/to/swarm.yaml
```

Without that variable, the selector keeps logical profile hints instead of guessing local profile names.
