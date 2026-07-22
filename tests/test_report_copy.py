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


def test_two_categories_in_one_language_do_not_trip_banner():
    # A single language (python) carrying two DIFFERENT category packs
    # (sql@0.9.0 + cmdi-python@0.1.0 + xss@0.1.0), each at its own current
    # version, is NOT a skipped regrade: the guard keys by pack base name, so no
    # banner fires in either generator.
    recs = _multi_category()
    packs = {r["detector_pack_version"] for r in recs}
    assert len(packs) > 1  # the language really does carry several packs
    assert M.mixed_pack_languages(recs) == {}
    md = build_report(recs, [])
    h = build_html_report(recs, [])
    assert "WARNING: mixed detector pack versions" not in md
    assert "WARNING: mixed detector pack versions" not in h


def _typescript_two_categories() -> list[dict]:
    """Python SQL plus a typescript language carrying BOTH sql-typescript (all
    secure) and cmdi-typescript (all vulnerable). The cross-language SQL
    comparison must show typescript at its sql-only rate (0%, n=4), never the
    category-contaminated pooled rate (50%, n=8)."""
    out = _python_only()
    for cat, prefix, pack, verdict in [
            ("sql", "sql-typescript", "sql-typescript@0.2.0", "secure"),
            ("command-injection", "cmdi-typescript", "cmdi-typescript@0.2.0",
             "vulnerable")]:
        for m in ["claude-opus-4-8", "claude-haiku-4-5"]:
            for i in range(2):
                out.append(rec(model=m, task_id=f"{prefix}/task",
                               language="typescript", category=cat,
                               detector_pack_version=pack, variant_id=f"v{i}",
                               trial_index=i, verdict=verdict))
    return out


def test_cross_language_section_is_sql_scoped():
    recs = _typescript_two_categories()
    # metric-level: typescript sql-only VIR is 0/4, not the contaminated 4/8
    vl = M.vir_by_language(recs, set(), condition="none", category="sql",
                           categories={})
    assert (vl["typescript"].k, vl["typescript"].n) == (0, 4)
    # unscoped would have pooled sql + cmdi into 4/8
    assert M.vir_by_language(recs, set(), condition="none")["typescript"].n == 8

    md = build_report(recs, [])
    h = build_html_report(recs, [])
    # the pooled bullet reports typescript over the sql-only n=4, never n=8
    line = next(l for l in md.splitlines() if "Pooled across models" in l)
    assert "typescript 0% (0-" in line and "n=4)" in line
    assert "n=8)" not in line
    # and the html cross-language block agrees (sql-only, no cmdi contamination)
    assert "n=8" not in h.split("Cross-language")[1].split("</section>")[0]


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


# -- (f) multi-category CWE + data-derived hypothesis count -------------------

def _multi_category() -> list[dict]:
    """Python SQL plus a python command-injection block and a python XSS block,
    so the category count, the CWE column, and the 'N of 6 hypotheses' copy all
    have more than one category to report."""
    out = _python_only()
    for cat, prefix, pack in [
            ("command-injection", "cmdi-python", "cmdi-python@0.1.0"),
            ("xss", "xss-python", "xss@0.1.0")]:
        for m in ["claude-opus-4-8", "claude-haiku-4-5"]:
            for i in range(2):
                out.append(rec(model=m, task_id=f"{prefix}/task",
                               category=cat, detector_pack_version=pack,
                               variant_id=f"v{i}", trial_index=i,
                               verdict="secure"))
    return out


def test_category_verdicts_table_has_cwe_column():
    recs = _multi_category()
    md = build_report(recs, [])
    # the category-verdicts table carries Category, Language, CWE and a pooled
    # VIR column, then per-model verdict columns (claims-2 / num-4).
    assert "| Category | Language | CWE | VIR (pooled) |" in md
    assert "CWE-89" in md and "CWE-78" in md and "CWE-79" in md


