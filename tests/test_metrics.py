"""Metrics: Wilson CI, flip rate, contamination delta, headline population,
remediation counts."""
from __future__ import annotations

import pytest

from lgtm_bench import metrics as M
from lgtm_bench.schema import Condition, TaskSpec, Variant


def rec(model="m1", task_id="sql/t1", condition="none", variant_id="v1",
        verdict="secure", mode="generate", trial_index=0,
        fixed_existing=None, flagged_existing=None) -> dict:
    return {
        "model": model, "task_id": task_id, "condition": condition,
        "variant_id": variant_id, "verdict": verdict, "mode": mode,
        "trial_index": trial_index, "fixed_existing": fixed_existing,
        "flagged_existing": flagged_existing,
    }


# -- Wilson CI ----------------------------------------------------------------

def test_wilson_k0_lower_bound_is_zero():
    lo, hi = M.wilson(0, 10)
    assert lo == pytest.approx(0.0, abs=1e-12)
    assert 0.0 < hi < 0.35


def test_wilson_kn_upper_bound_is_one():
    lo, hi = M.wilson(10, 10)
    assert hi == pytest.approx(1.0, abs=1e-12)
    assert 0.65 < lo < 1.0


def test_wilson_known_value_8_of_10():
    lo, hi = M.wilson(8, 10)
    assert lo == pytest.approx(0.49, abs=0.02)
    assert hi == pytest.approx(0.94, abs=0.02)


def test_wilson_n0_is_nan():
    lo, hi = M.wilson(0, 0)
    assert lo != lo and hi != hi  # NaN


def test_wilson_bounds_are_clamped_and_ordered():
    for k, n in [(0, 1), (1, 1), (1, 3), (5, 7), (99, 100)]:
        lo, hi = M.wilson(k, n)
        assert 0.0 <= lo <= k / n <= hi <= 1.0


# -- flip rate ----------------------------------------------------------------

def test_flip_rate_mixed_cell():
    records = [
        # cell A: mixed verdicts across 3 trials -> flip
        rec(variant_id="vA", verdict="secure", trial_index=0),
        rec(variant_id="vA", verdict="vulnerable", trial_index=1),
        rec(variant_id="vA", verdict="secure", trial_index=2),
        # cell B: unanimous -> no flip
        rec(variant_id="vB", verdict="secure", trial_index=0),
        rec(variant_id="vB", verdict="secure", trial_index=1),
        # cell C: only one graded trial -> not eligible
        rec(variant_id="vC", verdict="vulnerable", trial_index=0),
        # cell D: secure + invalid -> invalid is not graded, 1 graded trial,
        # not eligible and not a flip
        rec(variant_id="vD", verdict="secure", trial_index=0),
        rec(variant_id="vD", verdict="invalid", trial_index=1),
    ]
    out = M.flip_rate(records)
    assert out["m1"].k == 1
    assert out["m1"].n == 2  # cells A and B eligible
    assert out["m1"].p == pytest.approx(0.5)


def test_flip_rate_is_per_model():
    records = [
        rec(model="m1", verdict="secure"),
        rec(model="m1", verdict="vulnerable", trial_index=1),
        rec(model="m2", verdict="secure"),
        rec(model="m2", verdict="secure", trial_index=1),
    ]
    out = M.flip_rate(records)
    assert out["m1"].k == 1 and out["m1"].n == 1
    assert out["m2"].k == 0 and out["m2"].n == 1


# -- contamination delta ------------------------------------------------------

def test_contamination_delta_arithmetic():
    records = []
    # clean: 1 vulnerable of 4 graded
    for i, v in enumerate(["vulnerable", "secure", "secure", "secure"]):
        records.append(rec(condition="clean-repo", verdict=v, trial_index=i))
    # dirty: 3 vulnerable of 4 graded
    for i, v in enumerate(["vulnerable", "vulnerable", "vulnerable", "secure"]):
        records.append(rec(condition="dirty-repo", verdict=v, trial_index=i))
    # edit-mode records must not count toward the generate-only delta
    records.append(rec(condition="dirty-repo", verdict="vulnerable",
                       mode="edit", task_id="sql/edit1"))
    # invalid records are excluded from rates
    records.append(rec(condition="dirty-repo", verdict="invalid",
                       trial_index=9))

    out = M.contamination_delta(records, hints=set())
    d = out["m1"]
    assert (d["clean"].k, d["clean"].n) == (1, 4)
    assert (d["dirty"].k, d["dirty"].n) == (3, 4)
    assert d["delta"] == pytest.approx(0.75 - 0.25)
    assert d["p_value"] is not None
    assert 0.0 <= d["p_value"] <= 1.0


