"""Export-document invariants (schema 1.0). The web export is a pure function
of the JSONL records plus task specs, and every rate must agree with
lgtm_bench.metrics by construction, so these tests lock in:

  (a) the top-level shape and the required keys a frontend depends on;
  (b) VIR point estimates and Wilson CIs equal metrics.py exactly (no drift);
  (c) an unknown model id never crashes the export and gets fallback metadata;
  (d) multi-category records nest cleanly (XSS lands without a shape change);
  (e) no en/em dashes leak into the serialized JSON;
  (f) the export is deterministic: same input, byte-identical output.

Fast unit tests over small synthetic record lists (no model calls, no files),
mirroring tests/test_report_copy.py's `rec` shape.
"""
from __future__ import annotations

from lgtm_bench import metrics as M
from lgtm_bench.export import build_export, export_json
from lgtm_bench.schema import ArtifactKind, Condition, TaskSpec

EN_DASH = chr(0x2013)
EM_DASH = chr(0x2014)


def rec(model="claude-opus-4-8", task_id="sql/user-lookup", mode="generate",
        language="python", condition="none", variant_id="v1-plain",
        verdict="secure", run_id="2026-07-13T03-40-43Z",
        detector_pack_version="sql@0.9.0", fixture_version="1",
        trial_index=0, runner="claude-code", **extra) -> dict:
    d = {
        "trial_key": f"{model}|{task_id}|{condition}|{variant_id}|{trial_index}",
        "run_id": run_id, "model": model, "task_id": task_id, "mode": mode,
        "language": language, "condition": condition, "variant_id": variant_id,
        "trial_index": trial_index, "verdict": verdict,
        "fixed_existing": None, "flagged_existing": None, "findings": [],
        "error": None, "detector_pack_version": detector_pack_version,
        "fixture_version": fixture_version, "runner": runner,
    }
    d.update(extra)
    return d


def _task(task_id="sql/user-lookup", category="sql", language="python",
          variants=None) -> TaskSpec:
    variants = variants or [{"id": "v1-plain", "prompt": "x"}]
    return TaskSpec(id=task_id, category=category, language=language,
                    title="t", conditions=[Condition.NONE],
                    artifact=ArtifactKind.FUNCTION, variants=variants)


def _dataset() -> list[dict]:
    """A small mixed dataset: two Claude models plus one open-weight model,
    condition none, a couple of variants, some vulnerable and invalid trials."""
    out = []
    for m in ["claude-opus-4-8", "claude-haiku-4-5"]:
        for i, v in enumerate(["v1-plain", "v2-contextual"]):
            for j in range(2):
                out.append(rec(model=m, variant_id=v, trial_index=j,
                               verdict="vulnerable" if (m.endswith("haiku-4-5")
                                                        and i == 0 and j == 0)
                               else "secure"))
    # open-weight model with an invalid trial in the pool
    for i, v in enumerate(["v1-plain", "v2-contextual"]):
        for j in range(2):
            verdict = "secure"
            if i == 0 and j == 0:
                verdict = "vulnerable"
            if i == 1 and j == 1:
                verdict = "invalid"
            out.append(rec(model="qwen2.5-coder:7b", runner="ollama",
                           variant_id=v, trial_index=j, verdict=verdict))
    return out


def _tasks() -> list[TaskSpec]:
    return [_task(variants=[{"id": "v1-plain", "prompt": "x"},
                            {"id": "v2-contextual", "prompt": "y"}])]


# -- (a) shape and required keys ---------------------------------------------

def test_top_level_shape_and_required_keys():
    doc = build_export(_dataset(), _tasks())
    for key in ("schemaVersion", "meta", "models", "categories",
                "detectorPacks", "results"):
        assert key in doc, key
    assert doc["schemaVersion"] == "1.0"

    meta = doc["meta"]
    for key in ("harnessVersion", "benchmark", "runIds", "runCount",
                "trialTotals", "sampling", "ci", "axes", "headlinePopulation",
                "metrics", "eradicationRule", "dataQuality",
                "detectorMethodology"):
        assert key in meta, key
    # trial totals are internally consistent
    tt = meta["trialTotals"]
    assert tt["gradable"] == tt["secure"] + tt["vulnerable"]
    assert tt["published"] == tt["gradable"] + tt["invalid"]
    assert tt["published"] == len(_dataset())
    # ci block carries the exact Wilson z
    assert meta["ci"]["z"] == M.Z95 and meta["ci"]["method"] == "wilson"
    # generatedAt derives from the newest run id, converted to ISO
    assert meta["generatedAt"] == "2026-07-13T03:40:43Z"

    results = doc["results"]
    for key in ("pooled", "byModelCondition", "byLanguage", "byModelLanguage",
                "byModelTask", "categoryVerdicts", "invalidByModel", "flipRate",
                "promptSensitivity", "contaminationDelta", "brownfieldDelta",
                "safetyHintDelta", "remediation"):
        assert key in results, key

    # every VIR stat object carries the canonical keys
    for cell in results["byModelCondition"]:
        v = cell["vir"]
        for k in ("vulnerable", "gradable", "rate", "ciLow", "ciHigh", "invalid"):
            assert k in v, k


