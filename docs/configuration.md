# Configuration

Configuration is policy-driven and file-backed.

## Pattern policy

`policies/pattern_rules.yaml` controls pattern descriptions, scoring hints, proof expectations, and override metadata.

A packaged copy is stored at `src/hermes_worker_patterns/policies/pattern_rules.yaml` so installed builds work outside a source checkout.

## Worker profile policy

`policies/worker_profiles.yaml` maps logical roles to profile hints and model-policy expectations.

A packaged copy is stored at `src/hermes_worker_patterns/policies/worker_profiles.yaml`.

## Optional swarm roster

Set `HERMES_SWARM_ROSTER_PATH` to map logical lanes to a concrete Hermes swarm roster:

```bash
export HERMES_SWARM_ROSTER_PATH=/path/to/swarm.yaml
```

The roster is optional. Without it, outputs remain generic and portable.

## Temporarily skipped profiles

Callers can quarantine profiles for one run with:

```bash
export HERMES_SWARM_UNHEALTHY_PROFILES=swarm6,swarm11
```

Aliases also accepted:

- `HERMES_SWARM_BLOCKED_PROFILES`
- `HERMES_SWARM_PROVIDER_BLOCKED_PROFILES`

## Debug tracing

Tracing is off by default. Enable it explicitly:

```bash
HERMES_WORKER_PATTERNS_DEBUG=1 \
HERMES_WORKER_PATTERNS_LOG="$(mktemp)" \
  worker-pattern select "small docs update"
```

Trace events include bounded request metadata, selection scores, matched signals, selected pattern, lane summaries, duration, interface, and error metadata. Common secret patterns are redacted.
