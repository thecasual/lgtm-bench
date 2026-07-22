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

# Go has no AST backstop: semgrep is the ONLY detector for this language, so
# if it is unavailable these corpus tests are the only thing standing between
# a broken sandbox and every go trial silently grading "secure" (det-1). A
# skipif here would read green on a semgrep-less machine and hide exactly the
# failure mode this file exists to catch, so fail loudly instead.
@pytest.fixture
def requires_semgrep():
    if not semgrep_available():
        pytest.fail(
            "semgrep binary not available: go detector-corpus tests cannot "
            "be skipped, they are the only check that go trials actually "
            "get graded. Install semgrep or set LGTM_SEMGREP_BIN (this "
            "sandbox ships one at /opt/semgrep-venv/bin/semgrep), then "
            "re-run.",
            pytrace=False,
        )


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


@pytest.mark.parametrize("path", VULNERABLE, ids=lambda p: p.name)
def test_vulnerable_go_sample_is_flagged(requires_semgrep, path: Path):
    findings = _run_pack(path.read_text(), _go_task())
    assert findings, f"{path.name}: labeled vulnerable but no detector fired"


@pytest.mark.parametrize("path", SAFE, ids=lambda p: p.name)
def test_safe_go_sample_is_clean(requires_semgrep, path: Path):
    findings = _run_pack(path.read_text(), _go_task())
    assert not findings, (
        f"{path.name}: labeled safe but got findings: {_describe(findings)}")
