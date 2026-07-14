"""Multi-language plumbing (go/rust) for the SQL-injection benchmark.

Verifies the language-aware pack wiring, the go/rust corpus stubs grade
correctly, the go/rust validity heuristics, and that TrialRecord carries the
task language. The full rules + corpus arrive later from the language agents;
these tests only prove the plumbing is live.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lgtm_bench.detectors import get_pack, pack_version_for
from lgtm_bench.detectors.semgrep import semgrep_available
from lgtm_bench.grading import _is_valid, _is_valid_go, _is_valid_rust, _run_pack
from lgtm_bench.schema import (ArtifactKind, Condition, TaskSpec, TrialRecord,
                               Variant, Mode)

CORPUS = Path(__file__).resolve().parent / "detector_corpus"

requires_semgrep = pytest.mark.skipif(
    not semgrep_available(), reason="semgrep binary not available")


def _task(language: str) -> TaskSpec:
    return TaskSpec(
        id=f"sql/multilang-{language}",
        category="sql",
        title=f"{language} corpus dummy",
        language=language,
        conditions=[Condition.NONE],
        artifact=ArtifactKind.FUNCTION,
        variants=[Variant(id="v1", prompt="corpus sample")],
    )


# --- pack wiring -----------------------------------------------------------

@requires_semgrep
@pytest.mark.parametrize("language", ["go", "rust"])
def test_get_pack_returns_detector_for_language(language: str):
    pack = get_pack("sql", language)
    assert len(pack) >= 1
    assert all(hasattr(d, "scan") for d in pack)


def test_pack_version_for_by_language():
    assert pack_version_for("sql", "python") == "sql@0.9.0"
    assert pack_version_for("sql", "go") == "sql-go@0.1.0"
    assert pack_version_for("sql", "rust") == "sql-rust@0.1.0"


# --- corpus grades correctly ----------------------------------------------

@requires_semgrep
@pytest.mark.parametrize("language,ext", [("go", "go"), ("rust", "rs")])
def test_vulnerable_corpus_is_flagged(language: str, ext: str):
    task = _task(language)
    for path in sorted((CORPUS / f"sql-{language}" / "vulnerable").glob(f"*.{ext}")):
        findings = _run_pack(path.read_text(), task)
        assert findings, f"{path.name}: labeled vulnerable but no detector fired"


@requires_semgrep
@pytest.mark.parametrize("language,ext", [("go", "go"), ("rust", "rs")])
def test_safe_corpus_is_clean(language: str, ext: str):
    task = _task(language)
    for path in sorted((CORPUS / f"sql-{language}" / "safe").glob(f"*.{ext}")):
        findings = _run_pack(path.read_text(), task)
        assert not findings, f"{path.name}: labeled safe but got {findings}"


# --- validity heuristics ---------------------------------------------------

def test_go_validity_heuristic():
    valid = "func getUser(name string) string {\n\treturn name\n}\n"
    assert _is_valid_go(valid) is True
    assert _is_valid(valid, _task("go")) is True
    prose = "Here is how you would safely query the database in Go."
    assert _is_valid_go(prose) is False
    assert _is_valid(prose, _task("go")) is False


def test_rust_validity_heuristic():
    valid = "fn get_user(name: &str) -> &str {\n    name\n}\n"
    assert _is_valid_rust(valid) is True
    assert _is_valid(valid, _task("rust")) is True
    prose = "Here is how you would safely query the database in Rust."
    assert _is_valid_rust(prose) is False
    assert _is_valid(prose, _task("rust")) is False


# --- trial record carries language ----------------------------------------

def test_trial_record_carries_language():
    rec = TrialRecord(
        trial_key="k", run_id="r", model="m", task_id="t", mode=Mode.GENERATE,
        language="go", condition=Condition.NONE, variant_id="v1",
        trial_index=0, prompt="p", raw_output="o", extracted_code="c",
        verdict="secure",
    )
    assert rec.language == "go"


def test_trial_record_language_defaults_to_python():
    rec = TrialRecord(
        trial_key="k", run_id="r", model="m", task_id="t", mode=Mode.GENERATE,
        condition=Condition.NONE, variant_id="v1", trial_index=0,
        prompt="p", raw_output="o", extracted_code="c", verdict="secure",
    )
    assert rec.language == "python"
