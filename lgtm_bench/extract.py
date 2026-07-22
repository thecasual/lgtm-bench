"""Code extraction from raw model output (TECH_SPEC §7.1)."""
from __future__ import annotations

import ast
import json
import re
import textwrap

FENCE_RE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[^\n]*\n(.*?)```", re.DOTALL)

# Truncated fence: output cut off (max-tokens) before the closing ``` was
# emitted. Mirrors FENCE_RE's opening-line shape but matches to end-of-string
# instead of requiring a close. Only ever applied to the tail starting at the
# last opening ``` in raw, and only when the overall ``` count is odd (see
# _unterminated_fence_block below), so it never fires on ordinary,
# well-formed output.
UNTERMINATED_FENCE_RE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[^\n]*\n(.*)\Z", re.DOTALL)

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
    # "jsx" is the tag React-flavored models (and JSX-emitting TS models)
    # reach for; without it here, a component fenced as ```jsx``` is treated
    # as untagged/foreign and can lose out to an unrelated fence entirely.
    "typescript": {"typescript", "ts", "tsx", "javascript", "js", "jsx", "node"},
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


def _has_definition(code: str, language: str = "python") -> bool:
    """True if `code` looks like it contains an actual definition, not just a
    fragment/usage-example. Language-aware: ast.parse only understands
    python, so go/rust/typescript reuse the same lightweight keyword
    heuristics grading.py's per-language validity checks already rely on
    (func / fn / function|=>|class), letting the fence-vs-tool-call
    preference below fire for those languages too instead of silently never
    matching."""
    if language == "go":
        return "func " in code
    if language == "rust":
        return "fn " in code
    if language == "typescript":
        return "function " in code or "=>" in code or "class " in code
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    return any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
               for n in ast.walk(tree))


def _unterminated_fence_block(raw: str) -> tuple[str, str] | None:
    """The dangling (tag, body) candidate for a fence whose closing ``` was
    lost to truncation, or None if there is nothing usable.

    Mirrors the UNTERMINATED_THINK_RE approach: called only when raw's total
    ``` count is odd, i.e. there is exactly one dangling opening fence with no
    matching close. Takes everything from that last opening fence to the end
    of the string as a best-effort block. Callers MUST still validity-gate
    whatever they build from this before using it -- an odd delimiter count
    only says a fence never closed, not that the tail is well-formed code.
    """
    idx = raw.rfind("```")
    if idx == -1:
        return None
    m = UNTERMINATED_FENCE_RE.match(raw, idx)
    if not m:
        return None
    tag, body = m.group(1), m.group(2)
    if not body.strip():
        return None
    return tag, body


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


_DEF_NAME_RE = re.compile(
    r"(?:export\s+default\s+(?P<d>\w+)"
    r"|(?:export\s+)?(?:const|let|var|function|class)\s+(?P<j>\w+)"
    r"|def\s+(?P<py>\w+)"
    r"|func\s+(?P<go>\w+)"
    r"|fn\s+(?P<rs>\w+))"
)


def _defined_names(body: str) -> set[str]:
    """Top-level definition names a block introduces (const/function/class/def/
    func/fn/export default, plus module-level assignments like
    `ALLOWED = {...}`). Used to detect redrafts: a name in two blocks means the
    later block redefines it. Completeness matters here in the safe direction: a
    name we MISS could make a block that still carries a needed definition (a
    module constant an allowlist depends on) look fully superseded and get
    dropped, so we err toward listing more names, which only makes the collapse
    more conservative (keep the block, fall back to concatenation)."""
    names: set[str] = set()
    for m in _DEF_NAME_RE.finditer(body):
        names.add(next(g for g in m.groups() if g))
    # Module-level (unindented, column 0) assignments: `ALLOWED = {...}`,
    # `_SORTABLE_COLUMNS = frozenset(...)`, etc. Restricted to line start so an
    # indented in-function `x = ...` is not treated as a top-level definition
    # (which would wrongly keep a genuine redraft block from collapsing).
    for line in body.splitlines():
        m = re.match(r"([A-Za-z_]\w*)\s*=(?!=)", line)
        if m:
            names.add(m.group(1))
    return names


