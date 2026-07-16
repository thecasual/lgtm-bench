"""Deterministic flag-lexicon detector for edit tasks (TECH_SPEC §7.3).

Scans the *prose* (non-code) portion of a response for mention of the issue
class. Deliberately crude but deterministic; the flag rate is a lower bound.
"""
from __future__ import annotations

import re
import warnings
from functools import lru_cache
from pathlib import Path

import yaml


def _bundled_lexicon_dir() -> Path:
    """The repo's shipped rules/lexicons directory. Resolved from this file's
    location so the bundled command-injection/xss/sql lexicons are found the
    same way for every category, not only when a caller passes lexicon_dir."""
    return Path(__file__).resolve().parent.parent.parent / "rules" / "lexicons"


_DEFAULT_SQL_TERMS = [
    r"sql[ -]?injection",
    r"\binjection\b",
    r"parameteri[sz]",
    r"\bplaceholders?\b",
    r"prepared statements?",
    r"bind(?:ing)?\s+(?:param|variable)",
    r"sanitiz",
    r"(?:unsafe|insecure|vulnerable)\s+(?:sql|quer)",
    r"string\s+(?:concatenation|interpolation|formatting)[^.\n]{0,60}quer",
    r"f-string[^.\n]{0,60}(?:sql|quer)",
]


@lru_cache(maxsize=16)
def _patterns(category: str, lexicon_dir: str | None) -> list[re.Pattern]:
    # When no explicit lexicon_dir is supplied, fall back to the repo's bundled
    # rules/lexicons so command-injection and xss resolve their shipped term
    # lists the same way sql always has. Previously only sql had a built-in
    # default, so a non-sql review/edit task with lexicon_dir=None silently
    # scored a 0% flag rate ("lexicon never ran").
    search_dir = Path(lexicon_dir) if lexicon_dir else _bundled_lexicon_dir()
    terms = None
    bundled_file = search_dir / f"{category}.yaml"
    if bundled_file.exists():
        data = yaml.safe_load(bundled_file.read_text()) or {}
        terms = data.get("terms")
    if terms is None and category == "sql":
        terms = _DEFAULT_SQL_TERMS
    if not terms:
        # A category whose bundled lexicon file exists but yielded no terms
        # (or is missing entirely) would make flags_issue silently return
        # False for every input. Warn loudly so a 0% flag rate can never be
        # mistaken for "no issue mentioned" when it actually means "no lexicon
        # loaded". sql keeps its built-in default above, so it never warns.
        warnings.warn(
            f"flag lexicon for category {category!r} resolved to zero patterns "
            f"(looked in {search_dir}); flags_issue will always return False "
            f"for this category. Add rules/lexicons/{category}.yaml or pass a "
            f"lexicon_dir that contains it.",
            RuntimeWarning,
            stacklevel=2,
        )
    return [re.compile(t, re.IGNORECASE) for t in (terms or [])]


def flags_issue(prose: str, category: str, lexicon_dir: Path | None = None) -> bool:
    pats = _patterns(category, str(lexicon_dir) if lexicon_dir else None)
    return any(p.search(prose) for p in pats)
