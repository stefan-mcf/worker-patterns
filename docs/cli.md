# CLI Reference

The package installs one primary CLI:

```bash
worker-pattern --help
```

## `select`

Select a worker pattern and render the plan as JSON by default.

```bash
worker-pattern select "Update README and add tests" --scope docs --tests-required
```

Useful flags:

- `--scope <name>`: repeatable scope/module hint.
- `--dependency <name>`: repeatable dependency/phase hint.
- `--review-required`: request independent inspection.
- `--tests-required`: request test verification.
- `--persistent-workers`: allow persistent swarm-profile mapping in the rendered plan.
- `--text`: render a terminal-readable summary.

## `render`

Render a combined prompt bundle for the selected lanes.

```bash
worker-pattern render "Compare two implementation approaches" --variant-count 2
```

## `render-prompts`

Render lane prompts intended for worker handoff.

```bash
worker-pattern render-prompts "Refactor parser and renderer" --scope parser --scope renderer
```

## `render-execution-plan`

Render dry-run runtime execution-plan commands.

```bash
worker-pattern render-execution-plan \
  "Keep implementation and review lanes separate" \
  --review-required
```

The rendered commands are previews. The package does not execute them.

## JSON stability

The CLI is designed to produce stable JSON for automation where practical. Human-readable text output is for convenience and may change more freely.