def test_contamination_delta_requires_both_sides():
    records = [rec(condition="dirty-repo", verdict="vulnerable")]
    assert M.contamination_delta(records, hints=set()) == {}


# -- headline population ------------------------------------------------------

def _hint_tasks() -> list[TaskSpec]:
    return [TaskSpec(
        id="sql/t1", category="sql", title="t",
        conditions=[Condition.NONE],
        variants=[Variant(id="v1", prompt="p"),
                  Variant(id="v-hint", prompt="p safe", safety_hint=True)])]


def test_headline_excludes_safety_hint_variants_and_invalid():
    hints = M.hint_map(_hint_tasks())
    assert hints == {("sql/t1", "v-hint")}
    records = [
        rec(variant_id="v1", verdict="vulnerable"),
        rec(variant_id="v1", verdict="secure", trial_index=1),
        rec(variant_id="v1", verdict="invalid", trial_index=2),
        rec(variant_id="v-hint", verdict="vulnerable"),
        rec(variant_id="v-hint", verdict="secure", trial_index=1),
    ]
    pop = M.headline(records, hints)
    assert len(pop) == 2
    assert all(r["variant_id"] == "v1" for r in pop)
    assert all(r["verdict"] in ("secure", "vulnerable") for r in pop)

    vir = M.vir_by_model_condition(records, hints)
    assert (vir[("m1", "none")].k, vir[("m1", "none")].n) == (1, 2)

    # the hint population is still reported, separately
    hd = M.safety_hint_delta(records, hints)
    assert (hd["m1"]["hint"].k, hd["m1"]["hint"].n) == (1, 2)
    assert (hd["m1"]["plain"].k, hd["m1"]["plain"].n) == (1, 2)


# -- remediation --------------------------------------------------------------

def test_remediation_counts_fixed_and_flagged():
    records = [
        rec(mode="edit", condition="dirty-repo", task_id="sql/e1",
            verdict="secure", fixed_existing=True, flagged_existing=True),
        rec(mode="edit", condition="dirty-repo", task_id="sql/e1",
            verdict="secure", fixed_existing=False, flagged_existing=True,
            trial_index=1),
        rec(mode="edit", condition="dirty-repo", task_id="sql/e1",
            verdict="vulnerable", fixed_existing=False, flagged_existing=False,
            trial_index=2),
        # excluded: invalid dirty edit trial
        rec(mode="edit", condition="dirty-repo", task_id="sql/e1",
            verdict="invalid", trial_index=3),
        # excluded: clean-repo edit trial
        rec(mode="edit", condition="clean-repo", task_id="sql/e1",
            verdict="secure", fixed_existing=None, flagged_existing=False),
        # excluded: generate trial in the dirty repo
        rec(mode="generate", condition="dirty-repo", verdict="secure"),
    ]
    out = M.remediation(records)
    d = out["m1"]
    assert d["n"] == 3
    assert (d["fix"].k, d["fix"].n) == (1, 3)
    assert (d["flag"].k, d["flag"].n) == (2, 3)


def test_html_report_builds_and_is_self_contained(tmp_path):
    import glob, json
    from lgtm_bench.html_report import build_html_report
    from lgtm_bench.schema import load_tasks
    from pathlib import Path
    from lgtm_bench.store import load_records
    recs = load_records([Path(f) for f in glob.glob("results-published/*.jsonl")])
    if not recs:
        return
    html = build_html_report(recs, load_tasks(Path("tasks")))
    assert html.strip().startswith("<!doctype")
    assert "<svg" in html
    # no external stylesheet/script/image resources
    assert 'src="http' not in html
    assert "<link" not in html and "<script" not in html
