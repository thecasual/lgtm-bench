"""Code extraction from raw model output (TECH_SPEC §7.1)."""
from __future__ import annotations

import re
import textwrap

FENCE_RE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[^\n]*\n(.*?)```", re.DOTALL)

_LANG_ALIASES = {
    "python": {"python", "py", "python3"},
    "sql": {"sql", "sqlite", "postgres", "postgresql", "mysql"},
}


def extract_code(raw: str, language: str = "python") -> str:
    """Pull code from markdown fences; fall back to whole-output heuristic.

    Preference order: fences tagged with the task language, then untagged
    fences, then the whole output. Multiple selected blocks are concatenated
    (models often split helper + usage across blocks).
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
    if not chosen:
        return textwrap.dedent(raw).strip()
    return "\n\n".join(textwrap.dedent(b).strip() for b in chosen).strip()


def prose_text(raw: str) -> str:
    """The non-code portion of the output (for the flag-lexicon detector)."""
    return FENCE_RE.sub(" ", raw)
