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


_LANG_EXT = {"python": ".py", "go": ".go", "rust": ".rs", "typescript": ".ts"}


class SemgrepScanError(RuntimeError):
    """Raised when semgrep could not actually analyze the target file, so a
    zero-finding result cannot be trusted as SECURE.

    Three failure shapes are surfaced this way instead of being swallowed into
    an empty (== SECURE) result: a subprocess timeout, unusable JSON output,
    and a scan that produced NO findings while semgrep reported a parse/syntax
    error on the target (the file was only partially parsed, so the missing
    findings may be false negatives). grading.py maps this to verdict INVALID
    for the semgrep-only languages (go/rust/typescript), which have no AST
    backstop, so a failed scan cannot masquerade as a graded-secure trial and
    is excluded from VIR denominators rather than counted as a clean pass.

    A scan that DID produce findings is authoritative even amid a partial
    parse elsewhere in the file, so this is never raised when results exist.
    """


def _has_target_parse_error(data: dict, target_name: str) -> bool:
    """True if semgrep reported a parse/syntax error on the scanned file.

    Semgrep emits these as `errors[].type == ["PartialParsing", ...]` (or a
    "Syntax error"/"Lexical error" message) with `path`/`spans` pointing at the
    target. We only trust an empty result set when NO such error was raised."""
    for err in data.get("errors", []) or []:
        etype = err.get("type")
        type_tag = etype[0] if isinstance(etype, list) and etype else etype
        message = err.get("message", "") or ""
        is_parse = (
            type_tag in ("PartialParsing", "SyntaxError", "LexicalError")
            or "syntax error" in message.lower()
            or "lexical error" in message.lower()
        )
        if not is_parse:
            continue
        # Scope to the file we scanned (path field, or any span's file).
        paths = {err.get("path")}
        for span in err.get("spans", []) or []:
            paths.add(span.get("file"))
        if any(p and p.endswith(target_name) for p in paths) or None in paths:
            return True
    return False


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
        target_name = f"snippet{ext}"
        with tempfile.TemporaryDirectory(prefix="lgtm-semgrep-") as td:
            target = Path(td) / target_name
            target.write_text(code)
            try:
                proc = subprocess.run(
                    [binary, "scan", "--config", str(self.rules_path), "--json",
                     "--quiet", "--metrics", "off", "--disable-version-check",
                     str(target)],
                    capture_output=True, text=True, timeout=120,
                )
            except subprocess.TimeoutExpired as e:
                # A timeout analyzed nothing; letting it become 0 results ==
                # SECURE would hide a possibly-vulnerable file. Surface it.
                raise SemgrepScanError(
                    f"semgrep timed out scanning a {self.language} snippet"
                ) from e
            try:
                data = json.loads(proc.stdout or "{}")
            except json.JSONDecodeError as e:
                raise SemgrepScanError(
                    f"semgrep produced unparseable JSON for a {self.language} "
                    f"snippet (returncode {proc.returncode})"
                ) from e
        results = data.get("results", [])
        # A file semgrep could not fully parse yields zero results, which is
        # indistinguishable from a genuinely-clean scan. When there are no
        # findings AND a parse/syntax error was reported on the target, the
        # zero is untrustworthy -> raise so grading marks the trial INVALID
        # rather than SECURE (det-2, det-3, pipe-4). A scan that DID find
        # something is authoritative even amid a partial parse, so we only
        # guard the empty case.
        if not results and _has_target_parse_error(data, target_name):
            raise SemgrepScanError(
                f"semgrep could not fully parse a {self.language} snippet "
                f"(partial parse, zero findings); result is not a trustworthy "
                f"SECURE and is marked invalid instead"
            )
        # Split once per scan; every finding slices from the same line list.
        # We do NOT trust extra.lines: OSS unauthenticated semgrep 1.169.0
        # emits the literal string "requires login" there instead of the
        # matched source, so we reconstruct the snippet ourselves from the
        # code we already sent it.
        code_lines = code.splitlines()
        findings = []
        for r in results:
            findings.append(Finding(
                detector=self.name,
                rule_id=r.get("check_id", "semgrep.unknown"),
                message=(r.get("extra", {}).get("message") or "").strip()[:300],
                line=r.get("start", {}).get("line"),
                snippet=self._snippet_from_code(code_lines, r),
            ))
        return findings

    @staticmethod
    def _snippet_from_code(code_lines: list[str], result: dict) -> str | None:
        """Slice the real matched source out of `code_lines` using the
        finding's start/end line (1-indexed, inclusive), instead of trusting
        semgrep's extra.lines field. Clamps out-of-range line numbers and
        returns None for an empty or unusable range."""
        start_line = result.get("start", {}).get("line")
        end_line = result.get("end", {}).get("line")
        if not isinstance(start_line, int) or not isinstance(end_line, int):
            return None
        total = len(code_lines)
        # Convert 1-indexed inclusive bounds to a 0-indexed slice, clamped to
        # the code we actually scanned.
        lo = max(start_line, 1) - 1
        hi = min(end_line, total)
        if lo >= hi or lo >= total or hi <= 0:
            return None
        snippet = "\n".join(code_lines[lo:hi])
        return snippet[:200] or None
