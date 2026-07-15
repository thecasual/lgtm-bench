"""<think> block handling in extract.py.

qwen3-family models can emit <think>...</think> reasoning even with think:false.
A fenced draft inside the think block would otherwise be extracted and graded
instead of the real answer. extract_code and prose_text must strip think blocks
(terminated AND unterminated) before any fence scanning.
"""
from __future__ import annotations

import ast

from lgtm_bench.extract import extract_code, prose_text

REAL = 'def get_user(conn, email):\n    return conn.execute("SELECT 1")'
DECOY = 'def get_user(conn, email):\n    return conn.execute("SELECT * FROM u WHERE e=" + email)'


def test_terminated_think_with_decoy_fence_is_ignored():
    """A fenced draft inside <think> must not win over the real answer that
    follows the closing tag."""
    raw = (
        "<think>\n"
        "Let me draft something first.\n"
        f"```python\n{DECOY}\n```\n"
        "Actually that concatenates, let me parametrize instead.\n"
        "</think>\n"
        "Here is the safe version:\n"
        f"```python\n{REAL}\n```\n"
    )
    out = extract_code(raw, language="python")
    assert out == REAL
    assert "email" not in out or '"SELECT 1"' in out
    assert "+ email" not in out
    ast.parse(out)


def test_unterminated_think_truncated_by_max_tokens_yields_no_code():
    """An unterminated <think> (no closing tag, truncated output) is stripped
    through end-of-string, so a decoy fence inside it is not extracted."""
    raw = (
        "<think>\n"
        "I should write the query. Here is a first cut:\n"
        f"```python\n{DECOY}\n```\n"
        "but wait, I need to"  # cut off mid-sentence, no </think>
    )
    out = extract_code(raw, language="python")
    # Everything from the dangling <think> onward is gone; nothing real remains.
    assert "def get_user" not in out
    assert "+ email" not in out


def test_unterminated_think_then_real_answer_after_partial():
    """If the think block is unterminated it swallows the rest, so the only way
    a real answer survives is when it precedes an (impossible) reopen; verify
    the common case: text BEFORE an unterminated think is preserved."""
    raw = (
        "Here is the code:\n"
        f"```python\n{REAL}\n```\n"
        "<think>now let me double check by drafting again\n"
        f"```python\n{DECOY}\n```"
    )
    out = extract_code(raw, language="python")
    assert out == REAL
    assert "+ email" not in out
    ast.parse(out)


def test_output_with_no_think_block_unchanged():
    raw = f"Here you go:\n```python\n{REAL}\n```\nEnjoy!"
    assert extract_code(raw, language="python") == REAL


def test_think_only_output_yields_no_code():
    """Output that is entirely a think block (terminated) leaves no answer."""
    raw = (
        "<think>\n"
        "The user wants a query. I could write it several ways.\n"
        f"```python\n{DECOY}\n```\n"
        "</think>"
    )
    out = extract_code(raw, language="python")
    assert "def get_user" not in out
    assert "+ email" not in out


def test_think_tag_case_insensitive():
    raw = (
        "<THINK>drafting\n"
        f"```python\n{DECOY}\n```\n"
        "</THINK>\n"
        f"```python\n{REAL}\n```"
    )
    assert extract_code(raw, language="python") == REAL


def test_prose_text_strips_think_prose():
    """The edit-mode lexicon detector must not be fed think prose."""
    raw = (
        "<think>This looks vulnerable to SQL injection, I must be careful.</think>\n"
        "The updated function parametrizes the query.\n"
        f"```python\n{REAL}\n```\n"
    )
    prose = prose_text(raw)
    assert "vulnerable to SQL injection" not in prose
    assert "parametrizes the query" in prose


def test_prose_text_strips_unterminated_think():
    raw = (
        "The fix is applied.\n"
        "<think>but is it really vulnerable? let me reconsider whether"
    )
    prose = prose_text(raw)
    assert "The fix is applied." in prose
    assert "vulnerable" not in prose
