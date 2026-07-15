"""Report-copy invariants: the markdown and HTML generators are pure functions
of the JSONL records, so every data-derived claim must track the records and
never a hardcoded assumption. These are fast unit tests over small synthetic
record lists (no model calls, no files), mirroring the shape of a real record
in results-published/ (see `rec` below for the fields the generators read).

They lock in the fixes for the imminent data drop (2 more open-weight models,
K=8 cells alongside the existing K=2 cells):
  (a) mixed-language data never claims "one language"; single-language data
      never mentions taint packs.
  (b) the invalid-rate bullet's numerator and denominator share one scope.
  (c) two pack versions within a language trips a loud banner in both outputs.
  (d) model ordering is natural (qwen3:8b before qwen3:14b), not lexicographic.
  (e) no en/em dashes leak into either output.
"""
from __future__ import annotations

import re

from lgtm_bench import metrics as M
from lgtm_bench.report import build_report
from lgtm_bench.html_report import build_html_report

EN_DASH = "–"
EM_DASH = "—"


def rec(model="claude-opus-4-8", task_id="sql/user-lookup", mode="generate",
        language="python", condition="none", variant_id="v1-plain",
        verdict="secure", run_id="run-test", detector_pack_version="sql@0.9.0",
        fixture_version="1", trial_index=0, **extra) -> dict:
    """A single synthetic trial record with every field the two generators
    read. Defaults describe a safe Python generate trial; override per test.
    The task_id prefix (sql/, sql-go/, sql-rust/) also drives language when the
    explicit `language` is dropped, matching M.record_language."""
    d = {
        "trial_key": f"{model}|{task_id}|{condition}|{variant_id}|{trial_index}",
        "run_id": run_id, "model": model, "task_id": task_id, "mode": mode,
        "language": language, "condition": condition, "variant_id": variant_id,
        "trial_index": trial_index, "verdict": verdict,
        "fixed_existing": None, "flagged_existing": None, "findings": [],
        "error": None, "detector_pack_version": detector_pack_version,
        "fixture_version": fixture_version,
    }
    d.update(extra)
    return d


def _python_only(n_models=2) -> list[dict]:
    """A minimal well-formed Python-only dataset with a couple of models and
    two trials per cell, enough for the generators to render a full body."""
    out = []
    models = ["claude-opus-4-8", "claude-haiku-4-5"][:n_models]
    for m in models:
        for i in range(2):
            out.append(rec(model=m, task_id="sql/user-lookup", trial_index=i,
                           verdict="vulnerable" if (m.endswith("haiku-4-5")
                                                    and i == 0) else "secure"))
    return out


def _mixed_language() -> list[dict]:
    """Python + Go + Rust, so the cross-language section renders and the
    'one language' claim must not appear anywhere."""
    out = _python_only()
    for lang, prefix, pack in [("go", "sql-go", "sql-go@0.3.0"),
                               ("rust", "sql-rust", "sql-rust@0.3.0")]:
        for m in ["claude-opus-4-8", "claude-haiku-4-5"]:
            for i in range(2):
                out.append(rec(model=m, task_id=f"{prefix}/user-lookup",
                               language=lang, detector_pack_version=pack,
                               trial_index=i,
                               verdict="vulnerable" if (m.endswith("haiku-4-5")
                                                        and i == 0) else "secure"))
    return out


# -- (a) language-scoped copy -------------------------------------------------

def test_mixed_language_never_claims_one_language():
    recs = _mixed_language()
    md = build_report(recs, [])
    h = build_html_report(recs, [])
    # The cross-language section is rendered, so a "one language" limitation
    # would flatly contradict it. Neither generator may print that phrase.
    assert "one language" not in md.lower()
    assert "one language" not in h.lower()
    # And the multi-language copy should actually name the other languages as
    # covered by audited taint packs.
    assert "taint pack" in md.lower()
    assert "taint pack" in h.lower()


def test_single_language_never_mentions_taint_packs():
    recs = _python_only()
    md = build_report(recs, [])
    h = build_html_report(recs, [])
    # No Go/Rust data => no cross-language section => no taint-pack prose.
    assert "taint" not in md.lower()
    assert "taint" not in h.lower()
    # Single-language keeps the plain "one language" limitation.
    assert "one language" in md.lower()


# -- (b) invalid-rate scope agreement -----------------------------------------

