"""Detector packs (TECH_SPEC §7). A pack is a list of detectors; a finding
from any detector in the pack yields a `vulnerable` verdict."""
from __future__ import annotations

from pathlib import Path

from .base import Detector
from .semgrep import SemgrepDetector, semgrep_available
from .sql_ast import SqlAstDetector

PACK_VERSIONS = {
    "sql": "sql@0.9.0",
    "sql-go": "sql-go@0.2.0",
    "sql-rust": "sql-rust@0.2.0",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _semgrep_rules(filename: str) -> Path:
    return repo_root() / "rules" / "semgrep" / filename


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
        detectors = []
        rules = _semgrep_rules("sql_go.yaml")
        if semgrep_available() and rules.exists():
            detectors.append(SemgrepDetector(rules, language="go"))
        return detectors
    if language == "rust":
        detectors = []
        rules = _semgrep_rules("sql_rust.yaml")
        if semgrep_available() and rules.exists():
            detectors.append(SemgrepDetector(rules, language="rust"))
        return detectors
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
