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


def test_json_shaped_tool_call_extraction():
    from lgtm_bench.extract import extract_code
    raw = ('I\'ll create it.\n<function_calls>\n'
           '[{"tool_name": "Write", "tool_input": {"path": "h.py", '
           '"content": "def wipe(conn, status):\\n    conn.execute(\\"DELETE FROM t WHERE s = ?\\", (status,))\\n"}}]\n'
           '</function_calls>\nDone.')
    code = extract_code(raw)
    import ast
    ast.parse(code)
    assert "def wipe" in code
    assert "h.py" not in code  # path param excluded


# --- FIX 1: "jsx" is a recognized typescript fence-language alias ------------

def test_jsx_tagged_fences_recognized_as_typescript():
    """React models tag component blocks ```jsx``` rather than ```tsx```/
    ```typescript```. Before adding "jsx" to the typescript alias set, both
    fences here counted as foreign-tagged, so extract_code fell back to
    "grade the single largest foreign fence" and picked the usage snippet
    instead of the real component -- silently dropping a genuine
    dangerouslySetInnerHTML sink from the graded code."""
    raw = (
        "Here's the component:\n\n"
        "```jsx\n"
        "const CommentBody = ({ text }) => {\n"
        "  return <div dangerouslySetInnerHTML={{ __html: text }} />;\n"
        "};\n"
        "```\n\n"
        "Usage:\n\n"
        "```jsx\n"
        'ReactDOM.render(<CommentBody text="hi" />, document.getElementById("root"));\n'
        "```\n"
    )
    out = extract_code(raw, language="typescript")
    assert "dangerouslySetInnerHTML" in out
    assert "CommentBody = ({ text })" in out
    assert "ReactDOM.render" in out  # both jsx-tagged blocks are concatenated


# --- FIX 2: fence-vs-tool-call definition check is language-aware ------------

def test_toolcall_preferred_over_definitionless_fence_for_go():
    """_has_definition used to be ast.parse-only (python), so for go/rust/ts
    the fence-vs-tool-call preference could never fire: a definitionless
    fence (e.g. a bare usage line) always "won" over a tool-call block that
    held the actual function, because neither side ever counted as having a
    definition. Language-aware keyword checks (func/fn/function|=>|class) let
    the real preference apply to go here."""
    raw = (
        "Run this to check status:\n\n"
        "```go\n"
        "fmt.Println(status)\n"
        "```\n\n"
        '<invoke name="Write"><parameter name="content">'
        "func checkStatus(cmd string) error {\n"
        '    return exec.Command("sh", "-c", cmd).Run()\n'
        "}</parameter></invoke>\n"
    )
    out = extract_code(raw, language="go")
    assert "func checkStatus" in out
    assert "fmt.Println" not in out


# --- FIX 3: truncated (never-closed) fence recovery, gated by is_valid -------

def test_truncated_fence_recovered_when_gated_by_is_valid():
    """Output cut off by max-tokens mid-block never emits the closing ```, so
    FENCE_RE (which requires a close) finds nothing and the real code is
    lost entirely. An odd total ``` count signals exactly this; the dangling
    tail is now tried as a candidate block, but ONLY when an is_valid gate is
    supplied and it actually accepts the candidate -- callers that omit
    is_valid keep the old (code-free) behavior exactly."""
    from lgtm_bench.grading import _is_valid_typescript

    raw = (
        "Here's the function:\n\n"
        "```typescript\n"
        "function riskyExec(cmd: string) {\n"
        "    return cp.execSync(cmd);\n"
        "}\n"
        "\n// still writing more"
    )
    assert raw.count("```") == 1  # a single, never-closed opening fence

    gated = extract_code(raw, language="typescript", is_valid=_is_valid_typescript)
    assert "function riskyExec" in gated
    assert "cp.execSync(cmd)" in gated
    assert _is_valid_typescript(gated)

    # Without a validity gate, the fix must not fire: prior (code-free)
    # behavior is preserved exactly.
    ungated = extract_code(raw, language="typescript")
    assert "Here's the function" in ungated  # prose leaked in, as before


def test_truncated_fence_not_recovered_when_candidate_fails_validity():
    """The odd-``` heuristic only detects a dangling fence, not that its tail
    is well-formed code -- e.g. truncation right after the opening fence line
    with no code at all yet, or a truncated tail that is still just prose.
    Gating by is_valid must reject these rather than accept junk."""
    from lgtm_bench.grading import _is_valid_typescript

    raw = (
        "I'll get started on this now:\n\n"
        "```typescript\n"
        "I was cut off before writing any actual code"
    )
    assert raw.count("```") == 1
    out = extract_code(raw, language="typescript", is_valid=_is_valid_typescript)
    # No function/=>/class keyword anywhere -- is_valid_typescript rejects the
    # dangling tail, so the fix must not have substituted it in.
    assert not _is_valid_typescript(out)


