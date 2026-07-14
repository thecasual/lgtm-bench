"""Go SQL-injection detector-corpus runner (TECH_SPEC §7.4).

Runs the language-aware ``sql`` pack (Semgrep, ``rules/semgrep/sql_go.yaml``)
against each labeled sample under ``tests/detector_corpus/sql-go/`` and asserts:

- files under ``vulnerable/`` yield >= 1 finding;
- files under ``safe/`` yield exactly 0 findings.

Grading goes through ``_run_pack`` with a ``language="go"`` TaskSpec, exactly as
the harness grades a real Go trial. Parametrized by file path so a failure names
the exact sample.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lgtm_bench.detectors.semgrep import semgrep_available
from lgtm_bench.grading import _run_pack
from lgtm_bench.schema import ArtifactKind, Condition, TaskSpec, Variant

CORPUS = Path(__file__).resolve().parent / "detector_corpus" / "sql-go"

VULNERABLE = sorted((CORPUS / "vulnerable").glob("*.go"))
SAFE = sorted((CORPUS / "safe").glob("*.go"))

requires_semgrep = pytest.mark.skipif(
    not semgrep_available(), reason="semgrep binary not available")


def _go_task() -> TaskSpec:
    return TaskSpec(
        id="sql-go/detector-corpus-dummy",
        category="sql",
        title="go detector corpus dummy task",
        language="go",
        conditions=[Condition.NONE],
        artifact=ArtifactKind.FUNCTION,
        variants=[Variant(id="v1", prompt="corpus sample")],
    )


def _describe(findings) -> str:
    return "; ".join(f"{f.detector}:{f.rule_id}" for f in findings) or "<none>"


def test_corpus_is_populated():
    assert len(VULNERABLE) >= 10, (
        f"expected >=10 vulnerable .go samples, found {len(VULNERABLE)}")
    assert len(SAFE) >= 10, (
        f"expected >=10 safe .go samples, found {len(SAFE)}")


@requires_semgrep
@pytest.mark.parametrize("path", VULNERABLE, ids=lambda p: p.name)
def test_vulnerable_go_sample_is_flagged(path: Path):
    findings = _run_pack(path.read_text(), _go_task())
    assert findings, f"{path.name}: labeled vulnerable but no detector fired"


@requires_semgrep
@pytest.mark.parametrize("path", SAFE, ids=lambda p: p.name)
def test_safe_go_sample_is_clean(path: Path):
    findings = _run_pack(path.read_text(), _go_task())
    assert not findings, (
        f"{path.name}: labeled safe but got findings: {_describe(findings)}")
