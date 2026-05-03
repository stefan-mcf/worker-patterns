# Hermes Worker Patterns

Hermes Worker Patterns is a compact taxonomy and selector for deciding **how agent work should be shaped** before execution starts.

Given a task, it classifies the work into a worker pattern such as `sequential`, `module-swarm`, `blueprint-fanout`, `phased-assembly`, `twin-inspection`, `recovery-lane`, or `bridge_lane`. Each pattern describes the lane structure, review expectations, and safety boundaries for that kind of work.

The package is intentionally conservative. It selects patterns and renders dry-run plans; it does **not** launch workers, mutate Hermes configuration, use credentials, push branches, publish packages, or decide that work is complete.

## Features

- Worker-pattern selection for common agent work shapes.
- Stable JSON output for CLI and tool consumption.
- Prompt and execution-plan rendering from selected patterns.
- Optional stdio MCP bridge with two tools:
  - `select_worker_pattern`
  - `render_execution_plan`
- Policy-driven profile/lane hints via YAML.
- Opt-in JSONL tracing with common secret redaction.
- Local smoke scripts that avoid writing to a real Hermes home.

## Install from a fresh clone

```bash
git clone https://github.com/stefan-mcf/hermes-worker-patterns.git
cd hermes-worker-patterns
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
python -m hermes_worker_patterns.mcp_server
```

The MCP bridge writes protocol messages to stdout and keeps debug traces out of stdout. A local temp-home proof is available:

```bash
scripts/smoke_hermes_temp_home_mcp.sh
```

## Supported patterns

- `sequential`: one bounded lane for small/simple work.
- `module-swarm`: disjoint scopes that can be decomposed into parallel lanes.
- `blueprint-fanout`: competing designs or approaches, followed by curation.
- `phased-assembly`: ordered dependency waves for migrations/refactors.
- `twin-inspection`: implementation plus independent review/test verification.
- `recovery-lane`: narrow continuation/repair after failure or stale work.
- `bridge_lane`: controlled landing path for high-risk or canonical recovery work.

See [`docs/worker-patterns.md`](docs/worker-patterns.md) for selection criteria and examples.

## Safety boundary

This repository is an adapter layer, not an agent runtime. It does not:

- launch workers;
- own queues or schedulers;
- mutate global Hermes config or profile config;
- create tasks in external planning systems;
- execute browser actions;
- use credentials;
- publish packages, push branches, or open pull requests.

Execution remains the responsibility of Hermes and the human-approved workflow that consumes these dry-run plans.

## Documentation

- [`docs/architecture.md`](docs/architecture.md): package components and data flow.
- [`docs/worker-patterns.md`](docs/worker-patterns.md): pattern taxonomy and routing rules.
- [`docs/cli.md`](docs/cli.md): command reference and output modes.
- [`docs/mcp.md`](docs/mcp.md): stdio MCP bridge.
- [`docs/hermes-integration.md`](docs/hermes-integration.md): consuming plans in Hermes.
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

## Maturity

Initial public release. The CLI and MCP surfaces are usable, but the package should be treated as alpha until broader external usage validates the policy defaults.

## License

MIT. See [`LICENSE`](LICENSE).
