"""Regression tests for SemgrepDetector parse-error handling.

A benign PartialParsing (semgrep skipped one construct but scanned the rest of
the file, including the sink) must NOT be treated as a failed scan: doing so
discarded ~30% of gradable Rust/TypeScript trials over a single unparseable
token. A hard SyntaxError / LexicalError (the file could not be analyzed) still
must be surfaced, so an empty result is not trusted as SECURE for the
semgrep-only languages that have no AST backstop.
"""
from lgtm_bench.detectors.semgrep import _has_target_parse_error

TARGET = "snippet.rs"


def _err(type_tag, message=""):
    # Mirror semgrep's shape: errors[].type is a [tag, spans] list, with a
    # path pointing at the scanned target.
    return {"errors": [{"type": [type_tag, []], "message": message,
                        "path": f"/tmp/{TARGET}", "spans": []}]}


def test_partial_parsing_is_not_a_parse_error():
    # The benign case: real code, one construct semgrep could not parse, rest
    # scanned fine. Must be treated as trustworthy (no parse error surfaced).
    assert _has_target_parse_error(_err("PartialParsing"), TARGET) is False


def test_syntax_error_is_a_parse_error():
    assert _has_target_parse_error(_err("SyntaxError", "Syntax error"), TARGET) is True


def test_lexical_error_is_a_parse_error():
    assert _has_target_parse_error(_err("LexicalError", "Lexical error"), TARGET) is True


def test_syntax_error_by_message_only():
    # Some semgrep versions carry the tag only in the message.
    assert _has_target_parse_error(_err("OtherError", "syntax error near X"), TARGET) is True


def test_no_errors_is_clean():
    assert _has_target_parse_error({"errors": []}, TARGET) is False


def test_partial_parsing_even_with_other_target_ignored():
    # A parse error on a DIFFERENT file must not count against our target.
    data = {"errors": [{"type": ["SyntaxError", []], "message": "syntax error",
                        "path": "/tmp/other.rs", "spans": []}]}
    assert _has_target_parse_error(data, TARGET) is False