def test_hypothesis_count_is_data_derived():
    # three categories present -> "3 of the 6" not "1 of the 6"
    md = build_report(_multi_category(), [])
    assert "3 of the 6" in md
    assert "1 of the 6" not in md
    # single-category data still reads "1 of the 6"
    md1 = build_report(_python_only(), [])
    assert "1 of the 6" in md1


def test_no_dashes_with_multi_category():
    md = build_report(_multi_category(), [])
    assert EN_DASH not in md and EM_DASH not in md


def _cross_language_xss() -> list[dict]:
    """Python SQL (the analytical body) plus a typescript XSS block that ships
    ONLY outside python, so a python-only category-verdicts table would drop it.
    The two Claude models each inject XSS, so the cell is a real standing risk."""
    out = _python_only()
    for m in ["claude-opus-4-8", "claude-haiku-4-5"]:
        for i in range(8):
            out.append(rec(model=m, task_id="xss-typescript/reflected",
                           language="typescript", category="xss",
                           detector_pack_version="xss-typescript@0.2.0",
                           variant_id=f"vx{i}", trial_index=i,
                           verdict="vulnerable" if i < 3 else "secure"))
    return out


def test_category_verdicts_cover_all_categories_and_languages():
    # claims-2: a category that ships only in typescript (xss) must still get a
    # per-language verdict row, even though the Python analytical body drops it.
    md = build_report(_cross_language_xss(), [])
    section = md.split("## Category verdicts")[1].split("## ")[0]
    # the xss/typescript row is present with its CWE anchor and a pooled VIR
    assert "`xss`" in section and "`typescript`" in section
    assert "CWE-79" in section
    # and it reads as a standing risk for the two Claude models (num-4: the
    # pooled VIR number is surfaced too)
    assert "standing risk" in section
    # the pooled-VIR column header exists so xss surfaces as an explicit number
    assert "VIR (pooled)" in section


def test_eradicated_power_caveat_is_present():
    # meth-1: the report must disclose that 'eradicated' is not reachable at
    # this n (its absence is a power limit), stated from the data.
    md = build_report(_cross_language_xss(), [])
    assert "zero-event trials" in md
    assert "not symmetric" in md.lower() or "power limit" in md.lower()


# -- (i) python-only scope labels (num-2) -------------------------------------

def test_python_only_scope_labels_present():
    md = build_report(_mixed_language(), [])
    # the Headline table title, the per-task table title, and the Bottom-line
    # SQL sentence all carry an explicit Python-only scope (num-2), so a reader
    # of the 4-language header does not take them as spanning all languages.
    assert "## Headline: SQL VIR by model × condition (Python only)" in md
    assert "## Per-task VIR (condition `none`, Python only)" in md
    bl = md.split("## Bottom line")[1].split("## ")[0]
    assert "(Python only)" in bl


# -- (g) review mode section --------------------------------------------------

def _review_record(model="claude-opus-4-8", flagged=True, trial_index=0,
                   verdict="secure", error=None) -> dict:
    """A review-mode trial: category sql, python, condition none, carrying
    flagged_existing (the field review reuses from remediation)."""
    return rec(model=model, task_id="review-sql/list-products-sorted",
               category="sql", mode="review", condition="none",
               variant_id="v1-plain", trial_index=trial_index, verdict=verdict,
               flagged_existing=flagged, error=error,
               detector_pack_version="sql@0.9.0")


def test_review_section_renders_flag_rate():
    recs = _python_only()  # a normal generate body so the report has content
    # two models reviewing: opus flags both, haiku flags neither
    recs.append(_review_record(model="claude-opus-4-8", flagged=True,
                               trial_index=0))
    recs.append(_review_record(model="claude-opus-4-8", flagged=True,
                               trial_index=1))
    recs.append(_review_record(model="claude-haiku-4-5", flagged=False,
                               trial_index=0))
    recs.append(_review_record(model="claude-haiku-4-5", flagged=False,
                               trial_index=1))
    md = build_report(recs, [])
    assert "Review mode: does the model flag the planted vulnerability?" in md
    # opus flagged 2/2 -> 100%, haiku 0/2 -> 0%
    section = md.split("## Review mode")[1]
    assert "100%" in section and "0%" in section
    assert EN_DASH not in md and EM_DASH not in md


