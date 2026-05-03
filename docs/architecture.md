# Architecture

Worker Patterns is a small planning package. It converts a task description into an inspectable worker-pattern plan that any compatible runtime can consume after review.

The package has three layers:

1. **Pattern selection**: decide the work shape.
2. **Lane contract**: describe roles, scopes, review expectations, and runtime hints.
3. **Adapters/renderers**: emit JSON, prompt bundles, MCP responses, or dry-run execution plans for a caller to inspect.

It is not an execution runtime. It does not launch workers, mutate config, create durable tasks, or mark work complete.

## Components

- `schemas.py`: typed request, selection, lane, plan, runtime mapping, and execution-plan models.
- `policy.py`: loads pattern-selection policy from packaged YAML data.
- `profile_policy.py`: maps logical worker roles to portable profile/lane hints and optional caller-supplied roster entries.
- `selector.py`: scores the request, selects a base pattern, adds overlays, and produces a `PatternPlan`.
- `prompt_renderer.py`: renders role prompts and JSON specs for selected lanes.
- `execution_plan.py`: renders dry-run runtime plans.
- `adapter.py`: maps selected patterns to runtime-neutral mechanisms such as direct, delegated, profile-backed, or durable task execution.
- `cli.py`: exposes `worker-pattern` commands.
- `mcp_server.py`: exposes stdio MCP tools.
- `trace.py`: optional JSONL diagnostics with secret redaction.

## Data flow

1. Caller builds a `PatternRequest` from CLI args, MCP input, or Python code.
2. Selector extracts task signals and scores candidate patterns.
3. The selected pattern is decorated with overlays such as `twin-inspection` when review is requested.
4. Logical lanes are assigned role/profile hints from policy.
5. Optional roster mapping may translate logical lanes into concrete profile names supplied by the caller.
6. Renderer emits JSON, text, prompts, or dry-run execution-plan data.
7. A separate runtime decides whether and how to execute the plan.

## Runtime boundary

Worker Patterns owns the planning contract. The runtime owns execution.

Worker Patterns owns:

- pattern selection;
- lane decomposition;
- review/recovery/phasing expectations;
- runtime-neutral mechanism hints;
- dry-run prompt/spec rendering;
- traceable evidence about the selection.

The caller/runtime owns:

- launching workers;
- coordinating processes or profiles;
- creating durable tasks;
- deciding whether rendered commands are safe;
- committing, pushing, publishing, or deploying;
- deciding when work is actually complete.

## Policy data

Source-readable policy lives in `policies/`. The same YAML files are packaged under `src/worker_patterns/policies/` so installed console scripts work from wheels and clean clones.

## Compatibility

The canonical module is `worker_patterns`. The `hermes_worker_patterns` module remains as a thin compatibility shim during the rebrand window. New integrations should use `worker_patterns`.
