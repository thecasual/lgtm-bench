"""Regression test for dryrun-1: SemgrepDetector.scan() must never surface
semgrep's OSS-unauthenticated "requires login" placeholder as a finding
snippet.

Background: semgrep 1.169.0 (OSS, unauthenticated) always emits the literal
string "requires login" in each result's `extra.lines` field instead of the
matched source text (that field is gated behind a paid/logged-in feature).
The old code in semgrep.py trusted `extra.lines` directly, so every semgrep
finding in the published data carried that fabricated snippet instead of real
code. scan() now reconstructs the snippet itself by slicing the `code` string
it already has, using the match's start/end line numbers.
"""
from __future__ import annotations

import pytest

from lgtm_bench.detectors import get_pack
from lgtm_bench.detectors.semgrep import semgrep_available
from lgtm_bench.schema import ArtifactKind, Condition, TaskSpec, Variant

# This is exactly the kind of check det-2/det-3 exist to enforce elsewhere:
# on a semgrep-less machine this test cannot meaningfully run (there is no
# code path left to exercise), so fail loudly rather than skip quietly.
@pytest.fixture
def requires_semgrep():
    if not semgrep_available():
        pytest.fail(
            "semgrep binary not available: the snippet-reconstruction "
            "regression test cannot run without it. Install semgrep or set "
            "LGTM_SEMGREP_BIN (this sandbox ships one at "
            "/opt/semgrep-venv/bin/semgrep), then re-run.",
            pytrace=False,
        )


# A known-vulnerable Go snippet: untrusted input interpolated into a query
# string via fmt.Sprintf, then passed straight to conn.Query. Mirrors
# tests/detector_corpus/sql-go/vulnerable/v01_sprintf_into_query.go, kept
# inline here so this test doesn't depend on that corpus file's contents.
VULNERABLE_GO_SNIPPET = (
    "package db\n"
    "\n"
    "import (\n"
    "\t\"database/sql\"\n"
    "\t\"fmt\"\n"
    ")\n"
    "\n"
    "// getUserByName interpolates untrusted input into the query with Sprintf.\n"
    "func getUserByName(conn *sql.DB, name string) (*sql.Rows, error) {\n"
    "\tquery := fmt.Sprintf(\"SELECT id, name FROM users WHERE name = '%s'\", name)\n"
    "\treturn conn.Query(query)\n"
    "}\n"
)


def _go_task() -> TaskSpec:
    return TaskSpec(
        id="sql-go/snippet-regression-dummy",
        category="sql",
        title="go snippet regression dummy task",
        language="go",
        conditions=[Condition.NONE],
        artifact=ArtifactKind.FUNCTION,
        variants=[Variant(id="v1", prompt="corpus sample")],
    )


def test_snippet_is_real_code_not_requires_login(requires_semgrep):
    pack = get_pack("sql", "go")
    task = _go_task()

    findings = []
    for detector in pack:
        findings.extend(detector.scan(VULNERABLE_GO_SNIPPET, task))

    assert findings, "expected the known-vulnerable snippet to be flagged"

    for f in findings:
        # The fabricated placeholder semgrep 1.169.0 OSS/unauthenticated
        # emits in extra.lines. If this ever appears, scan() went back to
        # trusting extra.lines instead of reconstructing from `code`.
        assert f.snippet != "requires login", (
            f"finding {f.rule_id} carries the fabricated 'requires login' "
            "snippet instead of real code")
        if f.snippet is not None:
            assert f.snippet in VULNERABLE_GO_SNIPPET, (
                f"finding {f.rule_id} snippet {f.snippet!r} is not a "
                "substring of the scanned code")
