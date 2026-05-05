# Runtime-Neutral Download Readiness Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task. Keep this repo public-facing and runtime-neutral. Do not use persistent local swarm profiles unless explicitly requested for review-only assistance; if used, state the actual substrate separately from the selected worker pattern.

**Goal:** Make `worker-patterns` look and behave like a professional, well-architected, downloadable runtime-neutral package by removing Hermes/local-runtime artifacts from the public core, improving documentation depth, and adding safe setup/validation surfaces that help users configure their own worker profile mappings without mutating their runtime.

**Architecture:** Worker Patterns is a planning layer. It selects work shapes, emits logical lanes, describes proof gates, and can render dry-run adapter contracts. Runtime-specific execution remains outside the core package and behind adapter boundaries. Public docs and code should explain worker patterns, worker lanes, worker profiles, policies, adapters, CLI, MCP, and safety boundaries without assuming Hermes, `/goal`, Telegram, Antaeus, local `swarmN` profiles, or any other private runtime.

**Tech Stack:** Python 3.10+, setuptools, PyYAML, pytest, ruff, Markdown documentation, YAML policy fixtures.

**Created:** 2026-05-05 22:10:28 AEST

---

## Non-negotiable product boundary

Worker Patterns may own:

- pattern selection;
- logical lane generation;
- worker role/profile hints;
- proof expectations and safety notes;
- dry-run prompt/spec rendering;
- generic roster/profile-policy validation;
- runtime adapter contracts.

Worker Patterns must not own:

- Hermes setup;
- Hermes swarm profiles;
- `/goal` execution semantics;
- Telegram routing;
- Antaeus-specific doctrine;
- local model/provider names;
- profile creation/mutation;
- real worker launches;
- queue/Kanban writes;
- commits, pushes, deployments, or package publishing as side effects.

Runtime-specific content is allowed only as optional adapter documentation or compatibility shims, and should not appear in the README/product narrative unless framed as one example among many.

---

## Initial artifact inventory from current scan

Use this inventory as the first implementation checklist. Re-run the searches in Task 1 because the repo may change before execution.

### Public docs with runtime-specific or confusing terms

- `README.md`
  - Mentions Hermes adapter in the runtime-adapters section.
  - Links `docs/hermes-integration.md` and `docs/install-skill.md` from the main docs list.
  - Uses `scripts/smoke_hermes_temp_home_mcp.sh` in quick README flow.
  - Mentions compatibility shim `hermes_worker_patterns`.
  - Maturity says stable/tested while `pyproject.toml` says Alpha.
- `docs/runtime-adapters.md`
  - Mechanisms include `goal`, `delegate_task`, `swarm_profiles`, `kanban`.
  - Roster env var is `HERMES_SWARM_ROSTER_PATH`.
- `docs/configuration.md`
  - Section title `Optional swarm roster`.
  - Uses `HERMES_SWARM_ROSTER_PATH` and unhealthy-profile env vars.
  - Debug variables are `HERMES_WORKER_PATTERNS_*`.
- `docs/hermes-integration.md`
  - Entire file is optional runtime-specific adapter docs.
- `docs/install-skill.md`
  - Entire file is optional Hermes skill docs.
- `docs/mcp.md`
  - Uses `scripts/smoke_hermes_temp_home_mcp.sh` and temporary `HERMES_HOME` wording.
- `docs/module-swarm-hardening.md`
  - Mentions Antaeus origin and Antaeus-era lesson.
- `docs/worker-patterns.md`
  - Mentions Antaeus origin.
  - Mentions persistent profiles as a typical mapping.
  - Uses `durable/persistent-worker flags` as selection inputs.
- `docs/elastic-worker-lanes.md`
  - Discusses named persistent profiles; may be fine if generalized.
- `CONTRIBUTING.md`
  - Uses `scripts/smoke_hermes_temp_home_mcp.sh`.

### Source/API artifacts to neutralize or quarantine

- `src/worker_patterns/schemas.py`
  - `ExecutionMechanism.GOAL` is runtime-specific language.
  - `ExecutionMechanism.SWARM_PROFILES` is runtime-specific language.
  - `HermesMapping = RuntimeMapping` compatibility alias should be deprecated/isolated.
- `src/worker_patterns/profile_policy.py`
  - Internal names use `swarm_roster`, `_default_swarm_roster_path`, `_unhealthy_swarm_profiles`, `_load_swarm_roster`, `apply_canonical_swarm_roster`.
  - Env vars are `HERMES_SWARM_ROSTER_PATH`, `HERMES_SWARM_UNHEALTHY_PROFILES`, etc.
  - Docstrings explicitly mention Hermes swarm.
- `src/worker_patterns/prompt_renderer.py`
  - `render_swarm_spec` builds `hermes --profile ...` command argv, which makes a public core renderer Hermes-specific.
- `src/worker_patterns/execution_plan.py`
  - Imports/uses `render_swarm_spec` and `ExecutionMechanism.SWARM_PROFILES`.
- `src/worker_patterns/runtime_tool.py`
  - Supports output `swarm` and `kind: worker_pattern_swarm_spec`.
- `src/worker_patterns/cli.py`
  - Supports command `render-swarm` and output kind `worker_pattern_swarm_spec`.
- `src/hermes_worker_patterns/*`
  - Compatibility shim. Keep temporarily but document as deprecated compatibility only.

