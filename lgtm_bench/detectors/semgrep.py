"""Semgrep-backed detector (TECH_SPEC §7.2, detector 1). Optional: if no
semgrep binary is available the pack runs with the AST backstop only, and the
run metadata records that."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from ..schema import ArtifactKind, Finding, TaskSpec

_CANDIDATES = [
    os.environ.get("LGTM_SEMGREP_BIN", ""),
    "/opt/semgrep-venv/bin/semgrep",
]


@lru_cache(maxsize=1)
def semgrep_bin() -> str | None:
    for cand in _CANDIDATES:
        if cand and Path(cand).exists():
            return cand
    return shutil.which("semgrep")


def semgrep_available() -> bool:
    return semgrep_bin() is not None


_LANG_EXT = {"python": ".py", "go": ".go", "rust": ".rs"}


class SemgrepDetector:
    name = "semgrep"

    def __init__(self, rules_path: Path, language: str = "python"):
        self.rules_path = rules_path
        self.language = language

    def scan(self, code: str, task: TaskSpec) -> list[Finding]:
        # The raw-sql short-circuit is python-only (go/rust have no raw-sql
        # artifact; that category is graded by the sqlglot detector).
        if self.language == "python" and task.artifact == ArtifactKind.RAW_SQL:
            return []
        binary = semgrep_bin()
        if binary is None:
            return []
        ext = _LANG_EXT.get(self.language, ".py")
        with tempfile.TemporaryDirectory(prefix="lgtm-semgrep-") as td:
            target = Path(td) / f"snippet{ext}"
            target.write_text(code)
            try:
                proc = subprocess.run(
                    [binary, "scan", "--config", str(self.rules_path), "--json",
                     "--quiet", "--metrics", "off", "--disable-version-check",
                     str(target)],
                    capture_output=True, text=True, timeout=120,
                )
                data = json.loads(proc.stdout or "{}")
            except (subprocess.TimeoutExpired, json.JSONDecodeError):
                return []
        findings = []
        for r in data.get("results", []):
            findings.append(Finding(
                detector=self.name,
                rule_id=r.get("check_id", "semgrep.unknown"),
                message=(r.get("extra", {}).get("message") or "").strip()[:300],
                line=r.get("start", {}).get("line"),
                snippet=(r.get("extra", {}).get("lines") or "")[:200] or None,
            ))
        return findings
