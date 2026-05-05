# Contributing

Thanks for considering a contribution to Worker Patterns.

## Development setup

Use Python 3.10, 3.11, or 3.12. On systems where `python` points to an older
interpreter, use `python3.10`, `python3.11`, `python3.12`, or `uv venv --python 3.11 .venv` for the virtual environment step.

```bash
git clone https://github.com/stefan-mcf/worker-patterns.git
cd worker-patterns
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .[dev]
```

## Quality checks

Run all checks before opening a pull request:

```bash
python -m ruff check .
python -m pytest
scripts/smoke_install.sh
scripts/smoke_hermes_temp_home_mcp.sh
```

For packaging changes, also run:

```bash
python -m build
python -m twine check dist/*
```

## Pull request expectations

- Keep the package dry-run safe by default.
- Do not add code that mutates global runtime configuration as a side effect of selection.
- Add or update tests for behavior changes.
- Keep CLI and docs synchronized.
- Avoid environment-specific paths, credentials, or private local assumptions.
- Mark future execution ideas as roadmap/design notes rather than implemented behavior.

## Policy changes

Policy files live in `policies/` for source-tree readability and are mirrored into package data under `src/worker_patterns/policies/` for installed use. During the 0.1.x compatibility window, the same packaged policy files are also mirrored under `src/hermes_worker_patterns/policies/`; keep them synchronized until the shim is removed. If a policy file changes, update every mirror and run the install smoke checks.

## Release checklist

1. Update `CHANGELOG.md`.
2. Run lint, tests, smoke scripts, and build checks.
3. Validate a clean clone install.
4. Confirm the tracked-file secret/private-term scan is clean.
5. Confirm canonical `worker_patterns` and temporary `hermes_worker_patterns` packaged policies are synchronized, or remove the temporary shim before a breaking release.
6. Tag only after CI passes on the release commit.
