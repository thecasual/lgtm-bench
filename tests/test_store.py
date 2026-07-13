"""JSONL result store: append, resume via existing_keys, crash tolerance."""
from __future__ import annotations

import json

from lgtm_bench.schema import Condition, Mode, TrialRecord, Verdict
from lgtm_bench.store import ResultStore, load_records


def _record(key: str, verdict: Verdict = Verdict.SECURE) -> TrialRecord:
    return TrialRecord(
        trial_key=key, run_id="run-1", model="mock-model",
        task_id="sql/unit-case", mode=Mode.GENERATE, condition=Condition.NONE,
        variant_id="v1", trial_index=0, prompt="p", raw_output="out",
        extracted_code="code", verdict=verdict)


def test_append_and_existing_keys_resume(tmp_path):
    store = ResultStore(tmp_path / "results" / "run.jsonl")
    assert store.existing_keys() == set()  # missing file is fine

    store.append(_record("k1"))
    store.append(_record("k2", Verdict.VULNERABLE))

    assert store.existing_keys() == {"k1", "k2"}

    # resume semantics: a fresh store on the same path sees the same keys,
    # so completed trials would be skipped
    resumed = ResultStore(tmp_path / "results" / "run.jsonl")
    assert resumed.existing_keys() == {"k1", "k2"}

    grid = ["k1", "k2", "k3"]
    todo = [k for k in grid if k not in resumed.existing_keys()]
    assert todo == ["k3"]

    records = resumed.load()
    assert [r["trial_key"] for r in records] == ["k1", "k2"]
    assert records[1]["verdict"] == "vulnerable"


def test_torn_trailing_line_tolerated(tmp_path):
    path = tmp_path / "run.jsonl"
    store = ResultStore(path)
    store.append(_record("k1"))
    store.append(_record("k2"))

    # simulate a crash mid-write: a truncated final line
    with open(path, "a") as f:
        f.write('{"trial_key": "k3", "run_id": "run-1", "mo')

    assert store.existing_keys() == {"k1", "k2"}
    assert [r["trial_key"] for r in store.load()] == ["k1", "k2"]


def test_corrupt_and_blank_lines_tolerated(tmp_path):
    path = tmp_path / "run.jsonl"
    store = ResultStore(path)
    store.append(_record("k1"))
    with open(path, "a") as f:
        f.write("\n")                      # blank line
        f.write("not json at all\n")       # garbage line
        f.write('{"no_trial_key": 1}\n')   # parseable but missing the key
    store.append(_record("k2"))

    assert store.existing_keys() == {"k1", "k2"}
    # raw load skips unparseable lines but keeps every valid JSON object
    raw = store.load(dedup=False)
    assert [r.get("trial_key") for r in raw] == ["k1", None, "k2"]
    # default (deduped) load drops the keyless record and keeps one per key
    loaded = store.load()
    assert sorted(r["trial_key"] for r in loaded) == ["k1", "k2"]


def test_load_records_multiple_files(tmp_path):
    p1, p2 = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    ResultStore(p1).append(_record("k1"))
    ResultStore(p2).append(_record("k2"))
    assert {r["trial_key"] for r in load_records([p1, p2])} == {"k1", "k2"}


def test_append_round_trips_full_record(tmp_path):
    path = tmp_path / "run.jsonl"
    store = ResultStore(path)
    store.append(_record("k1", Verdict.INVALID))
    raw = path.read_text().strip()
    rec = json.loads(raw)
    round_tripped = TrialRecord.model_validate(rec)
    assert round_tripped.trial_key == "k1"
    assert round_tripped.verdict == Verdict.INVALID
    assert round_tripped.fixed_existing is None


def test_append_after_torn_tail_heals_line(tmp_path):
    """A torn (newline-less) tail must not corrupt the next appended record."""
    from lgtm_bench.store import ResultStore
    from lgtm_bench.schema import TrialRecord, Verdict

    path = tmp_path / "r.jsonl"
    store = ResultStore(path)
    rec = TrialRecord(
        trial_key="k1", run_id="r", model="m", task_id="t", mode="generate",
        condition="none", variant_id="v", trial_index=0, prompt="p",
        raw_output="", extracted_code="", verdict=Verdict.INVALID)
    store.append(rec)
    # simulate crash mid-write: torn tail without newline
    with open(path, "a") as f:
        f.write('{"trial_key": "torn')
    rec2 = rec.model_copy(update={"trial_key": "k2"})
    store.append(rec2)
    keys = store.existing_keys()
    assert keys == {"k1", "k2"}
    assert len(store.load()) == 2


def test_regrade_in_place_preserves_records(tmp_path):
    """regrade(out_path == results_path) must not destroy the source."""
    import json
    from lgtm_bench.engine import regrade
    from lgtm_bench.store import ResultStore
    from lgtm_bench.schema import TrialRecord, Verdict

    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "t.yaml").write_text(
        "id: sql/t\ncategory: sql\ntitle: t\nconditions: [none]\n"
        "variants:\n  - id: v1\n    prompt: p\n")
    p = tmp_path / "r.jsonl"
    store = ResultStore(p)
    rec = TrialRecord(
        trial_key="k1", run_id="r", model="m", task_id="sql/t", mode="generate",
        condition="none", variant_id="v1", trial_index=0, prompt="p",
        raw_output="```python\nx = 1\n```", extracted_code="x = 1",
        verdict=Verdict.SECURE)
    store.append(rec)
    out = regrade(p, tasks_dir, out_path=p)
    lines = [json.loads(l) for l in open(out)]
    assert len(lines) == 1 and lines[0]["trial_key"] == "k1"


def test_completed_keys_excludes_errored_and_load_dedups(tmp_path):
    """Errored trials are not 'completed'; a later success supersedes them."""
    from lgtm_bench.store import ResultStore
    from lgtm_bench.schema import TrialRecord, Verdict

    path = tmp_path / "r.jsonl"
    store = ResultStore(path)
    base = dict(run_id="r", model="m", task_id="t", mode="generate",
                condition="none", variant_id="v", trial_index=0, prompt="p",
                raw_output="", extracted_code="")
    # first attempt: rate-limit error
    store.append(TrialRecord(trial_key="k1", verdict=Verdict.INVALID,
                             error="429 limit", **base))
    assert store.completed_keys() == set()          # not complete
    assert store.existing_keys() == {"k1"}          # but present
    # retry succeeds
    store.append(TrialRecord(trial_key="k1", verdict=Verdict.SECURE, **base))
    assert store.completed_keys() == {"k1"}
    loaded = store.load()
    assert len(loaded) == 1 and loaded[0]["verdict"] == "secure"  # success wins
    # a later error must NOT clobber the good record
    store.append(TrialRecord(trial_key="k1", verdict=Verdict.INVALID,
                             error="flaky", **base))
    loaded = store.load()
    assert len(loaded) == 1 and loaded[0]["verdict"] == "secure"