def test_invalid_rate_bullet_scope_agrees():
    # 4 Python trials, exactly 1 invalid -> the true Python invalid rate is 25%.
    # 4 Go trials, ALL invalid -> if the bullet divided an all-language
    # numerator by a Python-only denominator (the rep-2 bug) it would print a
    # 125% rate. It must report the Python-only 1-of-4 = 25% instead.
    recs = []
    py_verdicts = ["invalid", "secure", "secure", "vulnerable"]
    for i, v in enumerate(py_verdicts):
        recs.append(rec(task_id="sql/user-lookup", variant_id=f"v{i}",
                        verdict=v, trial_index=i))
    for i in range(4):
        recs.append(rec(task_id="sql-go/user-lookup", language="go",
                        detector_pack_version="sql-go@0.3.0",
                        variant_id=f"vg{i}", verdict="invalid", trial_index=i))
    md = build_report(recs, [])
    line = next(l for l in md.splitlines()
                if "Invalid rate is real signal" in l)
    # numerator and denominator are both Python-scoped, and labelled Python
    assert "1 of 4 Python trials" in line
    assert "(25%)" in line
    # the cross-scope bug would have surfaced as a >100% rate
    assert "125%" not in line
    m = re.search(r"(\d+) of (\d+) Python trials \((\d+)%\)", line)
    assert m, line
    num, den, pct = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert round(100 * num / den) == pct


# -- (c) mixed-pack banner ----------------------------------------------------

def test_mixed_pack_versions_trip_banner_in_both_generators(capsys):
    # Same language (go), two detector_pack_versions: the signature of a
    # skipped/partial regrade. Both generators must shout, and still render.
    recs = _python_only()
    recs.append(rec(model="claude-opus-4-8", task_id="sql-go/user-lookup",
                    language="go", detector_pack_version="sql-go@0.1.0",
                    variant_id="vg0", verdict="secure"))
    recs.append(rec(model="claude-opus-4-8", task_id="sql-go/user-lookup",
                    language="go", detector_pack_version="sql-go@0.3.0",
                    variant_id="vg1", verdict="vulnerable"))
    assert M.mixed_pack_languages(recs) == {"go": ["sql-go@0.1.0", "sql-go@0.3.0"]}

    md = build_report(recs, [])
    assert "WARNING: mixed detector pack versions" in md
    assert "sql-go@0.1.0" in md and "sql-go@0.3.0" in md
    # still renders the full report, not a refusal
    assert "## Limitations" in md

    h = build_html_report(recs, [])
    assert "WARNING: mixed detector pack versions" in h
    assert "sql-go@0.1.0" in h and "sql-go@0.3.0" in h

    # and the same warning went to stderr from both generators
    err = capsys.readouterr().err
    assert err.count("mixed detector pack versions within a language") >= 2


def test_clean_single_pack_has_no_banner():
    recs = _mixed_language()  # each language carries exactly one pack version
    assert M.mixed_pack_languages(recs) == {}
    md = build_report(recs, [])
    h = build_html_report(recs, [])
    assert "WARNING: mixed detector pack versions" not in md
    assert "WARNING: mixed detector pack versions" not in h


# -- (d) natural model ordering -----------------------------------------------

def test_natural_sort_orders_qwen3_8b_before_14b():
    assert M.sorted_models(["qwen3:14b", "qwen3:8b"]) == ["qwen3:8b", "qwen3:14b"]
    # lexicographic order would put "14b" first; natural order must not.
    assert (M.natural_sort_key("qwen3:8b") < M.natural_sort_key("qwen3:14b"))


def test_generators_order_models_naturally():
    # Two open-weight models whose numeric suffixes sort the wrong way
    # lexicographically. Both must appear, with :8b before :14b in each output.
    recs = []
    for m in ["qwen3:14b", "qwen3:8b"]:
        for i in range(2):
            recs.append(rec(model=m, task_id="sql/user-lookup",
                            variant_id=f"v{i}", verdict="secure", trial_index=i))
    md = build_report(recs, [])
    # find the Models: line and confirm 8b precedes 14b
    models_line = next(l for l in md.splitlines() if l.startswith("- **Models:**"))
    assert models_line.index("qwen3:8b") < models_line.index("qwen3:14b")


# -- (e) no en/em dashes ------------------------------------------------------

def test_no_unicode_dashes_in_output():
    recs = _mixed_language()
    # add an open-weight model too, exercising the vendor-split copy paths
    for i in range(2):
        recs.append(rec(model="qwen3:8b", task_id="sql/user-lookup",
                        variant_id=f"vq{i}", verdict="vulnerable", trial_index=i))
    md = build_report(recs, [])
    h = build_html_report(recs, [])
    for name, txt in [("markdown", md), ("html", h)]:
        assert EN_DASH not in txt, f"{name} output contains an en dash"
        assert EM_DASH not in txt, f"{name} output contains an em dash"