def test_macro_vir_never_carries_a_ci():
    doc = build_export(_dataset(), _tasks())
    macro = doc["results"]["pooled"]["macro"]["vir"]
    assert macro["ciLow"] is None and macro["ciHigh"] is None
    assert "models" in macro
    # per-language macroVir is a bare scalar (or null), never a stat object
    for cell in doc["results"]["byLanguage"]:
        assert not isinstance(cell["macroVir"], dict)


# -- (b) numbers match metrics.py exactly ------------------------------------

def test_vir_and_ci_match_metrics_exactly():
    records = _dataset()
    tasks = _tasks()
    hints = M.hint_map(tasks)
    doc = build_export(records, tasks)

    expected = M.vir_by_model_condition(records, hints, mode="generate")
    got = {(c["model"], c["condition"]): c["vir"]
           for c in doc["results"]["byModelCondition"]}
    assert set(got) == {k for k in expected}
    for key, rate in expected.items():
        lo, hi = rate.ci
        cell = got[key]
        assert cell["vulnerable"] == rate.k
        assert cell["gradable"] == rate.n
        assert cell["rate"] == rate.p
        assert cell["ciLow"] == lo
        assert cell["ciHigh"] == hi

    # pooled trial-weighted equals the same headline population metrics computes
    pop = [r for r in M.headline(records, hints)
           if r["condition"] == "none" and r["mode"] == "generate"]
    pooled = doc["results"]["pooled"]["trialWeighted"]["vir"]
    assert pooled["gradable"] == len(pop)
    assert pooled["vulnerable"] == sum(1 for r in pop
                                       if r["verdict"] == "vulnerable")
    lo, hi = M.wilson(pooled["vulnerable"], pooled["gradable"])
    assert pooled["ciLow"] == lo and pooled["ciHigh"] == hi

    # pooled macro equals metrics.macro_vir
    assert doc["results"]["pooled"]["macro"]["vir"]["rate"] == \
        M.macro_vir(records, hints, condition="none")


def test_per_cell_invalid_count_is_scoped():
    # one invalid qwen trial sits in the condition-none generate pool
    records = _dataset()
    doc = build_export(records, _tasks())
    qwen = next(c for c in doc["results"]["byModelCondition"]
               if c["model"] == "qwen2.5-coder:7b" and c["condition"] == "none")
    assert qwen["vir"]["invalid"] == 1
    # and that invalid trial is excluded from the gradable denominator
    assert qwen["vir"]["gradable"] == 3


def test_invalid_by_model_matches_metrics():
    records = _dataset()
    doc = build_export(records, _tasks())
    expected = M.invalid_by_model(records)
    got = {c["model"]: c["invalidRate"] for c in doc["results"]["invalidByModel"]}
    for m, rate in expected.items():
        assert got[m]["invalid"] == rate.k
        assert got[m]["total"] == rate.n
        assert got[m]["rate"] == rate.p


# -- (c) unknown model id -> fallback, no crash ------------------------------

def test_unknown_model_gets_fallback_metadata():
    records = _dataset()
    records += [rec(model="mystery-model:13b", runner="ollama",
                    variant_id="v1-plain", trial_index=k,
                    verdict="secure") for k in range(2)]
    doc = build_export(records, _tasks())  # must not raise
    entry = next(m for m in doc["models"] if m["id"] == "mystery-model:13b")
    assert entry["displayName"] == "mystery-model:13b"
    assert entry["family"] is None
    assert entry["weights"] == "open"
    assert entry["params"] == "13B"          # parsed from the :13b suffix
    assert entry["runner"] == "ollama"       # taken from the record
    assert entry["deprecated"] is False
    # known model still carries curated metadata
    opus = next(m for m in doc["models"] if m["id"] == "claude-opus-4-8")
    assert opus["vendor"] == "anthropic" and opus["weights"] == "proprietary"


