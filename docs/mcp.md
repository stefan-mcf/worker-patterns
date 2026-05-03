# MCP Bridge

Worker Patterns includes a stdio MCP executable:

```bash
worker-pattern-mcp
```

It can also be run from source:

```bash
python -m worker_patterns.mcp_server
```

## Tools

### `select_worker_pattern`

Inputs mirror the CLI selection request: objective, scopes, dependencies, review/test flags, risk level, persistence flags, and lane count.

Output is a serialized worker-pattern plan.

### `render_execution_plan`

Inputs mirror selection plus rendering options.

Output is a dry-run execution plan that a caller can inspect before choosing whether to run any runtime command.

## Protocol boundary

MCP protocol messages use stdout. Optional debug traces are file-backed and must not be written to stdout because that would corrupt the stdio protocol.

## Temp-home proof

Run:

```bash
scripts/smoke_hermes_temp_home_mcp.sh
```

The script uses a temporary `HERMES_HOME` and verifies the bridge without mutating a real runtime home.