def _collapse_redrafts(bodies: list[str]) -> list[str]:
    """Drop superseded redraft blocks. Models often answer a single-artifact
    task by showing a naive draft, then a revised one, then a final one, each a
    full redefinition of the SAME symbol (`const CommentBody` three times, which
    is not even valid JS). Concatenating them makes the detector grade the
    abandoned unsafe draft. A developer would keep the last definition, so do the
    same: if a block defines names and every one of them is redefined by a LATER
    block, it is fully superseded, so drop it. Legitimate helper+usage splits
    define DIFFERENT symbols (or the usage block defines none), so they are never
    collapsed."""
    if len(bodies) < 2:
        return bodies
    defs = [_defined_names(b) for b in bodies]
    kept = []
    for i, body in enumerate(bodies):
        later_names: set[str] = set()
        for j in range(i + 1, len(bodies)):
            later_names |= defs[j]
        if defs[i] and defs[i] <= later_names:
            continue  # every name this block defines is redefined later
        kept.append(body)
    return kept or [bodies[-1]]


def extract_code(raw: str, language: str = "python", is_valid=None) -> str:
    """Pull code from markdown fences; fall back to lighter-weight heuristics.

    Preference order: fences tagged with the task language, then untagged
    fences, then agentic tool-call XML parameter blocks, then the largest
    parseable span embedded in prose, then the whole output. Multiple
    selected blocks are concatenated (models often split helper + usage).

    `is_valid`, if given, is an `(code: str) -> bool` callable -- typically
    grading._is_valid bound to the calling trial's task -- that gates two
    additional, more speculative recovery attempts tried only when the normal
    selection above fails validity: retrying each matching-language block
    individually (see _select_and_assemble/is_valid below) and recovering a
    truncated, never-closed trailing fence (see _unterminated_fence_block).
    Neither attempt ever fires without an is_valid to gate it, so callers that
    omit it get exactly the prior (fence-concatenation-only) behavior.
    """
    # A reasoning model may wrap a draft (including fenced code) in a <think>
    # block; strip it before scanning so only the real answer is graded.
    raw = _strip_think(raw)
    blocks = FENCE_RE.findall(raw)
    want = _LANG_ALIASES.get(language, {language})

    # Tool-call code (XML or JSON-shaped simulated file write) is the model's
    # actual deliverable; a markdown fence in the same answer is often just a
    # usage example. If the chosen fence carries no definition but a tool-call
    # block does, prefer the tool-call code.
    tool_code = _tool_call_code(raw)

    def _select_and_assemble(blocks: list[tuple[str, str]]):
        """(joined_code, chosen_block_bodies) for `blocks`, or (None, []) if
        none of them are usable. Mirrors the original fence-selection logic:
        language-tagged first, then untagged, then (last resort) the single
        largest foreign-tagged fence."""
        tagged = [body for tag, body in blocks if tag.lower() in want]
        untagged = [body for tag, body in blocks if not tag]
        chosen = tagged or untagged
        if not chosen and blocks:
            chosen = [max((body for _, body in blocks), key=len)]
        if not chosen:
            return None, []
        # Collapse iterative redrafts (same symbol redefined across blocks) to
        # the model's final version before joining, so an abandoned unsafe draft
        # is not graded alongside the delivered safe one.
        chosen = _collapse_redrafts(chosen)
        fence_code = "\n\n".join(textwrap.dedent(b).strip() for b in chosen).strip()
        if tool_code and not _has_definition(fence_code, language) \
                and _has_definition(tool_code, language):
            fence_code = tool_code
        return fence_code, chosen

    fence_code, chosen = _select_and_assemble(blocks)

    if fence_code is not None:
        if is_valid is None or is_valid(fence_code):
            return fence_code

        # FIX: the concatenation of matching-language blocks fails validity
        # (e.g. a second block is a fragment that breaks the parser), but an
        # individual block might independently be the real, gradable answer.
        # Skip this for go/rust/typescript: those languages are deliberately
        # graded as a whole-file union over every block (det-4 in grading.py)
        # so a failing union must stay a union, not get quietly narrowed down
        # to one block.
        if language not in ("go", "rust", "typescript") and len(chosen) > 1:
            for body in sorted(chosen, key=len, reverse=True):
                candidate = textwrap.dedent(body).strip()
                if candidate and is_valid(candidate):
                    return candidate

    # FIX: output truncated mid-block (max-tokens) loses the closing ``` along
    # with the rest of the code, so FENCE_RE (which requires a close) finds
    # nothing for that block. An odd total ``` count means exactly one opening
    # fence never closed; retry selection with that dangling tail included as
    # an extra candidate block, gated by is_valid so a truncated non-code tail
    # (e.g. prose cut off after a stray ``` mention) is never accepted.
    if is_valid is not None and raw.count("```") % 2 == 1:
        tail = _unterminated_fence_block(raw)
        if tail is not None:
            tail_code, _ = _select_and_assemble(blocks + [tail])
            if tail_code is not None and is_valid(tail_code):
                return tail_code

    if fence_code is not None:
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
