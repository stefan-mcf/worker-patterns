# Architecture

Hermes Worker Patterns is a small adapter package. It converts a task description into a worker-pattern plan that another Hermes workflow can inspect or execute after approval.

## Components

- `schemas.py`: typed request, selection, lane, plan, and execution-plan models.
- `policy.py`: loads pattern-selection policy from packaged YAML data.
- `profile_policy.py`: maps logical worker roles to profile/lane hints and optional swarm roster entries.
- `selector.py`: scores the request, selects a base pattern, adds overlays, and produces a `PatternPlan`.
- `prompt_renderer.py`: renders role prompts for selected lanes.
- `execution_plan.py`: renders dry-run Hermes command plans.
- `adapter.py`: maps pattern plans to Hermes-oriented primitives.
- `cli.py`: exposes `worker-pattern` commands.
- `mcp_server.py`: exposes stdio MCP tools.
- `trace.py`: optional JSONL diagnostics with secret redaction.

## Data flow

1. Caller builds a `PatternRequest` from CLI args, MCP input, or Python code.
2. Selector extracts task signals and scores candidate patterns.
3. The selected pattern is decorated with overlays such as `twin-inspection` when review is requested.
4. Logical lanes are assigned role/profile hints from policy.
5. Optional persistent swarm mapping may map logical lanes through a caller-supplied roster file.
6. Renderer emits JSON, text, prompts, or dry-run execution-plan commands.

## Safety model

The package never executes the rendered commands. A rendered plan is evidence for a later human-approved Hermes run, not an action by itself.

## Policy data

Source-readable policy lives in `policies/`. The same YAML files are packaged under `src/hermes_worker_patterns/policies/` so installed console scripts work from wheels and clean clones.
