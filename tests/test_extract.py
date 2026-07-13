"""Code extraction from raw model output (extract.py)."""
from __future__ import annotations

from lgtm_bench.extract import extract_code, prose_text

PY_BODY = 'def get_user(conn, email):\n    return conn.execute("SELECT 1")'


def test_python_tagged_fence_preferred_over_other_fences():
    raw = (
        "Install it first:\n"
        "```bash\npip install flask\n```\n"
        "Then use this helper:\n"
        f"```python\n{PY_BODY}\n```\n"
        "And an untagged note:\n"
        "```\nsome untagged text\n```\n"
    )
    assert extract_code(raw, language="python") == PY_BODY


def test_multiple_tagged_blocks_concatenated_in_order():
    raw = (
        "Helper:\n```python\ndef helper(x):\n    return x\n```\n"
        "Usage:\n```py\nprint(helper(1))\n```\n"
    )
    assert extract_code(raw, language="python") == \
        "def helper(x):\n    return x\n\nprint(helper(1))"


def test_untagged_fence_fallback_when_no_language_tag_matches():
    raw = f"Here you go:\n```\n{PY_BODY}\n```\nEnjoy!"
    assert extract_code(raw, language="python") == PY_BODY


def test_no_fence_falls_back_to_whole_output():
    raw = "    def f(x):\n        return x + 1\n"
    # dedented and stripped whole-output heuristic
    assert extract_code(raw, language="python") == "def f(x):\n    return x + 1"


def test_only_foreign_tagged_fences_grades_largest_fence():
    small = "echo hi"
    big = "SELECT id, name, price\nFROM products\nWHERE name LIKE ?"
    raw = (
        f"```bash\n{small}\n```\n"
        f"```sql\n{big}\n```\n"
    )
    # language=python matches neither tag; the largest fence is graded anyway
    assert extract_code(raw, language="python") == big


def test_language_aliases_match_task_language():
    raw = f"```python3\n{PY_BODY}\n```"
    assert extract_code(raw, language="python") == PY_BODY
    raw_sql = "```sqlite\nSELECT * FROM users WHERE email = ?\n```"
    assert extract_code(raw_sql, language="sql") == \
        "SELECT * FROM users WHERE email = ?"


def test_prose_text_removes_code_and_keeps_prose():
    raw = (
        "The existing query is vulnerable to SQL injection.\n"
        f"```python\n{PY_BODY}\n```\n"
        "Let me know if you want the postgres version."
    )
    prose = prose_text(raw)
    assert "vulnerable to SQL injection" in prose
    assert "postgres version" in prose
    assert "def get_user" not in prose
    assert "conn.execute" not in prose
