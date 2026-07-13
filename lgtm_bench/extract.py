"""Code extraction from raw model output (TECH_SPEC §7.1)."""
from __future__ import annotations

import ast
import re
import textwrap

FENCE_RE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[^\n]*\n(.*?)```", re.DOTALL)

# Agentic tool-call XML: code emitted inside a simulated file-write tool call,
# e.g. <invoke name="Write"><parameter name="content">CODE</parameter></invoke>.
# Only content-bearing parameters are pulled (never path/command/tool_name/args).
PARAM_RE = re.compile(
    r'<parameter\s+name="(?:content|file_contents|contents|file_text|code)"\s*>'
    r"(.*?)</parameter>",
    re.DOTALL,
)

# Lines that plausibly begin a top-level block of Python source.
_CODE_START_RE = re.compile(
    r"^(?:import\s|from\s|def\s|class\s|async\s+def\s)"
    r"|^[A-Z][A-Z0-9_]*\s*=(?!=)"
)

_LANG_ALIASES = {
    "python": {"python", "py", "python3"},
    "sql": {"sql", "sqlite", "postgres", "postgresql", "mysql"},
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


def _largest_parseable_span(raw: str) -> str | None:
    """Largest contiguous code span starting at a top-level code line.

    Last-resort heuristic for fenceless, markup-free completions that drop
    source directly into prose. Anchors on an import/from/def/class or an
    ALLCAPS assignment, trims trailing prose lines until the span parses.
    """
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


def extract_code(raw: str, language: str = "python") -> str:
    """Pull code from markdown fences; fall back to lighter-weight heuristics.

    Preference order: fences tagged with the task language, then untagged
    fences, then agentic tool-call XML parameter blocks, then the largest
    parseable span embedded in prose, then the whole output. Multiple
    selected blocks are concatenated (models often split helper + usage).
    """
    blocks = FENCE_RE.findall(raw)
    want = _LANG_ALIASES.get(language, {language})
    tagged = [body for tag, body in blocks if tag.lower() in want]
    untagged = [body for tag, body in blocks if not tag]
    chosen = tagged or untagged
    if not chosen and blocks:
        # Only foreign-tagged fences (e.g. ```bash usage note) — grade the
        # largest fence anyway rather than declaring the trial code-free.
        chosen = [max((body for _, body in blocks), key=len)]
    if chosen:
        return "\n\n".join(textwrap.dedent(b).strip() for b in chosen).strip()

    # No usable markdown fences. Try agentic tool-call XML parameter blocks.
    params = PARAM_RE.findall(raw)
    if params:
        return "\n\n".join(textwrap.dedent(p).strip() for p in params).strip()

    # Last resort: the largest parseable span buried in running prose.
    span = _largest_parseable_span(raw)
    if span is not None:
        return span

    return textwrap.dedent(raw).strip()


def prose_text(raw: str) -> str:
    """The non-code portion of the output (for the flag-lexicon detector)."""
    return FENCE_RE.sub(" ", raw)
