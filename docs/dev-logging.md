# Developer Logging

Worker Patterns has opt-in JSONL tracing for debugging selector behavior.

## Enable tracing

```bash
HERMES_WORKER_PATTERNS_DEBUG=1 \
HERMES_WORKER_PATTERNS_LOG="$(mktemp)" \
  worker-pattern select "Refactor parser and renderer" --scope parser --scope renderer
```

## Event contents

Trace events include:

- interface (`cli`, `python_api`, or `mcp_bridge`);
- bounded objective preview;
- objective hash;
- selected pattern;
- overlays;
- matched signals;
- score metadata;
- lane/profile summaries;
- duration;
- error metadata when selection fails.

## Redaction

Common credential-like tokens are redacted from previews. Redaction is a defensive aid, not a permission to place secrets in objectives. Avoid passing real credentials or sensitive user data to the selector.

## MCP note

When using the stdio MCP bridge, logs must be file-backed. Do not write debug output to stdout because stdout is reserved for MCP protocol messages.
