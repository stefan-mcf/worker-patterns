from __future__ import annotations

from functools import lru_cache
from importlib import resources
from pathlib import Path

import yaml

from .schemas import WorkerPattern

POLICY_PATH = Path(__file__).resolve().parents[2] / "policies" / "pattern_rules.yaml"


def _read_policy_text(filename: str) -> str:
    """Read packaged policy data, falling back to the source-tree policy file."""

    package_policy = resources.files("hermes_worker_patterns").joinpath("policies", filename)
    if package_policy.is_file():
        return package_policy.read_text()
    return (Path(__file__).resolve().parents[2] / "policies" / filename).read_text()


@lru_cache(maxsize=1)
def load_pattern_policy() -> dict:
    return yaml.safe_load(_read_policy_text("pattern_rules.yaml")) or {}


def _worker_pattern(raw: str) -> WorkerPattern:
    return WorkerPattern(raw)


_POLICY = load_pattern_policy()
_PATTERN_DATA = _POLICY["patterns"]

PATTERN_DESCRIPTIONS: dict[WorkerPattern, str] = {
    _worker_pattern(pattern_id): str(metadata["description"])
    for pattern_id, metadata in _PATTERN_DATA.items()
}

PATTERN_KEYWORDS: dict[WorkerPattern, tuple[str, ...]] = {
    _worker_pattern(pattern_id): tuple(keywords)
    for pattern_id, keywords in (_POLICY.get("bounded_keyword_hints") or {}).get("patterns", {}).items()
}

DEFAULT_PROOF_EXPECTATIONS: dict[WorkerPattern, tuple[str, ...]] = {
    _worker_pattern(pattern_id): tuple(expectations)
    for pattern_id, expectations in (_POLICY.get("proof_expectations") or {}).items()
}

PATTERN_DIMENSIONS: tuple[str, ...] = tuple((_POLICY.get("dimensions") or {}).keys())
SELECTOR_VERSION = str(_POLICY.get("selector_version") or _POLICY.get("version") or "1")
SELECTOR_METADATA_FIELDS: tuple[str, ...] = tuple(_POLICY.get("selector_metadata_fields") or ())
CLOSE_SCORE_MARGIN = int((_POLICY.get("principles") or {}).get("close_score_margin", 0))
SIMPLER_PATTERN_ORDER: tuple[WorkerPattern, ...] = tuple(
    _worker_pattern(pattern_id) for pattern_id in (_POLICY.get("principles") or {}).get("simpler_pattern_order", ())
)
OVERRIDE_PREFIX = str((_POLICY.get("overrides") or {}).get("explicit_note_override_prefix") or "pattern:")
OVERRIDE_REQUESTED_BY_PREFIX = str((_POLICY.get("overrides") or {}).get("requested_by_prefix") or "pattern_override_requested_by:")
OVERRIDE_REASON_PREFIX = str((_POLICY.get("overrides") or {}).get("reason_prefix") or "pattern_override_reason:")
PATTERN_ALIASES: dict[str, WorkerPattern] = {
    alias: _worker_pattern(target)
    for alias, target in ((_POLICY.get("overrides") or {}).get("aliases") or {}).items()
}
PATTERN_SCORE_FORMULAS: dict[WorkerPattern, dict[str, dict[str, int]]] = {
    _worker_pattern(pattern_id): metadata.get("score_formula", {})
    for pattern_id, metadata in _PATTERN_DATA.items()
}
OVERLAY_PATTERNS: tuple[WorkerPattern, ...] = tuple(
    _worker_pattern(pattern_id)
    for pattern_id, metadata in _PATTERN_DATA.items()
    if metadata.get("overlay_only")
)
BASE_PATTERNS: tuple[WorkerPattern, ...] = tuple(
    _worker_pattern(pattern_id)
    for pattern_id, metadata in _PATTERN_DATA.items()
    if not metadata.get("overlay_only")
)
