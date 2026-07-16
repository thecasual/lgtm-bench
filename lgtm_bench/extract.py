"""Code extraction from raw model output (TECH_SPEC §7.1)."""
from __future__ import annotations

import ast
import json
import re
import textwrap

FENCE_RE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[^\n]*\n(.*?)```", re.DOTALL)

# Reasoning "think" blocks. qwen3-family models can emit <think>...</think>
# even when asked with think:false, and a fenced draft inside the think block
# would corrupt extraction (the real deliverable comes after the block). We
# strip these BEFORE any fence scanning or fallback. Terminated blocks go
# first; then any dangling, unterminated <think> (no closing tag, e.g. the
# output was truncated by max-tokens) is stripped through end-of-string.
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
UNTERMINATED_THINK_RE = re.compile(r"<think>.*\Z", re.DOTALL | re.IGNORECASE)


def _strip_think(raw: str) -> str:
    """Remove model reasoning <think> blocks from raw output.

    Terminated <think>...</think> pairs are removed first; whatever <think>
    remains afterward has no closing tag (a truncated block), so it is stripped
    from the dangling opener to the end of the string.
    """
    raw = THINK_RE.sub("", raw)
    raw = UNTERMINATED_THINK_RE.sub("", raw)
    return raw

# JSON-shaped simulated tool call: {"tool_name": "Write", "tool_input":
# {"content": "CODE"}} inside a <function_calls> block. Pull the content-bearing
# JSON string values (properly unescaped), never path/pattern/command.
JSON_PARAM_RE = re.compile(
    r'"(?:content|file_text|file_contents|code|new_str|text)"\s*:\s*("(?:[^"\\]|\\.)*")',
    re.DOTALL,
)

# Agentic tool-call XML: code emitted inside a simulated file-write tool call,
# e.g. <invoke name="Write"><parameter name="content">CODE</parameter></invoke>.
# Only content-bearing parameters are pulled (never path/command/tool_name/args).
PARAM_RE = re.compile(
    r'<parameter\s+name="(?:content|file_contents|contents|file_text|code)"\s*>'
    r"(.*?)</parameter>",
    re.DOTALL,
)

# Malformed / bare tool-call file-write scaffolding some models emit instead of
# the canonical <parameter name="content"> shape: a bare <content>CODE</content>
# body (seen with <write_file><path>...</path><content>...</content></write_file>
# and with <invoke name="write"><path>...</parameter><content>...</content>),
# where the surrounding tags are simulated, not real. The <content> body is the
# code; pulling it here strips the leaked <write_file>/<path>/<invoke> wrappers
# and any lead-in prose that would otherwise be graded as source (det-5).
CONTENT_TAG_RE = re.compile(r"<content>\n?(.*?)</content>", re.DOTALL)

# Lines that plausibly begin a top-level block of Python source.
_CODE_START_RE = re.compile(
    r"^(?:import\s|from\s|def\s|class\s|async\s+def\s)"
    r"|^[A-Z][A-Z0-9_]*\s*=(?!=)"
)

_LANG_ALIASES = {
    "python": {"python", "py", "python3"},
    "sql": {"sql", "sqlite", "postgres", "postgresql", "mysql"},
    "go": {"go", "golang"},
    "rust": {"rust", "rs"},
    "typescript": {"typescript", "ts", "tsx", "javascript", "js", "node"},
}


def _try_parse_block(block: list[str]) -> str | None:
    """Return a normalized, ast-parseable rendering of `block`, or None."""
    text = "\n".join(block).rstrip()
    variants = [text, textwrap.dedent(text)]
    if block:
        # The lead-in line may carry stray indentation the rest lacks; a
        # top-level statement belongs at column 0, so lstrip just that line.
        lead = "\n".join([block[0].lstrip()] + block[1:]).rstrip()
        variants += [lead, textwrap.dedent(lead)]
    for v in variants:
        if not v.strip():
            continue
        try:
            ast.parse(v)
        except SyntaxError:
            continue
        return v
    return None


def _largest_parseable_span(raw: str, language: str = "python") -> str | None:
    """Largest contiguous code span starting at a top-level code line.

    Last-resort heuristic for fenceless, markup-free completions that drop
    source directly into prose. Anchors on an import/from/def/class or an
    ALLCAPS assignment, trims trailing prose lines until the span parses.

    This heuristic relies on `ast.parse`, so it is python-only; for other
    languages there is no parser to trim against, so we skip it and let the
    caller fall through to the whole-output fallback.
    """
    if language != "python":
        return None
    lines = raw.splitlines()
    starts = [i for i, ln in enumerate(lines) if _CODE_START_RE.match(ln.strip())]
    best: str | None = None
    for s in starts:
        for e in range(len(lines), s, -1):
            parsed = _try_parse_block(lines[s:e])
            if parsed is not None:
                if best is None or len(parsed) > len(best):
                    best = parsed
                break  # largest end for this start; move to next start
    return best


def _has_definition(code: str) -> bool:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    return any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
               for n in ast.walk(tree))


def _tool_call_code(raw: str) -> str | None:
    """Concatenated code from simulated tool calls — XML <parameter> blocks or
    JSON-shaped {"content": "..."} tool_input — or None if there are none."""
    parts = list(PARAM_RE.findall(raw))
    parts += CONTENT_TAG_RE.findall(raw)
    for quoted in JSON_PARAM_RE.findall(raw):
        try:
            val = json.loads(quoted)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(val, str) and val.strip():
            parts.append(val)
    parts = [textwrap.dedent(p).strip() for p in parts if p.strip()]
    return "\n\n".join(parts).strip() if parts else None


def extract_code(raw: str, language: str = "python") -> str:
    """Pull code from markdown fences; fall back to lighter-weight heuristics.

    Preference order: fences tagged with the task language, then untagged
    fences, then agentic tool-call XML parameter blocks, then the largest
    parseable span embedded in prose, then the whole output. Multiple
    selected blocks are concatenated (models often split helper + usage).
    """
    # A reasoning model may wrap a draft (including fenced code) in a <think>
    # block; strip it before scanning so only the real answer is graded.
    raw = _strip_think(raw)
    blocks = FENCE_RE.findall(raw)
    want = _LANG_ALIASES.get(language, {language})
    tagged = [body for tag, body in blocks if tag.lower() in want]
    untagged = [body for tag, body in blocks if not tag]
    chosen = tagged or untagged
    if not chosen and blocks:
        # Only foreign-tagged fences (e.g. ```bash usage note) — grade the
        # largest fence anyway rather than declaring the trial code-free.
        chosen = [max((body for _, body in blocks), key=len)]

    # Tool-call code (XML or JSON-shaped simulated file write) is the model's
    # actual deliverable; a markdown fence in the same answer is often just a
    # usage example. If the chosen fence carries no definition but a tool-call
    # block does, prefer the tool-call code.
    tool_code = _tool_call_code(raw)

    if chosen:
        fence_code = "\n\n".join(textwrap.dedent(b).strip() for b in chosen).strip()
        if tool_code and not _has_definition(fence_code) and _has_definition(tool_code):
            return tool_code
        return fence_code

    if tool_code:
        return tool_code

    # Last resort: the largest parseable span buried in running prose.
    span = _largest_parseable_span(raw, language)
    if span is not None:
        return span

    return textwrap.dedent(raw).strip()


def prose_text(raw: str) -> str:
    """The non-code portion of the output (for the flag-lexicon detector)."""
    # Drop reasoning first so the edit-mode lexicon detector is not fed think
    # prose (draft musings about "vulnerable"/"safe" would skew the verdict).
    return FENCE_RE.sub(" ", _strip_think(raw))
