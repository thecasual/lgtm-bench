"""TypeScript cross-site-scripting detector-corpus runner (TECH_SPEC 7.4).

Runs the language-aware ``xss`` pack (Semgrep, ``rules/semgrep/xss_typescript.yaml``)
against each labeled sample under ``tests/detector_corpus/xss-typescript/`` and
asserts:

- files under ``vulnerable/`` yield >= 1 finding;
- files under ``safe/`` yield exactly 0 findings.

Grading goes through ``_run_pack`` with a ``language="typescript"`` /
``category="xss"`` TaskSpec, exactly as the harness grades a real TypeScript
xss trial. Parametrized by file path so a failure names the exact sample.
Mirrors ``test_corpus_sql_typescript.py`` / ``test_corpus_cmdi_typescript.py``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lgtm_bench.detectors.semgrep import semgrep_available
from lgtm_bench.grading import _run_pack
from lgtm_bench.schema import ArtifactKind, Condition, DetectorRef, TaskSpec, Variant

CORPUS = Path(__file__).resolve().parent / "detector_corpus" / "xss-typescript"

VULNERABLE = sorted((CORPUS / "vulnerable").glob("*.ts"))
SAFE = sorted((CORPUS / "safe").glob("*.ts"))

# TypeScript has no AST backstop: semgrep is the ONLY detector for this
# language, so if it is unavailable these corpus tests are the only thing
# standing between a broken sandbox and every xss-typescript trial silently
# grading "secure" (det-1). A skipif here would read green on a semgrep-less
# machine and hide exactly the failure mode this file exists to catch, so
# fail loudly instead.
@pytest.fixture
def requires_semgrep():
    if not semgrep_available():
        pytest.fail(
            "semgrep binary not available: xss-typescript detector-corpus "
            "tests cannot be skipped, they are the only check that "
            "xss-typescript trials actually get graded. Install semgrep or "
            "set LGTM_SEMGREP_BIN (this sandbox ships one at "
            "/opt/semgrep-venv/bin/semgrep), then re-run.",
            pytrace=False,
        )


def _ts_task() -> TaskSpec:
    return TaskSpec(
        id="xss-typescript/detector-corpus-dummy",
        category="xss",
        title="typescript xss detector corpus dummy task",
        language="typescript",
        conditions=[Condition.NONE],
        artifact=ArtifactKind.FUNCTION,
        variants=[Variant(id="v1", prompt="corpus sample")],
        detectors=[DetectorRef(pack="xss")],
    )


def _describe(findings) -> str:
    return "; ".join(f"{f.detector}:{f.rule_id}" for f in findings) or "<none>"


def test_corpus_is_populated():
    assert len(VULNERABLE) >= 10, (
        f"expected >=10 vulnerable .ts samples, found {len(VULNERABLE)}")
    assert len(SAFE) >= 10, (
        f"expected >=10 safe .ts samples, found {len(SAFE)}")


@pytest.mark.parametrize("path", VULNERABLE, ids=lambda p: p.name)
def test_vulnerable_xss_typescript_sample_is_flagged(requires_semgrep, path: Path):
    findings = _run_pack(path.read_text(), _ts_task())
    assert findings, f"{path.name}: labeled vulnerable but no detector fired"


@pytest.mark.parametrize("path", SAFE, ids=lambda p: p.name)
def test_safe_xss_typescript_sample_is_clean(requires_semgrep, path: Path):
    findings = _run_pack(path.read_text(), _ts_task())
    assert not findings, (
        f"{path.name}: labeled safe but got findings: {_describe(findings)}")
