"""Python command-injection detector-corpus runner (TECH_SPEC 7.4).

Runs the language-aware ``command-injection`` pack (the in-process AST detector
``cmdi_ast.CmdiAstDetector``) against each labeled sample under
``tests/detector_corpus/command-injection-python/`` and asserts:

- files under ``vulnerable/`` yield >= 1 finding;
- files under ``safe/`` yield exactly 0 findings.

Grading goes through ``_run_pack`` with a ``language="python"`` TaskSpec, exactly
as the harness grades a real python trial. Parametrized by file path so a
failure names the exact sample. Mirrors ``test_corpus_go.py``.

Unlike the semgrep-backed cells, python command-injection has an in-process AST
detector, so it needs no external binary. The ``requires_semgrep`` fixture is
kept for structural parity with the other corpus runners but is a no-op here:
the cmdi-python pack is AST-only, so there is no semgrep dependency to fail on.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lgtm_bench.grading import _run_pack
from lgtm_bench.schema import ArtifactKind, Condition, TaskSpec, Variant

CORPUS = Path(__file__).resolve().parent / "detector_corpus" / "command-injection-python"

VULNERABLE = sorted((CORPUS / "vulnerable").glob("*.py"))
SAFE = sorted((CORPUS / "safe").glob("*.py"))


# The cmdi-python pack is the in-process AST detector, not semgrep, so nothing
# external is required to grade it. The fixture exists only so this runner has
# the same shape as the semgrep-backed corpus runners.
@pytest.fixture
def requires_semgrep():
    return None


def _py_task() -> TaskSpec:
    return TaskSpec(
        id="cmdi-python/detector-corpus-dummy",
        category="command-injection",
        title="python command-injection detector corpus dummy task",
        language="python",
        conditions=[Condition.NONE],
        artifact=ArtifactKind.FUNCTION,
        variants=[Variant(id="v1", prompt="corpus sample")],
        detectors=[{"pack": "command-injection"}],
    )


def _describe(findings) -> str:
    return "; ".join(f"{f.detector}:{f.rule_id}" for f in findings) or "<none>"


def test_corpus_is_populated():
    assert len(VULNERABLE) >= 10, (
        f"expected >=10 vulnerable .py samples, found {len(VULNERABLE)}")
    assert len(SAFE) >= 10, (
        f"expected >=10 safe .py samples, found {len(SAFE)}")


@pytest.mark.parametrize("path", VULNERABLE, ids=lambda p: p.name)
def test_vulnerable_python_sample_is_flagged(requires_semgrep, path: Path):
    findings = _run_pack(path.read_text(), _py_task())
    assert findings, f"{path.name}: labeled vulnerable but no detector fired"


@pytest.mark.parametrize("path", SAFE, ids=lambda p: p.name)
def test_safe_python_sample_is_clean(requires_semgrep, path: Path):
    findings = _run_pack(path.read_text(), _py_task())
    assert not findings, (
        f"{path.name}: labeled safe but got findings: {_describe(findings)}")
