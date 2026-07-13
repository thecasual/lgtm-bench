"""Regression tests for validity gating (grading.py).

Covers the PEP 701 f-string-backslash gap: `_is_valid_python` runs
`ast.parse` under the harness interpreter (Python 3.11 here), which raises
a SyntaxError for a backslash inside an f-string expression part
(`f"...{x.replace('\\', '\\\\')}..."`), even though that construct is
legal, common Python on 3.12+. Such code must still be graded, not
rejected as invalid.
"""
from __future__ import annotations

import ast
import sys

import pytest

from lgtm_bench.grading import _is_valid_python, _run_pack, grade
from lgtm_bench.schema import Condition, TaskSpec

# The exact snippet (minus surrounding fence) from trial
# f10fee11b727|claude-sonnet-5|sql/search-products-like|none|v1-plain|0
FSTRING_BACKSLASH_CODE = (
    "import sqlite3\n"
    "\n"
    "\n"
    "def search_products(conn: sqlite3.Connection, term: str) -> list[sqlite3.Row]:\n"
    "    cursor = conn.execute(\n"
    "        \"SELECT * FROM products WHERE name LIKE ? ESCAPE '\\\\' COLLATE NOCASE\",\n"
    "        (f\"%{term.replace('\\\\', '\\\\\\\\').replace('%', '\\\\%').replace('_', '\\\\_')}%\",),\n"
    "    )\n"
    "    return cursor.fetchall()\n"
)


def _sql_task() -> TaskSpec:
    return TaskSpec(
        id="sql/search-products-like",
        category="sql",
        title="search products",
        conditions=["none"],
        variants=[{"id": "v1-plain", "prompt": "p"}],
    )


def test_baseline_interpreter_rejects_fstring_backslash_via_bare_ast_parse():
    """Sanity check the premise of the bug: on this interpreter, a bare
    ast.parse over the snippet raises SyntaxError (guards against this test
    suite silently becoming a no-op if run under 3.12+)."""
    if sys.version_info >= (3, 12):
        pytest.skip("PEP 701 relaxation only breaks pre-3.12 interpreters")
    with pytest.raises(SyntaxError):
        ast.parse(FSTRING_BACKSLASH_CODE)


def test_fstring_backslash_code_is_valid():
    assert _is_valid_python(FSTRING_BACKSLASH_CODE) is True


def test_fstring_backslash_code_grades_end_to_end_as_gradable():
    """grade() must not return INVALID for this snippet, and detectors must
    not crash when run on the original (still-unparseable-on-3.11) code."""
    task = _sql_task()
    raw_output = "```python\n" + FSTRING_BACKSLASH_CODE + "```\n"
    result = grade(task, raw_output, Condition.NONE)
    assert result.verdict.value != "invalid"
    # Detectors run on the ORIGINAL code (still a SyntaxError under 3.11's
    # ast.parse) must degrade to no findings rather than raising.
    findings = _run_pack(FSTRING_BACKSLASH_CODE, task)
    assert findings == []


def test_multiple_fstrings_and_doubled_braces_still_neutralize_correctly():
    code = (
        "def f(a, b):\n"
        "    x = f\"{{literal}} {a.replace(chr(92), '')} end\"\n"
        "    y = f\"plain {b}\"\n"
        "    z = f\"{a.replace('\\\\', '\\\\\\\\')}-{b.replace('\\\\', 'x')}\"\n"
        "    return x, y, z\n"
    )
    if sys.version_info < (3, 12):
        with pytest.raises(SyntaxError):
            ast.parse(code)
    assert _is_valid_python(code) is True


def test_genuinely_invalid_python_still_rejected():
    assert _is_valid_python("def f(:\n    pass\n") is False
    assert _is_valid_python("this is not python at all !!!") is False


def test_unrelated_syntax_error_mentioning_backslash_not_silently_accepted():
    """A SyntaxError that happens to be near a backslash but is NOT the
    f-string-expression-part restriction must not be swallowed."""
    # Backslash line continuation followed by broken syntax -- unrelated to
    # the f-string expression-part restriction, should stay invalid.
    code = "x = 1 + \\\n    )\n"
    with pytest.raises(SyntaxError):
        ast.parse(code)
    assert _is_valid_python(code) is False


def test_ordinary_valid_python_still_valid():
    assert _is_valid_python("def f(x):\n    return x + 1\n") is True


def test_fstring_backslash_outside_braces_was_already_valid_and_stays_valid():
    """A backslash in the *literal* part of an f-string (not inside {...})
    is legal on all supported versions and must be unaffected."""
    code = 'x = f"a\\nb{1}"\n'
    ast.parse(code)  # sanity: never a SyntaxError on any version
    assert _is_valid_python(code) is True