### Policy/test fixtures that may be okay but need review

- `policies/worker_profiles.yaml` and packaged copies use `module_swarm_default_profile`. The pattern name `module-swarm` is allowed, but comments should avoid implying specific runtime profile systems.
- Test fixture names with `module_swarm_*` are okay because `module-swarm` is a pattern name.
- `tests/fixtures/legacy_policy_expected_mappings.yaml` contains legacy paths such as `profiles/code-worker/README.md`; keep only if truly testing migration compatibility and label as legacy.

---

## Naming decisions

Use these replacements consistently.

- Keep pattern name: `module-swarm`.
  - Rationale: it describes the decomposition pattern, not Hermes swarm profiles.
  - Define clearly: a swarm is a coordinated set of logical lanes over disjoint scopes.
- Replace public execution mechanism `goal` with `continuation` or `managed_continuation`.
- Replace public execution mechanism `delegate_task` with `ephemeral_workers` or `parallel_subtasks`.
- Replace public execution mechanism `swarm_profiles` with `persistent_workers` or `named_workers`.
- Replace public CLI/output `render-swarm` with `render-persistent-workers` or `render-named-workers`.
- Replace public JSON kind `worker_pattern_swarm_spec` with `worker_pattern_persistent_worker_spec`.
- Replace env var `HERMES_SWARM_ROSTER_PATH` with `WORKER_PATTERNS_ROSTER_PATH`.
- Replace env vars `HERMES_SWARM_UNHEALTHY_PROFILES`, `HERMES_SWARM_BLOCKED_PROFILES`, `HERMES_SWARM_PROVIDER_BLOCKED_PROFILES` with `WORKER_PATTERNS_UNAVAILABLE_WORKERS` and optional aliases.
- Replace debug vars `HERMES_WORKER_PATTERNS_DEBUG` and `HERMES_WORKER_PATTERNS_LOG` with `WORKER_PATTERNS_DEBUG` and `WORKER_PATTERNS_LOG`.
- Keep old env vars and commands as deprecated compatibility aliases for one release, but hide them from primary docs.

---

## Tranche 0: Baseline snapshot and guardrails

### Task 0.1: Create an implementation branch

**Objective:** Keep the public cleanup isolated.

**Files:** None.

**Steps:**

```bash
cd /Users/stefan/worker-patterns
git status --short
git switch -c cleanup/runtime-neutral-readiness
```

**Expected:** status is clean except this plan file if not committed yet; branch is `cleanup/runtime-neutral-readiness`.

**Commit:** Do not commit yet if this plan file is already uncommitted; include it in Task 0.2.

### Task 0.2: Commit this plan as the execution contract

**Objective:** Preserve the tranche plan before edits.

**Files:**

- Add/commit: `docs/plans/2026-05-05-runtime-neutral-readiness.md`

**Steps:**

```bash
git add docs/plans/2026-05-05-runtime-neutral-readiness.md
git commit -m "docs: plan runtime-neutral readiness cleanup"
```

**Expected:** plan commit created.

### Task 0.3: Capture current failing/passing baseline

**Objective:** Know whether cleanup introduces regressions.

**Files:** None.

