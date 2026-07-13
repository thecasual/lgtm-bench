"""Detector-corpus runner (TECH_SPEC §7.4).

Runs every detector in the `sql` pack against each labeled sample under
``tests/detector_corpus/sql/`` and asserts:

- files under ``vulnerable/`` (and ``raw/vulnerable/``) yield >= 1 finding;
- files under ``safe/`` (and ``raw/safe/``) yield exactly 0 findings.

Parametrized by file path so a failure names the exact sample.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from lgtm_bench.detectors import get_pack
from lgtm_bench.grading import _run_pack
from lgtm_bench.schema import ArtifactKind, Condition, TaskSpec, Variant

CORPUS = Path(__file__).resolve().parent / "detector_corpus" / "sql"

PY_VULNERABLE = sorted((CORPUS / "vulnerable").glob("*.py"))
PY_SAFE = sorted((CORPUS / "safe").glob("*.py"))
RAW_VULNERABLE = sorted((CORPUS / "raw" / "vulnerable").glob("*.sql"))
RAW_SAFE = sorted((CORPUS / "raw" / "safe").glob("*.sql"))


def _dummy_task(artifact: ArtifactKind) -> TaskSpec:
    return TaskSpec(
        id="sql/detector-corpus-dummy",
        category="sql",
        title="detector corpus dummy task",
        conditions=[Condition.NONE],
        artifact=artifact,
        variants=[Variant(id="v1", prompt="corpus sample")],
    )


@pytest.fixture(scope="module")
def pack():
    return get_pack("sql")


def _scan(pack, path: Path, artifact: ArtifactKind):
    # Grade exactly the way the pipeline does: union of pack findings with
    # AST-cleared lines suppressing coarser pattern matches (grading.§7.2).
    code = path.read_text()
    task = _dummy_task(artifact)
    return _run_pack(code, task)


def _describe(findings) -> str:
    return "; ".join(f"{f.detector}:{f.rule_id}" for f in findings) or "<none>"


def test_corpus_is_populated():
    assert len(PY_VULNERABLE) >= 14, f"expected >=14 vulnerable .py samples, found {len(PY_VULNERABLE)}"
    assert len(PY_SAFE) >= 14, f"expected >=14 safe .py samples, found {len(PY_SAFE)}"
    assert len(RAW_VULNERABLE) >= 3, f"expected >=3 vulnerable raw .sql samples, found {len(RAW_VULNERABLE)}"
    assert len(RAW_SAFE) >= 3, f"expected >=3 safe raw .sql samples, found {len(RAW_SAFE)}"


@pytest.mark.parametrize("path", PY_VULNERABLE + PY_SAFE, ids=lambda p: p.name)
def test_python_sample_parses(path: Path):
    # A syntax error would make detectors return no findings, silently
    # corrupting the corpus; require every .py sample to parse.
    ast.parse(path.read_text())


@pytest.mark.parametrize("path", PY_VULNERABLE, ids=lambda p: p.name)
def test_vulnerable_python_sample_is_flagged(pack, path: Path):
    findings = _scan(pack, path, ArtifactKind.FUNCTION)
    assert findings, f"{path.name}: labeled vulnerable but no detector fired"


@pytest.mark.parametrize("path", PY_SAFE, ids=lambda p: p.name)
def test_safe_python_sample_is_clean(pack, path: Path):
    findings = _scan(pack, path, ArtifactKind.FUNCTION)
    assert not findings, (
        f"{path.name}: labeled safe but got findings: {_describe(findings)}"
    )


@pytest.mark.parametrize("path", RAW_VULNERABLE, ids=lambda p: p.name)
def test_vulnerable_raw_sql_sample_is_flagged(pack, path: Path):
    findings = _scan(pack, path, ArtifactKind.RAW_SQL)
    assert findings, f"{path.name}: labeled vulnerable but no detector fired"


@pytest.mark.parametrize("path", RAW_SAFE, ids=lambda p: p.name)
def test_safe_raw_sql_sample_is_clean(pack, path: Path):
    findings = _scan(pack, path, ArtifactKind.RAW_SQL)
    assert not findings, (
        f"{path.name}: labeled safe but got findings: {_describe(findings)}"
    )
