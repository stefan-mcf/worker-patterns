# Elastic Worker Lanes

This document records a future design direction. It is not implemented execution behavior.

## Problem

Named persistent profiles are useful for long-running work, but a named profile is a live identity, not the entire capacity model. A future launcher may need multiple isolated lane instances from the same profile class while respecting provider and concurrency limits.

## Concept

- Worker pattern: selected execution shape.
- Worker lane: role/scope in that shape.
- Worker profile template: model/tool policy used to instantiate lanes.
- Worker identity: a caller-owned runtime worker identity.

The selector can render lane specs that a separate approved execution layer may consume. The selector itself must not create profiles, mutate config, or launch workers.

## Example lane spec

```json
{
  "role": "builder",
  "scope": "auth",
  "profile_template": "code-worker",
  "max_active_instances": 2,
  "requires_review": true
}
```

## Constraints

- fail closed when capacity is unavailable;
- keep review independent from implementation;
- make all generated commands dry-run inspectable;
- never mutate global runtime configuration as a side effect of selection.
