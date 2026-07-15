"""Rust SQL-injection detector-corpus runner (sql-rust pack, v0.1).

Runs the `sql` pack (language=rust -> Semgrep with rules/semgrep/sql_rust.yaml)
against each labeled sample under ``tests/detector_corpus/sql-rust/`` and
asserts, exactly the way the grading pipeline does (via ``_run_pack`` with a
``language="rust"`` TaskSpec):

- files under ``vulnerable/`` yield >= 1 finding;
- files under ``safe/``       yield exactly 0 findings.

Parametrized by file path so a failure names the exact sample.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lgtm_bench.detectors.semgrep import semgrep_available
from lgtm_bench.grading import _run_pack
from lgtm_bench.schema import ArtifactKind, Condition, TaskSpec, Variant

CORPUS = Path(__file__).resolve().parent / "detector_corpus" / "sql-rust"

VULNERABLE = sorted((CORPUS / "vulnerable").glob("*.rs"))
SAFE = sorted((CORPUS / "safe").glob("*.rs"))

# Rust has no AST backstop: semgrep is the ONLY detector for this language, so
# if it is unavailable these corpus tests are the only thing standing between
# a broken sandbox and every rust trial silently grading "secure" (det-1). A
# skipif here would read green on a semgrep-less machine and hide exactly the
# failure mode this file exists to catch, so fail loudly instead.
@pytest.fixture
def requires_semgrep():
    if not semgrep_available():
        pytest.fail(
            "semgrep binary not available: rust detector-corpus tests cannot "
            "be skipped, they are the only check that rust trials actually "
            "get graded. Install semgrep or set LGTM_SEMGREP_BIN (this "
            "sandbox ships one at /opt/semgrep-venv/bin/semgrep), then "
            "re-run.",
            pytrace=False,
        )


def _rust_task() -> TaskSpec:
    return TaskSpec(
        id="sql-rust/detector-corpus-dummy",
        category="sql",
        title="rust detector corpus dummy task",
        language="rust",
        conditions=[Condition.NONE],
        artifact=ArtifactKind.FUNCTION,
        variants=[Variant(id="v1", prompt="corpus sample")],
    )


def _describe(findings) -> str:
    return "; ".join(f"{f.detector}:{f.rule_id}" for f in findings) or "<none>"


def test_corpus_is_populated():
    assert len(VULNERABLE) >= 10, \
        f"expected >=10 vulnerable .rs samples, found {len(VULNERABLE)}"
    assert len(SAFE) >= 10, \
        f"expected >=10 safe .rs samples, found {len(SAFE)}"


@pytest.mark.parametrize("path", VULNERABLE, ids=lambda p: p.name)
def test_vulnerable_rust_sample_is_flagged(requires_semgrep, path: Path):
    findings = _run_pack(path.read_text(), _rust_task())
    assert findings, f"{path.name}: labeled vulnerable but no detector fired"


@pytest.mark.parametrize("path", SAFE, ids=lambda p: p.name)
def test_safe_rust_sample_is_clean(requires_semgrep, path: Path):
    findings = _run_pack(path.read_text(), _rust_task())
    assert not findings, (
        f"{path.name}: labeled safe but got findings: {_describe(findings)}"
    )
