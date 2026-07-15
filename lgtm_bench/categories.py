"""Single source of truth for category metadata (label + CWE anchor + status).

Both report.py and export.py read the CWE/label for a category from here so the
mapping lives in exactly one place. `cwe` is a list because a future category
may span several CWE ids (reflected/stored/DOM XSS all sit under CWE-79).
"""
from __future__ import annotations

# category id -> {label, cwe (list), status}
CATEGORY_META: dict[str, dict] = {
    "sql":               {"label": "SQL injection",        "cwe": ["CWE-89"], "status": "active"},
    "command-injection": {"label": "OS command injection", "cwe": ["CWE-78"], "status": "active"},
    "xss":               {"label": "Cross-site scripting", "cwe": ["CWE-79"], "status": "active"},
}


def meta_for(category: str) -> dict:
    """The CATEGORY_META entry for `category`, or a permissive fallback so an
    unregistered category still renders (label = the id itself, no CWE)."""
    return CATEGORY_META.get(
        category, {"label": category, "cwe": [], "status": "active"})


def cwe_for(category: str) -> list[str]:
    return meta_for(category)["cwe"]


def label_for(category: str) -> str:
    return meta_for(category)["label"]