# -- (d) multi-category nesting ----------------------------------------------

def test_multi_category_records_nest():
    records = _dataset()
    # add an XSS category task + trials
    for k in range(2):
        records.append(rec(model="claude-opus-4-8", task_id="xss/reflected",
                           variant_id="v1-plain", trial_index=k,
                           detector_pack_version="xss@0.1.0", verdict="secure"))
    tasks = _tasks() + [_task(task_id="xss/reflected", category="xss")]
    doc = build_export(records, tasks)

    cat_ids = {c["id"] for c in doc["categories"]}
    assert {"sql", "xss"} <= cat_ids
    xss = next(c for c in doc["categories"] if c["id"] == "xss")
    assert xss["cwe"] == ["CWE-79"]
    # axis enumeration also lists both categories
    assert set(doc["meta"]["axes"]["category"]) >= {"sql", "xss"}
    # a category verdict cell exists for the xss category
    assert any(c["category"] == "xss"
               for c in doc["results"]["categoryVerdicts"])
    # detector packs keyed by language include the xss pack version
    versions = [e["version"] for entries in doc["detectorPacks"].values()
                for e in entries]
    assert "xss@0.1.0" in versions


# -- (e) no en/em dashes ------------------------------------------------------

def test_no_unicode_dashes_in_output():
    records = _dataset()
    records.append(rec(model="qwen3:8b", runner="ollama", variant_id="v1-plain",
                       trial_index=9, verdict="vulnerable"))
    text = export_json(records, _tasks())
    assert EN_DASH not in text
    assert EM_DASH not in text


# -- (f) determinism ----------------------------------------------------------

def test_export_is_byte_identical_for_same_input():
    records = _dataset()
    tasks = _tasks()
    a = export_json(records, tasks)
    b = export_json(list(records), tasks)
    assert a == b
    # shuffling input record order must not change the output (dedup + sorted
    # arrays make the document order-independent)
    import random
    shuffled = list(records)
    random.Random(1).shuffle(shuffled)
    assert export_json(shuffled, tasks) == a


# -- (g) headline aggregates are Python-scoped (mirrors report.py) -----------

def _mixed_dataset(go_verdict="vulnerable") -> list[dict]:
    """Python trials plus a block of Go trials whose VIR is set by go_verdict.
    Used to prove the headline aggregates are scoped to Python exactly as
    report.py scopes its analytical body: the Go block, however extreme, must
    never move the headline pooled number or the byModelCondition cells."""
    out = []
    # python: one model, condition none, 1 vulnerable of 4 gradable
    for j in range(4):
        out.append(rec(model="claude-opus-4-8", variant_id="v1-plain",
                       trial_index=j,
                       verdict="vulnerable" if j == 0 else "secure"))
    # go: a big block of generate/condition-none trials at the given verdict
    for j in range(10):
        out.append(rec(model="claude-opus-4-8", task_id="sql-go/user-lookup",
                       language="go", detector_pack_version="sql-go@0.3.0",
                       variant_id="v1-plain", trial_index=j, verdict=go_verdict))
    return out


def _mixed_tasks() -> list[TaskSpec]:
    return [_task(variants=[{"id": "v1-plain", "prompt": "x"}]),
            _task(task_id="sql-go/user-lookup", category="sql", language="go")]


def test_headline_pooled_equals_python_only_figure():
    records = _mixed_dataset(go_verdict="vulnerable")
    tasks = _mixed_tasks()
    hints = M.hint_map(tasks)
    doc = build_export(records, tasks)

    # independent python-only headline pooling (condition none, generate,
    # gradable = secure+vulnerable), computed straight from the same records
    py = [r for r in records if M.record_language(r) == "python"]
    pop = [r for r in M.headline(py, hints)
           if r["condition"] == "none" and r["mode"] == "generate"]
    pooled = doc["results"]["pooled"]["trialWeighted"]["vir"]
    assert pooled["gradable"] == len(pop) == 4
    assert pooled["vulnerable"] == \
        sum(1 for r in pop if r["verdict"] == "vulnerable") == 1
    lo, hi = M.wilson(pooled["vulnerable"], pooled["gradable"])
    assert pooled["ciLow"] == lo and pooled["ciHigh"] == hi
    # the pooled scope is explicitly tagged python so the frontend isn't misled
    assert doc["results"]["pooled"]["trialWeighted"]["scope"]["language"] == \
        "python"
    # and byModelCondition none cell equals the python-only per-model VIR
    none_cell = next(c["vir"] for c in doc["results"]["byModelCondition"]
                     if c["model"] == "claude-opus-4-8" and
                     c["condition"] == "none")
    assert none_cell["vulnerable"] == 1 and none_cell["gradable"] == 4
    assert all(c["scope"] == "python"
               for c in doc["results"]["byModelCondition"])


