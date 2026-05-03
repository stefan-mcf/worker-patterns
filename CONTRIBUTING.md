# Contributing

Thanks for considering a contribution to Hermes Worker Patterns.

## Development setup

```bash
git clone https://github.com/stefan-mcf/hermes-worker-patterns.git
cd hermes-worker-patterns
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
- Do not add code that mutates global Hermes configuration as a side effect of selection.
- Add or update tests for behavior changes.
- Keep CLI and docs synchronized.
- Avoid environment-specific paths, credentials, or private local assumptions.
- Mark future execution ideas as roadmap/design notes rather than implemented behavior.

## Policy changes

Policy files live in `policies/` for source-tree readability and are mirrored into package data under `src/hermes_worker_patterns/policies/` for installed use. If a policy file changes, update both copies and run the install smoke checks.

## Release checklist

1. Update `CHANGELOG.md`.
2. Run lint, tests, smoke scripts, and build checks.
3. Validate a clean clone install.
4. Confirm the tracked-file secret/private-term scan is clean.
5. Tag only after CI passes on the release commit.