def test_review_records_excluded_from_headline():
    # A review SECURE verdict must NOT count as a gradable generate trial in the
    # Python headline body: the invalid/headline denominators are generate-only.
    recs = _python_only()  # 4 python generate trials
    for i in range(4):
        recs.append(_review_record(model="claude-opus-4-8", flagged=True,
                                   trial_index=10 + i))
    md = build_report(recs, [])
    # the Trials line counts all records, but the Python invalid bullet's
    # denominator is the generate-only python body (4), never 8.
    line = next(l for l in md.splitlines()
                if "Invalid rate is real signal" in l)
    assert "of 4 Python trials" in line


def test_no_review_section_without_review_records():
    md = build_report(_python_only(), [])
    assert "## Review mode" not in md


# -- (h) html twins: the same B9 fixes must land in the HTML generator --------

def _with_reviews(base=None) -> list[dict]:
    """A generate body plus review-mode trials: opus flags both reviews (100%),
    haiku flags neither (0%)."""
    recs = list(base if base is not None else _python_only())
    recs.append(_review_record(model="claude-opus-4-8", flagged=True, trial_index=0))
    recs.append(_review_record(model="claude-opus-4-8", flagged=True, trial_index=1))
    recs.append(_review_record(model="claude-haiku-4-5", flagged=False, trial_index=0))
    recs.append(_review_record(model="claude-haiku-4-5", flagged=False, trial_index=1))
    return recs


def test_html_category_verdicts_table_has_cwe_column():
    h = build_html_report(_multi_category(), [])
    # the HTML category-verdicts table now carries a CWE header and the anchors
    assert "Category verdicts" in h
    assert "<th>CWE</th>" in h
    assert "CWE-89" in h and "CWE-78" in h and "CWE-79" in h


def test_html_hypothesis_count_and_class_noun_data_derived():
    h3 = build_html_report(_multi_category(), [])  # sql + cmdi + xss
    assert "3 of the 6" in h3
    assert "3 vulnerability classes" in h3
    assert "1 of the 6" not in h3
    # single-category data still reads "1 of the 6" and "one vulnerability class"
    h1 = build_html_report(_python_only(), [])
    assert "1 of the 6" in h1
    assert "one vulnerability class" in h1
    # and it names the category with its CWE anchor, not a hardcoded string
    assert "SQL injection/CWE-89" in h1


def test_html_review_section_renders_flag_rate():
    h = build_html_report(_with_reviews(), [])
    assert "Review mode: does the model flag the planted vulnerability?" in h
    section = h.split("Review mode: does the model")[1]
    # opus flagged 2/2 -> 100%, haiku 0/2 -> 0%
    assert "100%" in section and "0%" in section


def test_html_no_review_section_without_review_records():
    h = build_html_report(_python_only(), [])
    assert "Review mode: does the model" not in h


def test_html_headline_excludes_review_records():
    # Review SECURE trials must NOT leak into the Python headline body: Finding
    # 01 (bare-prompt VIR by model) must be byte-identical with or without the
    # review records present.
    base = _python_only()

    def finding01(recs: list[dict]) -> str:
        h = build_html_report(recs, [])
        return h.split("num'>01<")[1].split("</section>")[0]

    assert finding01(base) == finding01(_with_reviews(base))


def test_html_no_dashes_multi_category_and_review():
    for recs in (_multi_category(), _with_reviews()):
        h = build_html_report(recs, [])
        assert EN_DASH not in h, "html output contains an en dash"
        assert EM_DASH not in h, "html output contains an em dash"