def test_by_model_language_retains_non_python():
    records = _mixed_dataset(go_verdict="vulnerable")
    tasks = _mixed_tasks()
    doc = build_export(records, tasks)
    langs = {c["language"] for c in doc["results"]["byModelLanguage"]}
    assert "go" in langs and "python" in langs
    go_cell = next(c for c in doc["results"]["byModelLanguage"]
                   if c["language"] == "go")
    # the cross-language cell reflects the full go block (all 10 vulnerable)
    assert go_cell["vir"]["gradable"] == 10
    assert go_cell["vir"]["vulnerable"] == 10
    assert go_cell["scope"] == "all-languages"
    # byLanguage keeps go too, tagged all-languages
    by_lang = {c["language"]: c for c in doc["results"]["byLanguage"]}
    assert "go" in by_lang and by_lang["go"]["scope"] == "all-languages"


def test_cross_language_rates_do_not_move_the_headline():
    """Regression: a Go block that swings from all-vulnerable to all-secure must
    NOT change the Python-scoped headline pooled number or byModelCondition."""
    tasks = _mixed_tasks()
    hi = build_export(_mixed_dataset(go_verdict="vulnerable"), tasks)
    lo = build_export(_mixed_dataset(go_verdict="secure"), tasks)

    pooled_hi = hi["results"]["pooled"]["trialWeighted"]["vir"]
    pooled_lo = lo["results"]["pooled"]["trialWeighted"]["vir"]
    assert (pooled_hi["vulnerable"], pooled_hi["gradable"], pooled_hi["rate"]) \
        == (pooled_lo["vulnerable"], pooled_lo["gradable"], pooled_lo["rate"])
    # macro pooled unmoved as well
    assert hi["results"]["pooled"]["macro"]["vir"]["rate"] == \
        lo["results"]["pooled"]["macro"]["vir"]["rate"]

    def none_cell(doc):
        return next(c["vir"] for c in doc["results"]["byModelCondition"]
                    if c["model"] == "claude-opus-4-8" and
                    c["condition"] == "none")
    assert none_cell(hi) == none_cell(lo)
    # but the cross-language array DID move (proving the go data is still there)
    def go_cell(doc):
        return next(c["vir"]["vulnerable"]
                    for c in doc["results"]["byModelLanguage"]
                    if c["language"] == "go")
    assert go_cell(hi) == 10 and go_cell(lo) == 0


def test_meta_declares_python_headline_scope():
    doc = build_export(_mixed_dataset(), _mixed_tasks())
    hp = doc["meta"]["headlinePopulation"]
    assert hp["languageScope"] == "python"
    assert "languageScopeNote" in hp


# -- (h) multi-category grouping + CWE ----------------------------------------

def _multi_cat_dataset() -> list[dict]:
    """Python SQL plus a python command-injection block, so the multi-category
    grouping (byModelCondition split per category, categoryVerdicts per
    category, detector packs per category) has two categories to separate."""
    out = []
    for j in range(4):
        out.append(rec(model="claude-opus-4-8", variant_id="v1-plain",
                       trial_index=j,
                       verdict="vulnerable" if j == 0 else "secure"))
    for j in range(4):
        out.append(rec(model="claude-opus-4-8", task_id="cmdi-python/ping-host",
                       category="command-injection", variant_id="v1-plain",
                       trial_index=j, detector_pack_version="cmdi-python@0.1.0",
                       verdict="vulnerable" if j < 2 else "secure"))
    return out


def _multi_cat_tasks() -> list[TaskSpec]:
    return [_task(),
            _task(task_id="cmdi-python/ping-host", category="command-injection")]


def test_by_model_condition_splits_per_category():
    doc = build_export(_multi_cat_dataset(), _multi_cat_tasks())
    cells = doc["results"]["byModelCondition"]
    cats = {c["category"] for c in cells}
    assert cats == {"sql", "command-injection"}
    # each category keeps its own VIR: sql 1/4, cmdi 2/4 (no pooling)
    sql = next(c for c in cells if c["category"] == "sql")
    cmdi = next(c for c in cells if c["category"] == "command-injection")
    assert (sql["vir"]["vulnerable"], sql["vir"]["gradable"]) == (1, 4)
    assert (cmdi["vir"]["vulnerable"], cmdi["vir"]["gradable"]) == (2, 4)


