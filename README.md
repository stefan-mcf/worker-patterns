# Worker Patterns

Worker Patterns is a small, runtime-agnostic planning layer for deciding **what shape agent work should take** before any worker is launched.

Agent systems often have plenty of execution machinery: model-backed profiles, subagents, queues, tools, MCP servers, browser workers, schedulers, or long-running profile processes. Those pieces answer *who can run the work*. Worker Patterns answers the earlier question: *how should the work be structured so execution is reviewable, recoverable, and not ad hoc?*

Given a task, the selector classifies the work into a pattern such as `sequential`, `module-swarm`, `blueprint-fanout`, `phased-assembly`, `twin-inspection`, `recovery-lane`, or `bridge_lane`. Each pattern describes the lane structure, review expectations, coordination boundaries, and safety checks for that kind of work.

The package is intentionally conservative. It selects patterns and renders dry-run plans; it does **not** launch workers, mutate runtime configuration, use credentials, push branches, publish packages, or decide that work is complete.

## Why worker patterns?

Most agent runtimes make it easy to send work to a capable model or worker. That is useful, but it can make orchestration collapse into ad hoc routing: pick a strong profile, send a prompt, and hope the worker infers whether the task needs decomposition, independent review, recovery, or ordered phases.

That breaks down when work spans multiple modules, has dependencies, needs parallel exploration, requires proof, or is continuing from a failed attempt. The shape of the work should be explicit before execution starts.

Worker Patterns adds a planning contract in front of runtime execution:

- classify the task shape before assigning lanes;
- make decomposition explicit instead of burying it inside a prompt;
- separate builder, reviewer, curator, recovery, and bridge responsibilities;
- define when work should be sequential, parallel, phased, inspected, or recovered;
- preserve safety boundaries for high-risk or stale work;
- produce stable JSON that other tools can inspect before running anything;
- keep runtime/profile/model policy configurable instead of hard-coded into each prompt.

In short: workers decide *what to do inside a lane*. Worker patterns decide *which lanes should exist, why they exist, and how they should be checked*.

## Features

- Worker-pattern selection for common agent work shapes.
- Runtime-neutral JSON output for CLI, MCP, and adapter consumption.
- Prompt and execution-plan rendering from selected patterns.
- Optional stdio MCP bridge with two tools:
  - `select_worker_pattern`
  - `render_execution_plan`
- Policy-driven profile/lane hints via YAML.
- Opt-in JSONL tracing with common secret redaction.
- Local smoke scripts that avoid writing to a real runtime home.

## Install from a fresh clone

```bash
git clone https://github.com/stefan-mcf/worker-patterns.git
cd worker-patterns
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .[dev]
```

Smoke-test the installed console entrypoints without relying on `PYTHONPATH`:

```bash
scripts/smoke_install.sh
```

## CLI quickstart

```bash
worker-pattern select \
  "Refactor auth and billing modules, then run tests" \
  --scope auth \
  --scope billing \
  --review-required

worker-pattern render \
  "Compare two frontend designs and choose one" \
  --variant-count 2

worker-pattern render-execution-plan \
  "Keep implementation and review lanes separate" \
  --review-required
```

Use `--text` on `select` for a terminal-readable summary, or the default JSON output for automation.

## MCP executable

After installation, run the stdio MCP surface with:

```bash
worker-pattern-mcp
```

From a source checkout, this equivalent also works:

```bash
python -m worker_patterns.mcp_server
```

The MCP bridge writes protocol messages to stdout and keeps debug traces out of stdout. A local temp-home proof is available:

```bash
scripts/smoke_hermes_temp_home_mcp.sh
```

## Supported patterns

- `sequential`: one bounded lane for small/simple work.
- `module-swarm`: disjoint scopes that can be decomposed into many independent lanes, including large decompositions such as 32 module lanes, then executed in bounded waves with integration/review gates.
- `blueprint-fanout`: competing designs or approaches, followed by curation.
- `phased-assembly`: ordered dependency waves for migrations/refactors.
- `twin-inspection`: implementation plus independent review/test verification.
- `recovery-lane`: narrow continuation/repair after failure or stale work.
- `bridge_lane`: controlled landing path for high-risk or canonical recovery work.

See [`docs/worker-patterns.md`](docs/worker-patterns.md) for selection criteria and examples.

## Runtime adapters

Worker Patterns is not an agent runtime. It emits an inspectable contract that other systems can consume:

- a CLI can print JSON for shell automation;
- an MCP server can expose pattern selection as a tool;
- a queue or task board can translate lanes into durable work items;
- a profile-based runtime can map lanes to named workers;
- Hermes Agent can consume the same plan through the optional Hermes adapter.

Hermes support is intentionally treated as an adapter, not the product boundary. See [`docs/runtime-adapters.md`](docs/runtime-adapters.md) for the generic adapter contract and [`docs/hermes-integration.md`](docs/hermes-integration.md) for the optional Hermes-specific notes.

## Safety boundary

This repository is a planning and adapter layer, not an execution system. It does not:

- launch workers;
- own queues or schedulers;
- mutate global runtime or profile configuration;
- create tasks in external planning systems;
- execute browser actions;
- use credentials;
- publish packages, push branches, or open pull requests.

Execution remains the responsibility of the runtime and the human-approved workflow that consumes these dry-run plans.

## Documentation

- [`docs/architecture.md`](docs/architecture.md): package components and data flow.
- [`docs/worker-patterns.md`](docs/worker-patterns.md): pattern taxonomy and routing rules.
- [`docs/cli.md`](docs/cli.md): command reference and output modes.
- [`docs/mcp.md`](docs/mcp.md): stdio MCP bridge.
- [`docs/runtime-adapters.md`](docs/runtime-adapters.md): generic adapter contract.
- [`docs/hermes-integration.md`](docs/hermes-integration.md): optional Hermes integration notes.
- [`docs/configuration.md`](docs/configuration.md): policy files, profile hints, tracing.
- [`docs/browser-routing.md`](docs/browser-routing.md): browser-capable route boundary.
- [`docs/dev-logging.md`](docs/dev-logging.md): opt-in trace logging.
- [`docs/elastic-worker-lanes.md`](docs/elastic-worker-lanes.md): future elastic-lane design notes.
- [`docs/module-swarm-hardening.md`](docs/module-swarm-hardening.md): scale and safety policy.
- [`docs/install-skill.md`](docs/install-skill.md): optional Hermes skill installation.

## Development

```bash
python -m pip install -e .[dev]
python -m ruff check .
python -m pytest
scripts/smoke_install.sh
scripts/smoke_hermes_temp_home_mcp.sh
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for contributor workflow and release checks.

## Compatibility

The canonical Python import path is now `worker_patterns`. A thin `hermes_worker_patterns` compatibility shim remains for existing integrations during the initial rebrand window.

## Maturity

Initial public release. The CLI and MCP surfaces are usable, but the package should be treated as alpha until broader external usage validates the policy defaults.

## License

MIT. See [`LICENSE`](LICENSE).
