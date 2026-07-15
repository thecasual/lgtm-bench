"""Multi-language plumbing (go/rust) for the SQL-injection benchmark.

Verifies the language-aware pack wiring, the go/rust corpus stubs grade
correctly, the go/rust validity heuristics, and that TrialRecord carries the
task language. The full rules + corpus arrive later from the language agents;
these tests only prove the plumbing is live.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from lgtm_bench.detectors import PACK_VERSIONS, get_pack, pack_version_for
from lgtm_bench.detectors.semgrep import semgrep_available
from lgtm_bench.grading import _is_valid, _is_valid_go, _is_valid_rust, _run_pack
from lgtm_bench.schema import (ArtifactKind, Condition, TaskSpec, TrialRecord,
                               Variant, Mode)

CORPUS = Path(__file__).resolve().parent / "detector_corpus"

# Matches a friendly pack slug of the shape "<slug>@x.y.z" (e.g. "sql@0.9.0",
# "sql-go@0.3.0", "cmdi-python@0.1.0", "xss-typescript@0.1.0") but NOT a string
# that silently reverts to an unversioned fallback (see pack_version()'s
# "{name}@unversioned" default).
_PACK_VERSION_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*@\d+\.\d+\.\d+$")

# The go/rust detector tests below (and test_corpus_go.py / test_corpus_rust.py)
# are the ONLY guard against det-1 (get_pack silently returning an empty
# detector list). On a semgrep-less machine that guard must fail loudly
# rather than "skip" and read green, because go/rust have no AST backstop:
# semgrep missing means the benchmark cannot grade those languages at all.
# This is a fixture (not a skipif-replacement decorator) so it composes
# cleanly with pytest.mark.parametrize on the tests below.
@pytest.fixture
def requires_semgrep():
    if not semgrep_available():
        pytest.fail(
            "semgrep binary not available: go/rust detector tests cannot be "
            "skipped, they are the only check that go/rust trials actually "
            "get graded. Install semgrep or set LGTM_SEMGREP_BIN (this "
            "sandbox ships one at /opt/semgrep-venv/bin/semgrep), then "
            "re-run.",
            pytrace=False,
        )


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

@pytest.mark.parametrize("language", ["go", "rust"])
def test_get_pack_returns_detector_for_language(requires_semgrep, language: str):
    pack = get_pack("sql", language)
    assert len(pack) >= 1
    assert all(hasattr(d, "scan") for d in pack)


def test_pack_version_for_by_language():
    # Compare against PACK_VERSIONS directly (not a hardcoded literal) so a
    # future version bump can't silently break this test, or worse, silently
    # keep passing against a stale expectation while the real pack moved on.
    assert pack_version_for("sql", "python") == PACK_VERSIONS["sql"]
    assert pack_version_for("sql", "go") == PACK_VERSIONS["sql-go"]
    assert pack_version_for("sql", "rust") == PACK_VERSIONS["sql-rust"]
    # The new language-qualified cells resolve to their friendly slugs too:
    # a typescript SQL cell and a python command-injection cell.
    assert pack_version_for("sql", "typescript") == PACK_VERSIONS["sql-typescript"]
    assert (pack_version_for("command-injection", "python")
            == PACK_VERSIONS["command-injection-python"])
    # Format check: every pack version string must look like name@x.y.z, so
    # a bump that produces e.g. an unversioned fallback ("sql-go@unversioned")
    # can't trivially satisfy the equality checks above by coincidence.
    for value in PACK_VERSIONS.values():
        assert _PACK_VERSION_RE.match(value), f"malformed pack version: {value!r}"


# --- corpus grades correctly ----------------------------------------------

@pytest.mark.parametrize("language,ext", [("go", "go"), ("rust", "rs")])
def test_vulnerable_corpus_is_flagged(requires_semgrep, language: str, ext: str):
    task = _task(language)
    for path in sorted((CORPUS / f"sql-{language}" / "vulnerable").glob(f"*.{ext}")):
        findings = _run_pack(path.read_text(), task)
        assert findings, f"{path.name}: labeled vulnerable but no detector fired"


@pytest.mark.parametrize("language,ext", [("go", "go"), ("rust", "rs")])
def test_safe_corpus_is_clean(requires_semgrep, language: str, ext: str):
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
