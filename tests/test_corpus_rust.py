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

requires_semgrep = pytest.mark.skipif(
    not semgrep_available(), reason="semgrep binary not available")


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


@requires_semgrep
@pytest.mark.parametrize("path", VULNERABLE, ids=lambda p: p.name)
def test_vulnerable_rust_sample_is_flagged(path: Path):
    findings = _run_pack(path.read_text(), _rust_task())
    assert findings, f"{path.name}: labeled vulnerable but no detector fired"


@requires_semgrep
@pytest.mark.parametrize("path", SAFE, ids=lambda p: p.name)
def test_safe_rust_sample_is_clean(path: Path):
    findings = _run_pack(path.read_text(), _rust_task())
    assert not findings, (
        f"{path.name}: labeled safe but got findings: {_describe(findings)}"
    )
