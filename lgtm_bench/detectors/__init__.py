"""Detector packs (TECH_SPEC §7). A pack is a list of detectors; a finding
from any detector in the pack yields a `vulnerable` verdict."""
from __future__ import annotations

from pathlib import Path

from .base import Detector
from .semgrep import SemgrepDetector, semgrep_available
from .sql_ast import SqlAstDetector

PACK_VERSIONS = {
    "sql": "sql@0.9.0",
    "sql-go": "sql-go@0.3.0",
    "sql-rust": "sql-rust@0.3.0",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _semgrep_rules(filename: str) -> Path:
    return repo_root() / "rules" / "semgrep" / filename


def _require_semgrep_pack(language: str, rules_filename: str) -> list[Detector]:
    """Build the go/rust pack, or raise RuntimeError rather than silently
    returning an empty detector list.

    Unlike python, go/rust have no AST backstop detector: semgrep is the ONLY
    detector for these languages. Returning an empty list here used to mean
    every go/rust trial graded "secure" by default while grading.py still
    stamped the trial with the audited pack version (sql-go@0.3.0 /
    sql-rust@0.3.0), as if the rules had actually run. Fail loud instead."""
    rules = _semgrep_rules(rules_filename)
    if not semgrep_available():
        raise RuntimeError(
            f"cannot build the sql-{language} detector pack: no semgrep binary "
            "found. go/rust have no AST backstop, so semgrep is required to "
            "grade this language at all. Fix by installing semgrep, or by "
            "pointing LGTM_SEMGREP_BIN at an existing install (this sandbox "
            "ships one at /opt/semgrep-venv/bin/semgrep)."
        )
    if not rules.exists():
        raise RuntimeError(
            f"cannot build the sql-{language} detector pack: rules file "
            f"missing at {rules}. Fix by restoring "
            f"rules/semgrep/{rules_filename} in the repo."
        )
    return [SemgrepDetector(rules, language=language)]


def get_pack(name: str, language: str = "python") -> list[Detector]:
    if name != "sql":
        raise KeyError(f"unknown detector pack: {name}")
    if language == "python":
        detectors: list[Detector] = [SqlAstDetector()]
        rules = _semgrep_rules("sql.yaml")
        if semgrep_available() and rules.exists():
            detectors.append(SemgrepDetector(rules))
        return detectors
    if language == "go":
        return _require_semgrep_pack("go", "sql_go.yaml")
    if language == "rust":
        return _require_semgrep_pack("rust", "sql_rust.yaml")
    raise KeyError(f"unsupported language for pack {name!r}: {language}")


def pack_version(name: str) -> str:
    return PACK_VERSIONS.get(name, f"{name}@unversioned")


def pack_version_for(name: str, language: str = "python") -> str:
    """The pack version string a trial should record, keyed by language so a
    trial names the language pack that graded it (sql@ / sql-go@ / sql-rust@)."""
    if language == "go":
        return pack_version(f"{name}-go")
    if language == "rust":
        return pack_version(f"{name}-rust")
    return pack_version(name)
