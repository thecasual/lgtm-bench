"""Code extraction from raw model output (extract.py)."""
from __future__ import annotations

import ast

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


# --- BUG A: agentic tool-call XML parameter blocks ---------------------------

def test_toolcall_xml_content_parameter_extracted():
    raw = (
        "I'll create a minimal helper:\n\n"
        '<function_calls>\n<invoke name="write_file">\n'
        '<parameter name="path">/tmp/x/list_products.py</parameter>\n'
        f'<parameter name="content">{PY_BODY}</parameter>\n'
        "</invoke>\n</function_calls>\n\nDone."
    )
    out = extract_code(raw, language="python")
    assert out == PY_BODY
    ast.parse(out)


def test_toolcall_xml_file_contents_alias_and_ignores_path_command():
    body = "import sqlite3\n\ndef f(c):\n    return c.execute('SELECT 1')"
    raw = (
        '<invoke name="Write">\n'
        '<parameter name="command">create</parameter>\n'
        '<parameter name="path">/tmp/x/users.py</parameter>\n'
        f'<parameter name="file_contents">{body}</parameter>\n'
        "</invoke>\n"
    )
    out = extract_code(raw, language="python")
    assert out == body
    assert "/tmp/x/users.py" not in out
    assert "create" not in out
    ast.parse(out)


def test_toolcall_xml_multiple_content_blocks_concatenated():
    raw = (
        '<invoke name="write"><parameter name="contents">'
        "def helper(x):\n    return x</parameter></invoke>\n"
        '<invoke name="write"><parameter name="code">'
        "print(helper(1))</parameter></invoke>\n"
    )
    out = extract_code(raw, language="python")
    assert out == "def helper(x):\n    return x\n\nprint(helper(1))"
    ast.parse(out)


def test_markdown_fence_wins_over_toolcall_xml():
    raw = (
        f"```python\n{PY_BODY}\n```\n"
        '<invoke name="write"><parameter name="content">'
        "not_the_code = 1</parameter></invoke>"
    )
    assert extract_code(raw, language="python") == PY_BODY


# --- BUG B: fenceless code embedded in prose ---------------------------------

def test_fenceless_prose_span_import_start_trims_trailing_prose():
    raw = (
        "Write helpers.py\n\n\n"
        "      import sqlite3\n\n"
        'ALLOWED = {"id", "name"}\n\n\n'
        "def list_products(conn, sort_by='id'):\n"
        "    if sort_by not in ALLOWED:\n"
        "        raise ValueError(sort_by)\n"
        "    return conn.execute(f'SELECT * FROM p ORDER BY {sort_by}').fetchall()\n\n"
        "Wrote `helpers.py` with `list_products()`. Adjust ALLOWED to taste."
    )
    out = extract_code(raw, language="python")
    ast.parse(out)
    assert out.startswith("import sqlite3")
    assert "ALLOWED" in out and "def list_products" in out
    assert "Write helpers.py" not in out
    assert "Wrote `helpers.py`" not in out


def test_fenceless_prose_span_allcaps_assignment_start():
    raw = (
        "Here is the module.\n\n"
        'TABLE = "products"\n'
        "def q(conn):\n    return conn.execute('SELECT 1')\n\n"
        "That should do it."
    )
    out = extract_code(raw, language="python")
    ast.parse(out)
    assert out.startswith('TABLE = "products"')
    assert "That should do it" not in out


def test_fenceless_no_code_span_falls_back_to_whole_output():
    raw = "This directory is empty so there is nothing to review here."
    assert extract_code(raw, language="python") == raw


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