**Steps:**

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m ruff check .
scripts/smoke_install.sh
```

If local Python is too old or dependencies are missing, use the known reliable uv flow:

```bash
rm -rf /tmp/worker-patterns-verify-venv
uv venv --python /Users/stefan/.local/bin/python3.11 /tmp/worker-patterns-verify-venv
uv pip install --python /tmp/worker-patterns-verify-venv/bin/python -q -e '.[dev]'
/tmp/worker-patterns-verify-venv/bin/python -m pytest -q
/tmp/worker-patterns-verify-venv/bin/python -m ruff check .
```

**Expected:** record pass/fail in commit message or plan checkpoint if there are pre-existing failures.

---

## Tranche 1: Public language scrub and information architecture

### Task 1.1: Add a neutral artifact-audit script

**Objective:** Create an executable guard that catches runtime-specific language outside allowed compatibility/adapter paths.

**Files:**

- Create: `scripts/check_runtime_neutrality.py`
- Modify: `pyproject.toml` only if adding script config is desired.

**Implementation outline:**

Create a Python script that:

- scans `README.md`, `docs/**/*.md`, `src/worker_patterns/**/*.py`, `policies/**/*.yaml`, and `tests/**/*.py|yaml`;
- ignores `.git`, `.venv`, caches, egg-info;
- supports allowlisted paths:
  - `src/hermes_worker_patterns/**`;
  - `docs/adapters/hermes.md` if retained;
  - tests explicitly named legacy/compatibility;
- flags public mentions of:
  - `Hermes swarm`, `swarmN`, `swarm[0-9]+`;
  - `HERMES_SWARM_` in primary docs/code;
  - `/goal` and bare `goal` mechanism docs outside compatibility notes;
  - `Telegram`, `Antaeus`, `CHASSIS`, `Codex`, `Gemini`;
  - `hermes --profile` in core renderers/docs;
  - `worker_pattern_swarm_spec` outside compatibility.

**Verification:**

```bash
python scripts/check_runtime_neutrality.py --report
```

Expected initially: fails and lists known artifacts.

**Commit:**

```bash
git add scripts/check_runtime_neutrality.py
git commit -m "test: add runtime neutrality audit"
```

### Task 1.2: Restructure documentation index

**Objective:** Make README look like a professional product entrypoint, not a local adapter report.

**Files:**

- Modify: `README.md`
- Create or rewrite: `docs/index.md`

**README target structure:**

1. Title and one-paragraph product definition.
2. What Worker Patterns does.
3. What Worker Patterns does not do.
4. Install.
5. CLI quickstart.
6. MCP quickstart.
7. Supported worker patterns summary.
8. Worker profiles and runtime adapters summary.
9. Configuration summary.
10. Safety boundary.
11. Documentation map.
12. Development/verification.
13. Compatibility/maturity/license.

**Important language:**

- Do not mention Hermes in README body except possibly in a short `Compatibility` note that a legacy import shim exists.
- Do not link optional Hermes adapter docs from the main docs list. If retained, put it under `docs/adapters/` and label it optional/compatibility.
- Rename `scripts/smoke_hermes_temp_home_mcp.sh` references to a neutral smoke script after Tranche 4.

**Verification:**

```bash
python scripts/check_runtime_neutrality.py --paths README.md docs/index.md
```

**Commit:**

```bash
git add README.md docs/index.md
git commit -m "docs: restructure runtime-neutral overview"
```

### Task 1.3: Rewrite `docs/worker-patterns.md` as the deep taxonomy page

**Objective:** Extensively explain what worker patterns are and describe every pattern in depth.

**Files:**

- Modify: `docs/worker-patterns.md`

**Required sections:**

- Definition: worker pattern vs worker vs runtime.
- Anatomy of a pattern:
  - intent;
  - selection signals;
  - lane structure;
  - proof expectations;
  - risk controls;
  - typical adapter mappings;
  - anti-patterns.
- Pattern pages/sections:
  - `sequential`;
  - `module-swarm`;
  - `blueprint-fanout`;
  - `phased-assembly`;
  - `twin-inspection` overlay;
  - `recovery-lane`;
  - `bridge_lane`.
- For each pattern include:
  - when to use;
  - when not to use;
  - example objective;
  - sample lanes;
  - expected evidence;
  - safety notes.
- Add explicit note: `module-swarm` is a logical-lane decomposition pattern, not a requirement for any runtime with “swarm” in its name.

**Remove:**

- Antaeus-origin references.
- Any implication that persistent profiles are the default mapping.

**Verification:**

```bash
python scripts/check_runtime_neutrality.py --paths docs/worker-patterns.md
```

**Commit:**

```bash
git add docs/worker-patterns.md
git commit -m "docs: expand worker pattern taxonomy"
```

### Task 1.4: Split architecture and adapter docs cleanly

**Objective:** Make architecture explain core package boundaries and make adapter docs generic.

**Files:**

- Modify: `docs/architecture.md`
- Modify: `docs/runtime-adapters.md`
- Create: `docs/worker-profiles.md`
- Optional create: `docs/adapters/README.md`
- Optional move: `docs/hermes-integration.md` -> `docs/adapters/hermes.md`

**Architecture content:**

- package components:
  - schemas;
  - selector;
  - policy loader;
  - profile policy;
  - prompt/spec renderers;
  - CLI;
  - MCP server;
  - trace logging;
- data flow from request to plan;
- compatibility boundaries;
- dry-run guarantee.

**Runtime adapter content:**

- generic adapter contract;
- mechanisms using neutral names only:
  - `direct`;
  - `continuation`;
  - `ephemeral_workers`;
  - `persistent_workers`;
  - `task_graph`;
- mapping responsibilities;
- fail-closed expectations;
- no auto execution.

**Worker profiles content:**

Explain in depth:

- logical profile hints;
- role to profile mapping;
- selected profile vs fallback profiles;
- toolsets;
- model-policy metadata;
- profile pools/classes;
- rosters;
- unavailable workers;
- how adapters map profiles to actual worker identities;
- examples with generic names only (`worker-code-fast`, `worker-review`, etc.).

**Verification:**

```bash
python scripts/check_runtime_neutrality.py --paths docs/architecture.md docs/runtime-adapters.md docs/worker-profiles.md
```

**Commit:**

```bash
git add docs/architecture.md docs/runtime-adapters.md docs/worker-profiles.md docs/adapters/README.md docs/adapters/hermes.md
git commit -m "docs: clarify core architecture and adapter boundaries"
```

---

## Tranche 2: Neutralize public API and compatibility names

### Task 2.1: Rename execution mechanisms with backward compatibility

**Objective:** Replace runtime-specific mechanism names in the public schema while preserving old values as aliases during a compatibility window.

**Files:**

- Modify: `src/worker_patterns/schemas.py`
- Modify tests that assert mechanism values.

**Target enum:**

```python
class ExecutionMechanism(str, Enum):
    DIRECT = "direct"
    CONTINUATION = "continuation"
    EPHEMERAL_WORKERS = "ephemeral_workers"
    PERSISTENT_WORKERS = "persistent_workers"
    TASK_GRAPH = "task_graph"

    # Deprecated aliases for compatibility only.
    GOAL = "goal"
    DELEGATE_TASK = "delegate_task"
    SWARM_PROFILES = "swarm_profiles"
    KANBAN = "kanban"
```

**Important:** Do not silently emit deprecated values in new plans. Only accept them when reading old integrations/fixtures if needed.

**Verification:**

```bash
python -m pytest tests/test_selector.py tests/test_execution_plan.py -q
```

**Commit:**

```bash
git add src/worker_patterns/schemas.py tests
git commit -m "feat: add runtime-neutral execution mechanisms"
```

### Task 2.2: Rename swarm roster internals to worker roster internals

**Objective:** Make code vocabulary runtime-neutral.

**Files:**

- Modify: `src/worker_patterns/profile_policy.py`
- Modify: matching tests/fixtures.

**Rename concepts:**

- `SwarmRosterEntry` -> `WorkerRosterEntry`.
- `swarm_roster` -> `worker_roster`.
- `swarm_roster_path` -> `worker_roster_path`.
- `apply_canonical_swarm_roster` -> `apply_worker_roster`.
- `_default_swarm_roster_path` -> `_default_worker_roster_path`.
- `_unhealthy_swarm_profiles` -> `_unavailable_workers`.
- `_load_swarm_roster` -> `_load_worker_roster`.
- `module_swarm_default_profile` may remain if it refers specifically to the `module-swarm` pattern, but consider `module_decomposition_default_profile` if public output reads better.

**Environment variables:**

Primary:

```text
WORKER_PATTERNS_ROSTER_PATH
WORKER_PATTERNS_UNAVAILABLE_WORKERS
```

Deprecated aliases accepted but not documented in primary docs:

```text
HERMES_SWARM_ROSTER_PATH
HERMES_SWARM_UNHEALTHY_PROFILES
HERMES_SWARM_BLOCKED_PROFILES
HERMES_SWARM_PROVIDER_BLOCKED_PROFILES
```

**Verification:**

```bash
python -m pytest tests/test_profile_policy.py tests/test_selector.py -q
python scripts/check_runtime_neutrality.py --paths src/worker_patterns/profile_policy.py
```

Allow compatibility alias mentions only if script allowlist marks them as deprecated compatibility.

**Commit:**

```bash
git add src/worker_patterns/profile_policy.py tests scripts/check_runtime_neutrality.py
git commit -m "refactor: neutralize worker roster policy naming"
```

### Task 2.3: Replace Hermes-specific persistent worker renderer

**Objective:** Ensure core renderers never emit `hermes --profile` commands.

**Files:**

- Modify: `src/worker_patterns/prompt_renderer.py`
- Modify: `src/worker_patterns/execution_plan.py`
- Modify: `src/worker_patterns/runtime_tool.py`
- Modify: `src/worker_patterns/cli.py`
- Modify tests.

**Changes:**

- Rename `render_swarm_spec` -> `render_persistent_worker_spec`.
- Return neutral worker specs:

```json
{
  "mechanism": "persistent_workers",
  "dry_run": true,
  "selected_pattern": "module-swarm",
  "workers": [
    {
      "role": "builder",
      "worker_profile": "worker-code-fast",
      "fallback_profiles": [],
      "toolsets": ["terminal", "file"],
      "prompt": "...",
      "adapter_command": null
    }
  ]
}
```

- Do not generate command argv for a concrete runtime.
- If command previews are useful, use an abstract placeholder:

```json
"adapter_hint": "Map this logical worker profile to your runtime before execution."
```

- Rename CLI command:

```bash
worker-pattern render-persistent-workers ...
```

- Keep `render-swarm` as deprecated alias for one release if needed. It should emit a warning to stderr and the neutral spec kind.

**Verification:**

```bash
worker-pattern render-persistent-workers "refactor auth billing" --scope auth --scope billing
python -m pytest tests/test_prompt_renderer.py tests/test_cli.py tests/test_execution_plan.py -q
python scripts/check_runtime_neutrality.py --paths src/worker_patterns/prompt_renderer.py src/worker_patterns/cli.py src/worker_patterns/runtime_tool.py src/worker_patterns/execution_plan.py
```

**Commit:**

```bash
git add src/worker_patterns tests
git commit -m "refactor: render neutral persistent worker specs"
```

### Task 2.4: Neutralize debug/tracing env var names

**Objective:** Remove Hermes-specific env names from normal trace docs and code.

**Files:**

- Modify: trace module if env vars are defined there.
- Modify: `docs/dev-logging.md`
- Modify: `docs/configuration.md`
- Modify tests for trace env vars.

**Target variables:**

```text
WORKER_PATTERNS_DEBUG=1
WORKER_PATTERNS_LOG=/path/to/log.jsonl
WORKER_PATTERNS_FORCE_STDIO_FALLBACK=1
```

Keep old `HERMES_WORKER_PATTERNS_*` only as deprecated aliases.

**Verification:**

```bash
WORKER_PATTERNS_DEBUG=1 WORKER_PATTERNS_LOG="$(mktemp)" worker-pattern select "small docs update" --text
python -m pytest tests/test_dev_trace.py tests/test_mcp_stdio_smoke.py -q
```

**Commit:**

```bash
git add src/worker_patterns docs tests
git commit -m "refactor: use neutral worker patterns environment variables"
```

---

## Tranche 3: Professional documentation expansion

### Task 3.1: Create complete CLI command reference

**Objective:** Make `docs/cli.md` standalone and professional.

**Files:**

- Modify: `docs/cli.md`

**Required sections:**

- Installation prerequisite.
- Global behavior: dry-run, JSON default, `--text` where supported.
- Commands:
  - `select`;
  - `render`;
  - `render-execution-plan`;
  - `render-prompts`;
  - `render-delegate` or new neutral alias `render-ephemeral-workers`;
  - `render-persistent-workers`;
  - `render-task-graph`;
  - any `doctor`, `validate-roster`, or setup commands added in Tranche 5.
- Options:
  - objective;
  - `--scope`;
  - `--dependency`;
  - `--risk-level`;
  - `--review-required` / `--no-review-required` if available;
  - `--tests-required`;
  - `--variants-requested`;
  - `--durable` if retained;
  - `--persistent-workers`;
  - `--max-parallel-lanes`;
  - `--override` if available;
  - `--text`.
- Examples for each pattern.
- Machine-readable output guarantees.
- Deprecation notes for legacy command aliases.

**Verification:**

```bash
python scripts/check_runtime_neutrality.py --paths docs/cli.md
```

**Commit:**

```bash
git add docs/cli.md
git commit -m "docs: expand CLI reference"
```

### Task 3.2: Create policy/configuration reference

**Objective:** Explain pattern policy and worker profile policy in depth.

**Files:**

- Modify: `docs/configuration.md`
- Create: `docs/policies.md`

**Required content:**

- Policy file locations.
- Packaged defaults vs source checkout policy files.
- Pattern scoring policy.
- Selection signals.
- Overrides and fail-closed behavior.
- Worker profile policy fields.
- Roster file schema.
- Unavailable-worker quarantine variable.
- Debug tracing.
- Examples with generic worker names only.

**Verification:**

```bash
python scripts/check_runtime_neutrality.py --paths docs/configuration.md docs/policies.md
```

**Commit:**

```bash
git add docs/configuration.md docs/policies.md
git commit -m "docs: document policies and configuration"
```

### Task 3.3: Create examples directory with neutral examples

**Objective:** Give downloaders copy-pasteable examples without local runtime assumptions.

**Files:**

- Create: `examples/README.md`
- Create: `examples/basic-select.sh`
- Create: `examples/roster.generic.yaml`
- Create: `examples/runtime-adapter-output.json` or generated fixture.

**Example roster shape:**

```yaml
workers:
  - id: worker-code-fast
    name: Fast Code Worker
    roles: [builder, recovery-worker]
    capabilities: [code, tests, refactor]
    accepts_broadcast: true

  - id: worker-review
    name: Independent Review Worker
    roles: [reviewer]
    capabilities: [code-review, test-review, security-review]
    accepts_broadcast: true

  - id: worker-general-premium
    name: General Planning Worker
    roles: [curator, integrator, phase-worker]
    capabilities: [planning, synthesis, integration]
    accepts_broadcast: true
```

**Verification:**

```bash
WORKER_PATTERNS_ROSTER_PATH=examples/roster.generic.yaml worker-pattern select "implement backend frontend docs review" --scope backend --scope frontend --scope docs --scope review --persistent-workers --text
python scripts/check_runtime_neutrality.py --paths examples
```

**Commit:**

```bash
git add examples
git commit -m "docs: add runtime-neutral examples"
```

### Task 3.4: Add glossary and concepts page

**Objective:** Make terms clear for users who are not already familiar with Stefan/Hermes/Antaeus context.

**Files:**

- Create: `docs/concepts.md`

**Terms to define:**

- worker pattern;
- lane;
- role;
- scope;
- overlay;
- proof expectation;
- runtime adapter;
- worker profile;
- roster;
- selected profile;
- fallback profile;
- task graph;
- dry run;
- module-swarm;
- bridge lane.

**Verification:**

```bash
python scripts/check_runtime_neutrality.py --paths docs/concepts.md
```

**Commit:**

```bash
git add docs/concepts.md
git commit -m "docs: add worker patterns concepts glossary"
```

---

## Tranche 4: Neutral smoke scripts and MCP docs

### Task 4.1: Rename Hermes-named smoke script

**Objective:** Remove Hermes naming from MCP smoke tests.

**Files:**

- Rename: `scripts/smoke_hermes_temp_home_mcp.sh` -> `scripts/smoke_mcp_temp_home.sh`
- Modify tests referencing the old script.
- Modify `README.md`, `CONTRIBUTING.md`, `docs/mcp.md`.

**Behavior:**

- If the script uses `HERMES_HOME` only because a compatibility harness expects it, replace with neutral temp env where possible.
- If `HERMES_HOME` cannot be removed yet, keep it internal and document as compatibility-only in script comments, not user docs.

**Compatibility:**

Optionally keep a one-line wrapper at the old path for one release:

```bash
#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "$0")/smoke_mcp_temp_home.sh" "$@"
```

**Verification:**

```bash
scripts/smoke_mcp_temp_home.sh
python -m pytest tests/test_mcp_stdio_smoke.py tests/test_hermes_temp_home_smoke_script.py -q
python scripts/check_runtime_neutrality.py --paths README.md CONTRIBUTING.md docs/mcp.md scripts/smoke_mcp_temp_home.sh
```

Rename test file `tests/test_hermes_temp_home_smoke_script.py` if present.

**Commit:**

```bash
git add -A scripts tests README.md CONTRIBUTING.md docs/mcp.md
git commit -m "refactor: neutralize MCP smoke script naming"
```

### Task 4.2: Make MCP docs standalone

**Objective:** Explain MCP bridge as a generic stdio tool surface.

**Files:**

- Modify: `docs/mcp.md`

**Required content:**

- what MCP is in this package;
- tools exposed:
  - `select_worker_pattern`;
  - `render_execution_plan`;
- stdio contract;
- stdout/stderr behavior;
- dry-run boundary;
- smoke-test command;
- example JSON-RPC call if useful;
- no dependency on a specific agent runtime.

**Verification:**

```bash
python scripts/check_runtime_neutrality.py --paths docs/mcp.md
scripts/smoke_mcp_temp_home.sh
```

**Commit:**

```bash
git add docs/mcp.md
git commit -m "docs: expand runtime-neutral MCP guide"
```

---

## Tranche 5: Setup/doctor without runtime mutation

### Task 5.1: Add `worker-pattern doctor`

**Objective:** Help downloaders verify installation and config without mutating any runtime.

**Files:**

- Modify: `src/worker_patterns/cli.py`
- Create: `src/worker_patterns/doctor.py`
- Add tests: `tests/test_doctor.py`
- Update docs after implementation.

**Command behavior:**

```bash
worker-pattern doctor
worker-pattern doctor --json
worker-pattern doctor --roster examples/roster.generic.yaml
```

Checks:

- package import works;
- CLI version/import path available;
- packaged policy files load;
- optional roster path exists and parses;
- no required credentials;
- no runtime launch attempted;
- MCP entrypoint importable;
- deprecated env vars present warning if used.

Human output example:

```text
Worker Patterns doctor
Package: OK
Policy files: OK
MCP entrypoint: OK
Roster: not configured (optional)
Runtime mutation: none
Next: run worker-pattern select "small docs update" --text
```

**Tests:**

- no env vars -> OK with optional roster absent;
- valid roster -> OK;
- invalid roster -> non-zero with helpful error;
- deprecated Hermes env var -> warning, not failure.

**Verification:**

```bash
worker-pattern doctor
worker-pattern doctor --json
python -m pytest tests/test_doctor.py tests/test_cli.py -q
```

**Commit:**

```bash
git add src/worker_patterns/doctor.py src/worker_patterns/cli.py tests/test_doctor.py tests/test_cli.py
git commit -m "feat: add runtime-neutral doctor command"
```

### Task 5.2: Add `worker-pattern validate-roster`

**Objective:** Let users validate worker profile rosters without involving any runtime.

**Files:**

- Modify: `src/worker_patterns/cli.py`
- Modify/create: `src/worker_patterns/profile_policy.py` or `src/worker_patterns/roster.py`
- Add tests: `tests/test_validate_roster.py`

**Command:**

```bash
worker-pattern validate-roster examples/roster.generic.yaml
worker-pattern validate-roster examples/roster.generic.yaml --json
```

**Validation rules:**

- top-level `workers` list exists;
- each worker has stable `id`;
- roles are non-empty;
- capabilities are list-like;
- duplicate ids fail;
- no secrets or endpoint URLs required;
- adapter-specific extra keys are allowed but ignored by core unless under `adapter`.

**Verification:**

```bash
worker-pattern validate-roster examples/roster.generic.yaml
python -m pytest tests/test_validate_roster.py -q
```

**Commit:**

```bash
git add src/worker_patterns tests examples/roster.generic.yaml
git commit -m "feat: add worker roster validation"
```

### Task 5.3: Add `worker-pattern init-config --dry-run` and optional write mode

**Objective:** Provide helpful setup without creating runtime profiles.

**Files:**

- Modify: `src/worker_patterns/cli.py`
- Create/modify: `src/worker_patterns/setup.py`
- Add tests: `tests/test_setup_command.py`
- Modify docs.

**Commands:**

```bash
worker-pattern init-config --dry-run
worker-pattern init-config --target .worker-patterns/roster.yaml
worker-pattern init-config --target ~/.config/worker-patterns/roster.yaml --write
```

**Rules:**

- Default is dry-run.
- Never writes outside the explicit `--target` path.
- Never edits runtime profiles or credentials.
- Writes a generic roster template only.
- If file exists, fail unless `--force` is passed.

**Verification:**

```bash
worker-pattern init-config --dry-run
worker-pattern init-config --target /tmp/worker-patterns-roster.yaml --write
worker-pattern validate-roster /tmp/worker-patterns-roster.yaml
python -m pytest tests/test_setup_command.py -q
```

**Commit:**

```bash
git add src/worker_patterns tests docs README.md
git commit -m "feat: add safe config initialization command"
```

---

## Tranche 6: Optional adapter quarantine and compatibility cleanup

### Task 6.1: Move optional Hermes docs out of primary docs path or remove from public docs

**Objective:** Ensure public docs do not imply Worker Patterns needs Hermes.

**Files:**

- Option A modify/move:
  - Move `docs/hermes-integration.md` -> `docs/adapters/hermes.md`.
  - Move `docs/install-skill.md` -> `docs/adapters/hermes-skill.md`.
  - Create `docs/adapters/README.md`.
- Option B delete these docs from public repo if they are not meant for downloaders.

**Preferred:** Option A if preserving compatibility docs matters; Option B if the repo should be completely runtime-neutral with no named runtime examples.

**Adapter doc requirements if kept:**

- Header: `Optional Hermes Adapter Notes`.
- First paragraph: `Worker Patterns does not require Hermes. This page is only for users who already use Hermes and want to write their own adapter.`
- No local `swarmN`, no Stefan paths, no Telegram, no Antaeus.
- Link is not in README primary docs list; only in `docs/adapters/README.md`.

**Verification:**

```bash
python scripts/check_runtime_neutrality.py --report
```

Expected: only allowlisted adapter paths mention Hermes.

**Commit:**

```bash
git add -A docs
git commit -m "docs: quarantine optional runtime-specific adapter notes"
```

### Task 6.2: Deprecate `src/hermes_worker_patterns` shim clearly

**Objective:** Keep compatibility without making it look like the main package identity.

**Files:**

- Modify: `src/hermes_worker_patterns/__init__.py`
- Modify: `docs/architecture.md` or `docs/compatibility.md`
- Add/modify tests for deprecation behavior if warnings are emitted.

**Rules:**

- Public import path is `worker_patterns`.
- `hermes_worker_patterns` remains only as legacy shim.
- Do not include `hermes_worker_patterns` in README quickstart.

**Verification:**

```bash
python -m pytest tests/test_compatibility_shim.py -q
python scripts/check_runtime_neutrality.py --report
```

**Commit:**

```bash
git add src/hermes_worker_patterns docs tests
git commit -m "docs: mark legacy import shim as compatibility only"
```

---

## Tranche 7: Metadata, maturity, packaging polish

### Task 7.1: Align pyproject maturity and metadata

**Objective:** Remove contradictory release-readiness signals.

**Files:**

- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Decision:** Choose one:

- If ready but not final: classifier `Development Status :: 4 - Beta` and README says “Beta: CLI/MCP dry-run surfaces are tested; APIs may still evolve.”
- If not ready: keep Alpha and soften README “stable and tested” line.

Given the goal “ready for downloading,” prefer Beta once tests/docs pass.

**Also check:**

- package description is runtime-neutral;
- keywords include `agents`, `orchestration`, `planning`, `mcp`, `workflow`;
- no Hermes keyword in public metadata.

**Verification:**

```bash
python -m build
python -m twine check dist/*
```

**Commit:**

```bash
git add pyproject.toml README.md CHANGELOG.md
git commit -m "chore: align package metadata for beta readiness"
```

### Task 7.2: Add documentation quality checks

**Objective:** Make docs quality sustainable.

**Files:**

- Modify: `CONTRIBUTING.md`
- Modify: CI config if present.
- Add: `scripts/check_docs_links.py` if no existing checker.

**Checks:**

- runtime neutrality audit;
- all README doc links exist;
- examples referenced by docs exist;
- smoke scripts executable;
- package build/twine check.

**Verification:**

```bash
python scripts/check_runtime_neutrality.py --report
python scripts/check_docs_links.py
python -m pytest -q
python -m ruff check .
```

**Commit:**

```bash
git add CONTRIBUTING.md scripts .github
git commit -m "ci: add documentation readiness checks"
```

---

## Tranche 8: Test suite and fixture migration

### Task 8.1: Update golden routing fixtures to neutral mechanisms

**Objective:** Make tests assert the new public vocabulary.

**Files:**

- Modify: `tests/fixtures/golden_routing_cases.yaml`
- Modify: `tests/fixtures/pattern_cases.yaml`
- Modify: `tests/fixtures/module_swarm_32_lane_case.yaml` only if profile terminology leaks runtime assumptions.
- Modify related tests.

**Expected mapping examples:**

- old `direct` -> `direct`.
- old `goal` -> `continuation`.
- old `delegate_task` -> `ephemeral_workers`.
- old `swarm_profiles` -> `persistent_workers`.
- old `kanban` -> `task_graph`.

**Verification:**

```bash
python -m pytest tests/test_golden_routing_cases.py tests/test_selector.py -q
```

**Commit:**

```bash
git add tests
git commit -m "test: migrate fixtures to neutral execution mechanisms"
```

### Task 8.2: Add regression tests for no runtime-specific output

**Objective:** Prevent future public output from mentioning a runtime by accident.

**Files:**

- Create: `tests/test_runtime_neutrality.py`

**Test cases:**

- `worker-pattern select ...` JSON contains no `Hermes`, `HERMES`, `hermes --profile`, `/goal`, `swarm_profiles` unless compatibility alias command is explicitly requested.
- `render-persistent-workers` contains `persistent_workers`, not `swarm_profiles`.
- `render-execution-plan` emits no executable concrete runtime command.
- README/docs neutrality script passes for non-allowlisted files.

**Verification:**

```bash
python -m pytest tests/test_runtime_neutrality.py -q
```

**Commit:**

```bash
git add tests/test_runtime_neutrality.py
git commit -m "test: guard runtime-neutral public outputs"
```

---

## Tranche 9: Final scrub and release-readiness pass

### Task 9.1: Run full artifact scrub

**Objective:** Drive runtime-specific artifacts to zero outside allowed compatibility paths.

**Commands:**

```bash
python scripts/check_runtime_neutrality.py --report
python - <<'PY'
from pathlib import Path
terms = [
    'Hermes swarm', 'swarmN', 'Telegram', 'Antaeus', 'CHASSIS',
    'Codex', 'Gemini', '/goal', 'hermes --profile',
    'HERMES_SWARM_', 'worker_pattern_swarm_spec',
]
for path in Path('.').rglob('*'):
    if path.is_dir() or '.git' in path.parts or '.venv' in path.parts:
        continue
    try:
        text = path.read_text()
    except UnicodeDecodeError:
        continue
    for term in terms:
        if term in text:
            print(f'{path}: contains {term}')
PY
```

**Expected:** only allowlisted compatibility/adapter references remain.

**Commit:** if fixes are needed:

```bash
git add -A
git commit -m "chore: final runtime-neutral artifact scrub"
```

### Task 9.2: Run full verification matrix

**Objective:** Verify package quality before merge/release.

**Commands:**

```bash
rm -rf /tmp/worker-patterns-verify-venv dist build
uv venv --python /Users/stefan/.local/bin/python3.11 /tmp/worker-patterns-verify-venv
uv pip install --python /tmp/worker-patterns-verify-venv/bin/python -q -e '.[dev]'
/tmp/worker-patterns-verify-venv/bin/python -m pytest -q
/tmp/worker-patterns-verify-venv/bin/python -m ruff check .
/tmp/worker-patterns-verify-venv/bin/python scripts/check_runtime_neutrality.py --report
/tmp/worker-patterns-verify-venv/bin/python -m build
/tmp/worker-patterns-verify-venv/bin/python -m twine check dist/*
scripts/smoke_install.sh
scripts/smoke_mcp_temp_home.sh
```

**Expected:** all pass.

### Task 9.3: Review public repo presentation

**Objective:** Make the repo look professional to a downloader browsing GitHub.

**Manual checklist:**

- README first screen explains the product clearly.
- Install works from fresh clone.
- Quickstart command works after install.
- Docs map is complete and non-redundant.
- Each worker pattern is deeply documented.
- Worker profiles are explained without runtime lock-in.
- Adapter boundary is explicit.
- Setup/doctor commands do not mutate runtime configuration.
- No private/local names in public docs.
- Maturity classifier matches README language.
- License/security/contributing files are present and current.

**Optional independent review prompt:**

```text
Review /Users/stefan/worker-patterns for public download readiness. Focus on runtime neutrality, documentation completeness, packaging quality, and whether any Hermes/Antaeus/local execution artifacts remain in the public product narrative. Do not modify files; return issues with file paths and suggested fixes.
```

### Task 9.4: Final commit and merge

**Objective:** Land the cleanup safely.

**Commands:**

```bash
git status --short
git log --oneline --decorate -10
# If using PR workflow:
git push -u origin cleanup/runtime-neutral-readiness
# Open PR and wait for CI.
```

Before any push, verify GitHub account and remote scope:

```bash
gh api user --jq .login
git remote -v
```

Expected GitHub login: `stefan-mcf`.

---

## `/goal` handoff section

This section intentionally mentions `/goal` only as an execution handoff note for Stefan's private operator flow. Remove this section before publishing this plan if the plan itself becomes public-facing documentation.

**Recommended stop target:** Execute through Tranche 9.2 autonomously. Stop before release tags, package publication, branch protection changes, or public announcement.

**Mandatory human stop gates:**

- deleting optional compatibility shims instead of deprecating them;
- removing all Hermes adapter docs rather than quarantining them;
- changing public package name or import path;
- tagging a release;
- publishing to PyPI;
- pushing to GitHub if `gh api user --jq .login` is not `stefan-mcf`;
- any action that mutates a user's actual runtime/profile configuration.

**Autonomous defaults:**

- Repo: `/Users/stefan/worker-patterns`.
- Branch: `cleanup/runtime-neutral-readiness`.
- Commit after each tranche or coherent task group.
- Keep old env vars and CLI aliases as deprecated compatibility for one release unless tests prove they are safe to remove.
- Prefer runtime-neutral docs over named adapter examples.
- Use generic worker names only.
- No secrets, no paid APIs, no live runtime mutation.

**Prompt seed:**

```text
/goal Execute the plan at /Users/stefan/worker-patterns/docs/plans/2026-05-05-runtime-neutral-readiness.md through Tranche 9.2. Keep Worker Patterns runtime-neutral and public-download ready. Do not create or edit actual runtime profiles. Do not publish packages, tag releases, or push unless GitHub login is stefan-mcf and remote scope is verified. Commit after each tranche/task group with clear messages. Stop if deleting compatibility shims or optional adapter docs becomes necessary.
```

**Escalation rules:**

Stop early and report if:

- tests reveal the current API relies deeply on `swarm_profiles`/`goal` in a way that requires a breaking release decision;
- compatibility aliases create ambiguous output that cannot be cleanly tested;
- a public/private adapter-doc deletion decision is needed;
- local Python/tooling cannot run the verification matrix;
- GitHub auth or remote scope is wrong.

---

## Final success criteria

- `README.md` is runtime-neutral, clear, and professional.
- `docs/worker-patterns.md` deeply explains every pattern.
- `docs/worker-profiles.md` deeply explains logical worker profiles, rosters, and profile hints.
- `docs/runtime-adapters.md` is generic and not tied to Hermes, `/goal`, Telegram, or Antaeus.
- Optional runtime-specific docs, if retained, are quarantined under `docs/adapters/` and not part of the main narrative.
- Core source emits neutral mechanisms and spec names.
- Core source does not generate `hermes --profile` commands.
- New setup/doctor tooling is read-only by default and never mutates runtime profiles.
- Runtime-neutrality audit passes outside allowlisted compatibility paths.
- `pytest`, `ruff`, smoke scripts, build, and twine check pass.
- Package metadata and README maturity language agree.
