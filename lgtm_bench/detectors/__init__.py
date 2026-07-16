"""Detector packs (TECH_SPEC §7). A pack is a list of detectors; a finding
from any detector in the pack yields a `vulnerable` verdict."""
from __future__ import annotations

from pathlib import Path

from .base import Detector
from .semgrep import SemgrepDetector, semgrep_available
from .sql_ast import SqlAstDetector

PACK_VERSIONS = {
    "sql":                          "sql@0.9.0",
    "sql-go":                       "sql-go@0.3.0",
    "sql-rust":                     "sql-rust@0.3.0",
    "sql-typescript":               "sql-typescript@0.3.1",
    "command-injection-python":     "cmdi-python@0.1.1",
    "command-injection-typescript": "cmdi-typescript@0.2.0",
    "xss-typescript":               "xss-typescript@0.3.1",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _semgrep_rules(filename: str) -> Path:
    return repo_root() / "rules" / "semgrep" / filename


def _require_semgrep_pack(language: str, rules_filename: str) -> list[Detector]:
    """Build a semgrep-backed pack, or raise RuntimeError rather than silently
    returning an empty detector list.

    Unlike python (which has an AST backstop detector), the semgrep-backed
    languages have NO backstop: semgrep is the ONLY detector for these cells.
    Returning an empty list here used to mean every such trial graded "secure"
    by default while grading.py still stamped the trial with the audited pack
    version, as if the rules had actually run. Fail loud instead."""
    rules = _semgrep_rules(rules_filename)
    if not semgrep_available():
        raise RuntimeError(
            f"cannot build the {rules_filename} detector pack: no semgrep "
            "binary found. This cell has no AST backstop, so semgrep is "
            "required to grade this language at all. Fix by installing "
            "semgrep, or by pointing LGTM_SEMGREP_BIN at an existing install "
            "(this sandbox ships one at /opt/semgrep-venv/bin/semgrep)."
        )
    if not rules.exists():
        raise RuntimeError(
            f"cannot build the {rules_filename} detector pack: rules file "
            f"missing at {rules}. Fix by restoring "
            f"rules/semgrep/{rules_filename} in the repo."
        )
    return [SemgrepDetector(rules, language=language)]


def get_pack(name: str, language: str = "python") -> list[Detector]:
    if name == "sql":
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
        if language == "typescript":
            return _require_semgrep_pack("typescript", "sql_typescript.yaml")
        raise KeyError(f"unsupported language for pack {name!r}: {language}")
    if name == "command-injection":
        if language == "python":
            # AST-only, no semgrep companion. Lazy import: the leaf detector
            # file arrives in a later package, so importing at module load
            # would break this whole module before that file exists.
            from .cmdi_ast import CmdiAstDetector
            return [CmdiAstDetector()]
        if language == "typescript":
            return _require_semgrep_pack("typescript", "cmdi_typescript.yaml")
        raise KeyError(f"unsupported language for command-injection: {language}")
    if name == "xss":
        if language == "typescript":
            return _require_semgrep_pack("typescript", "xss_typescript.yaml")
        # python xss is deferred; fail loud rather than grade silently secure.
        raise KeyError(f"unsupported language for xss: {language}")
    raise KeyError(f"unknown detector pack: {name}")


def pack_version(name: str) -> str:
    return PACK_VERSIONS.get(name, f"{name}@unversioned")


def pack_version_for(name: str, language: str = "python") -> str:
    """The pack version string a trial should record, keyed by language so a
    trial names the language pack that graded it. Tries the language-qualified
    key (`<name>-<language>`) first, then the legacy bare key (python sql is
    keyed bare `sql`), then a clearly-unversioned fallback."""
    for key in (f"{name}-{language}", name):
        if key in PACK_VERSIONS:
            return PACK_VERSIONS[key]
    return f"{name}-{language}@unversioned"
