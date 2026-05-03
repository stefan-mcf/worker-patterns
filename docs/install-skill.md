# Optional Hermes Skill Installation

This repository includes an optional Hermes skill source at:

```text
skills/hermes-worker-patterns/SKILL.md
```

Install it only if you want a Hermes profile to remember the worker-pattern selector workflow.

## Manual install

Copy the skill into the target Hermes profile's skills directory, for example:

```bash
mkdir -p ~/.hermes/skills/hermes-worker-patterns
cp skills/hermes-worker-patterns/SKILL.md ~/.hermes/skills/hermes-worker-patterns/SKILL.md
```

If your Hermes profile stores skills elsewhere, use that profile's configured skill directory.

## Verify package entrypoints

```bash
python -m pip install -e .[dev]
worker-pattern select "small docs update" --text
```

## Boundary

The skill should call the selector and interpret dry-run outputs. It should not install global profiles, mutate Hermes config, launch workers as a side effect of selection, or create durable tasks without explicit operator intent.