def test_category_verdicts_carry_cwe_per_category():
    doc = build_export(_multi_cat_dataset(), _multi_cat_tasks())
    verdicts = {c["category"]: c["cwe"] for c in doc["results"]["categoryVerdicts"]}
    assert verdicts["sql"] == ["CWE-89"]
    assert verdicts["command-injection"] == ["CWE-78"]


def test_detector_packs_carry_correct_category():
    doc = build_export(_multi_cat_dataset(), _multi_cat_tasks())
    packs = {e["version"]: e["category"]
             for entries in doc["detectorPacks"].values() for e in entries}
    assert packs["sql@0.9.0"] == "sql"
    assert packs["cmdi-python@0.1.0"] == "command-injection"


def test_typescript_appears_in_language_axis():
    records = _dataset()
    for k in range(2):
        records.append(rec(model="claude-opus-4-8",
                           task_id="sql-typescript/user-lookup",
                           language="typescript",
                           detector_pack_version="sql-typescript@0.1.0",
                           variant_id="v1-plain", trial_index=k,
                           verdict="secure"))
    doc = build_export(records, _tasks() + [
        _task(task_id="sql-typescript/user-lookup", category="sql",
              language="typescript")])
    # typescript sits after rust in the ordered language axis
    assert "typescript" in doc["meta"]["axes"]["language"]
    assert doc["meta"]["axes"]["language"].index("typescript") > \
        doc["meta"]["axes"]["language"].index("python")


# -- (i) review mode ----------------------------------------------------------

def _review_rec(model="claude-opus-4-8", flagged=True, trial_index=0,
                verdict="secure") -> dict:
    return rec(model=model, task_id="review-sql/list-products-sorted",
               category="sql", mode="review", condition="none",
               variant_id="v1-plain", trial_index=trial_index, verdict=verdict,
               flagged_existing=flagged, detector_pack_version="sql@0.9.0")


def test_review_detection_array_and_axis():
    records = _dataset()
    records.append(_review_rec(model="claude-opus-4-8", flagged=True,
                               trial_index=0))
    records.append(_review_rec(model="claude-opus-4-8", flagged=False,
                               trial_index=1))
    doc = build_export(records, _tasks())
    # the reviewDetection array exists and matches metrics exactly
    rd = doc["results"]["reviewDetection"]
    opus = next(c for c in rd if c["model"] == "claude-opus-4-8")
    assert opus["flag"]["flagged"] == 1 and opus["flag"]["n"] == 2
    assert opus["flag"]["rate"] == M.review_detection(records)[
        "claude-opus-4-8"].p
    # review is an enumerated mode axis, and its description is documented
    assert "review" in doc["meta"]["axes"]["mode"]
    assert "reviewDetection" in doc["meta"]["metrics"]


def test_review_trials_do_not_touch_vir_or_invalid():
    """A review SECURE/INVALID trial must not move the generate VIR headline or
    the invalid-by-model counts (review is its own axis)."""
    base = _dataset()
    with_review = list(base) + [
        _review_rec(trial_index=0, verdict="secure"),
        _review_rec(trial_index=1, verdict="invalid", flagged=False)]
    a = build_export(base, _tasks())
    b = build_export(with_review, _tasks())
    assert a["results"]["byModelCondition"] == b["results"]["byModelCondition"]
    assert a["results"]["invalidByModel"] == b["results"]["invalidByModel"]
    assert a["results"]["flipRate"] == b["results"]["flipRate"]


def test_current_and_superseded_packs_flagged():
    records = _dataset()
    # two go pack versions -> the older is current:false, newer current:true,
    # and the language trips mixedPackLanguages
    for v, k in [("sql-go@0.2.0", 0), ("sql-go@0.3.0", 1)]:
        records.append(rec(model="claude-opus-4-8", task_id="sql-go/user-lookup",
                           language="go", detector_pack_version=v,
                           variant_id="v1-plain", trial_index=k,
                           verdict="secure"))
    tasks = _tasks() + [_task(task_id="sql-go/user-lookup", category="sql",
                              language="go")]
    doc = build_export(records, tasks)
    go = doc["detectorPacks"]["go"]
    current = {e["version"]: e["current"] for e in go}
    assert current == {"sql-go@0.2.0": False, "sql-go@0.3.0": True}
    assert doc["meta"]["dataQuality"]["mixedPackLanguages"] == \
        {"go": ["sql-go@0.2.0", "sql-go@0.3.0"]}
