# Hermes Integration

Hermes is now documented as one optional runtime adapter for Worker Patterns, not as the product boundary.

Use this page only if you want Hermes Agent to consume Worker Patterns plans through the CLI, MCP bridge, or optional skill.

## Integration modes

1. CLI: call `worker-pattern select` or `worker-pattern render-execution-plan` and paste/use the output as context.
2. MCP: run `worker-pattern-mcp` as a stdio MCP server and call its tools from a compatible Hermes profile.
3. Optional skill: install `skills/worker-patterns/SKILL.md` into a Hermes profile if you want Hermes to remember the selector workflow.
4. Persistent profiles: map lanes to a caller-supplied worker roster when you explicitly want named persistent profile execution.

## Boundary

Worker Patterns owns:

- pattern selection;
- lane/profile hints;
- prompt rendering;
- dry-run execution-plan rendering;
- opt-in trace evidence.

Hermes owns:

- actually launching workers;
- coordinating long-running profiles;
- deciding whether rendered commands are safe;
- creating durable tasks;
- committing, pushing, publishing, or deploying;
- judging whether the final work is complete.

## Persistent worker roster

If a caller wants logical lanes mapped to concrete named workers, set:

```bash
export WORKER_PATTERNS_ROSTER_PATH=/path/to/workers.yaml
```

Without that variable, the selector keeps logical profile hints instead of guessing local profile names.

## Important stance

Worker Patterns should remain useful outside any single runtime. Do not add hidden dependencies on a local runtime home, profile directory, bot, task board, or private checkout. Runtime-specific behavior belongs in adapter surfaces or in caller-owned configuration.
