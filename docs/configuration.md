# Configuration

Configuration is policy-driven and file-backed.

## Pattern policy

`policies/pattern_rules.yaml` controls pattern descriptions, scoring hints, proof expectations, and override metadata.

A packaged copy is stored at `src/worker_patterns/policies/pattern_rules.yaml` so installed builds work outside a source checkout.

## Worker profile policy

`policies/worker_profiles.yaml` maps logical roles to profile hints and model-policy expectations.

A packaged copy is stored at `src/worker_patterns/policies/worker_profiles.yaml`.

## Optional worker roster

Set `WORKER_PATTERNS_ROSTER_PATH` to map logical lanes to caller-owned worker identities:

```bash
export WORKER_PATTERNS_ROSTER_PATH=/path/to/workers.yaml
```

The roster is optional. Without it, outputs remain generic and portable.

A minimal roster looks like:

```yaml
workers:
  - id: worker-code-fast
    role: builder
    preferredTaskTypes: [implementation, feature]
    acceptsBroadcast: true
  - id: worker-review
    role: reviewer
    preferredTaskTypes: [review, qa, verification]
    acceptsBroadcast: true
```

## Temporarily skipped workers

Callers can quarantine workers for one run with:

```bash
export WORKER_PATTERNS_UNAVAILABLE_WORKERS=worker-review,worker-code-fast
```

Deprecated compatibility aliases from earlier runtime-specific adapters are still accepted for one migration window, but new integrations should use `WORKER_PATTERNS_*` names.

## Debug tracing

Tracing is off by default. Enable it explicitly:

```bash
WORKER_PATTERNS_DEBUG=1 \
WORKER_PATTERNS_LOG="$(mktemp)" \
  worker-pattern select "small docs update"
```

Trace events include bounded request metadata, selection scores, matched signals, selected pattern, lane summaries, duration, interface, and error metadata. Common secret patterns are redacted.