# --- FIX 4: per-block retry when whole-concatenation validity fails ----------

def test_sql_falls_back_to_largest_individually_valid_block():
    """extract_code normally concatenates every matching-language fence with
    "\\n\\n". If a second block is a bare fragment (e.g. a model splits a
    query across two fences, and the second is an incomplete continuation),
    the concatenation can break sqlglot even though the first block alone is
    a perfectly gradable query. Retry each block individually (largest
    first), gated by is_valid, rather than discarding the whole trial."""
    from lgtm_bench.grading import _is_valid_raw_sql

    block1 = "SELECT id, name, price\nFROM products\nWHERE category = ?"
    block2 = "ORDER BY"
    raw = f"```sql\n{block1}\n```\n\n```sql\n{block2}\n```\n"

    # Confirms the premise: concatenating both blocks (the old behavior)
    # fails validity, so the fix has something real to recover from.
    concatenated = block1 + "\n\n" + block2
    assert not _is_valid_raw_sql(concatenated)

    out = extract_code(raw, language="sql", is_valid=_is_valid_raw_sql)
    assert out == block1
    assert _is_valid_raw_sql(out)

    # Falls back to current (concatenation) behavior when no is_valid gate is
    # supplied -- unchanged for every existing caller that doesn't pass one.
    assert extract_code(raw, language="sql") == concatenated


def test_go_multiblock_union_not_narrowed_by_per_block_retry():
    """go/rust/typescript are deliberately graded as a whole-file union over
    every block (det-4 in grading.py): a later block can define a sink that
    only exists because of an earlier block's alias/helper. The per-block
    retry from FIX 4 must never kick in for these languages even when the
    concatenation fails validity, so a failing union stays a union rather
    than being silently narrowed down to a single "valid" block."""
    # Braces deliberately unbalanced across the pair (concatenation invalid),
    # so this is only reachable through the is_valid-failure path FIX 4 uses.
    block1 = "func helper(x int) int {\n    return x + 1\n"  # unclosed
    block2 = "func main() {\n    helper(1)\n}"
    raw = f"```go\n{block1}\n```\n\n```go\n{block2}\n```\n"

    from lgtm_bench.grading import _is_valid_go

    # The current (no is_valid) concatenation behavior is the reference: go's
    # per-block retry must never diverge from it, even under an is_valid gate
    # that fails on the concatenation.
    concatenated = extract_code(raw, language="go")
    assert not _is_valid_go(concatenated)  # unbalanced braces overall

    out = extract_code(raw, language="go", is_valid=_is_valid_go)
    # Unchanged from plain concatenation -- go is excluded from the
    # per-block-retry narrowing regardless of the is_valid gate outcome.
    assert out == concatenated


def test_redraft_same_symbol_keeps_last_definition():
    """Iterative redraft: a naive draft, then a safe final version, each a full
    redefinition of the SAME symbol. Extraction keeps only the last (delivered)
    definition instead of concatenating the abandoned unsafe draft (which would
    make the detector grade code the model superseded)."""
    raw = (
        "```tsx\n"
        "const CommentBody = ({ text }) => (\n"
        "  <div dangerouslySetInnerHTML={{ __html: text }} />\n"
        ");\nexport default CommentBody;\n"
        "```\n\n"
        "```tsx\n"
        "import DOMPurify from 'dompurify';\n"
        "const CommentBody = ({ text }) => (\n"
        "  <div>{DOMPurify.sanitize(text)}</div>\n"
        ");\nexport default CommentBody;\n"
        "```\n"
    )
    out = extract_code(raw, language="typescript")
    # The superseded unsafe draft is dropped; only the DOMPurify version remains.
    assert "DOMPurify.sanitize" in out
    assert "dangerouslySetInnerHTML" not in out


def test_redraft_does_not_collapse_distinct_symbols():
    """Helper + usage (or any two blocks defining DIFFERENT symbols) is a
    legitimate multi-block answer and must still be concatenated, never
    collapsed as if it were a redraft."""
    raw = (
        "```python\n"
        "def helper(x):\n    return x + 1\n"
        "```\n\n"
        "```python\n"
        "def main():\n    return helper(2)\n"
        "```\n"
    )
    out = extract_code(raw, language="python")
    assert "def helper" in out and "def main" in out
