"""Detector packs (TECH_SPEC §7). A pack is a list of detectors; a finding
from any detector in the pack yields a `vulnerable` verdict."""
from __future__ import annotations

from pathlib import Path

from .base import Detector
from .semgrep import SemgrepDetector, semgrep_available
from .sql_ast import SqlAstDetector

PACK_VERSIONS = {"sql": "sql@0.4.0"}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_pack(name: str) -> list[Detector]:
    if name == "sql":
        detectors: list[Detector] = [SqlAstDetector()]
        rules = repo_root() / "rules" / "semgrep" / "sql.yaml"
        if semgrep_available() and rules.exists():
            detectors.append(SemgrepDetector(rules))
        return detectors
    raise KeyError(f"unknown detector pack: {name}")


def pack_version(name: str) -> str:
    return PACK_VERSIONS.get(name, f"{name}@unversioned")
