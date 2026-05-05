from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

import yaml

from . import mcp_server
from .policy import _read_policy_text
from .profile_policy import deprecated_env_warnings, validate_roster_file


@dataclass(frozen=True)
class DoctorResult:
    ok: bool
    checks: dict[str, str]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "checks": self.checks, "warnings": list(self.warnings)}

    def to_text(self) -> str:
        lines = ["Worker Patterns doctor"]
        for name, status in self.checks.items():
            lines.append(f"{name}: {status}")
        for warning in self.warnings:
            lines.append(f"Warning: {warning}")
        lines.append("Runtime mutation: none")
        lines.append('Next: run worker-pattern select "small docs update" --text')
        return "\n".join(lines)


def run_doctor(*, roster: str | None = None) -> DoctorResult:
    checks: dict[str, str] = {}
    warnings = list(deprecated_env_warnings())
    ok = True

    try:
        version = metadata.version("worker-patterns")
    except metadata.PackageNotFoundError:
        version = "editable/source checkout"
    checks["Package"] = f"OK ({version})"

    try:
        yaml.safe_load(_read_policy_text("worker_profiles.yaml"))
        yaml.safe_load(_read_policy_text("pattern_rules.yaml"))
        checks["Policy files"] = "OK"
    except Exception as exc:  # noqa: BLE001
        checks["Policy files"] = f"FAIL ({exc})"
        ok = False

    try:
        if callable(mcp_server.main):
            checks["MCP entrypoint"] = "OK"
        else:
            checks["MCP entrypoint"] = "FAIL (main is not callable)"
            ok = False
    except Exception as exc:  # noqa: BLE001
        checks["MCP entrypoint"] = f"FAIL ({exc})"
        ok = False

    if roster:
        result = validate_roster_file(roster)
        checks["Roster"] = "OK" if result.ok else "FAIL"
        warnings.extend(result.warnings)
        if not result.ok:
            ok = False
            warnings.extend(result.errors)
    else:
        checks["Roster"] = "not configured (optional)"

    checks["Credentials"] = "not required"
    checks["Runtime launch"] = "not attempted"
    checks["Import path"] = str(Path(__file__).resolve().parent)
    return DoctorResult(ok=ok, checks=checks, warnings=tuple(warnings))
