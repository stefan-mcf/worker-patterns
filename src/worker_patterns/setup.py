from __future__ import annotations

from pathlib import Path

DEFAULT_ROSTER_TEMPLATE = """workers:
  - id: worker-code-fast
    name: Fast Code Worker
    roles: [builder, recovery-worker]
    capabilities: [code, tests, refactor]
    accepts_broadcast: true
    preferred_task_types: [implementation, feature, patch]

  - id: worker-review
    name: Independent Review Worker
    roles: [reviewer]
    capabilities: [code-review, test-review, security-review]
    accepts_broadcast: true
    preferred_task_types: [review, qa, verification]

  - id: worker-general-premium
    name: General Planning Worker
    roles: [curator, integrator, phase-worker]
    capabilities: [planning, synthesis, integration]
    accepts_broadcast: true
    preferred_task_types: [coordination, integration, docs]
"""


def init_config(target: Path, *, force: bool = False) -> Path:
    path = target.expanduser()
    if path.exists() and not force:
        raise FileExistsError(f"target already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_ROSTER_TEMPLATE)
    return path
