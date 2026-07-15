"""Crash-safety and unmapped-task handling for engine.regrade().

regrade() now builds its output in a temp file and os.replace()s it into place
only after the loop completes, so a mid-loop crash leaves the original (which,
for an in-place *.regraded.jsonl regrade, is the ONLY copy of the raw outputs)
byte-identical. It also treats a record missing its task_id key as unmapped
(pass-through + warn) instead of crashing on a bare subscript.
"""
from __future__ import annotations

import json

import pytest

from lgtm_bench import engine
from lgtm_bench.engine import regrade
from lgtm_bench.schema import TrialRecord, Verdict
from lgtm_bench.store import ResultStore


def _tasks_dir(tmp_path):
    d = tmp_path / "tasks"
    d.mkdir()
    (d / "t.yaml").write_text(
        "id: sql/t\ncategory: sql\ntitle: t\nconditions: [none]\n"
        "variants:\n  - id: v1\n    prompt: p\n")
    return d


def _rec(key: str, task_id: str = "sql/t") -> TrialRecord:
    return TrialRecord(
        trial_key=key, run_id="r", model="m", task_id=task_id, mode="generate",
        condition="none", variant_id="v1", trial_index=0, prompt="p",
        raw_output="```python\nx = 1\n```", extracted_code="x = 1",
        verdict=Verdict.SECURE)


def test_missing_task_id_key_passes_through_and_warns(tmp_path, capsys):
    """(a) An in-place regrade of a file with a record missing the task_id key
    completes, keeps every record, and warns about the unmapped trial."""
    tasks_dir = _tasks_dir(tmp_path)
    p = tmp_path / "r.regraded.jsonl"

    # A normal, regradable record...
    good = json.loads(_rec("k1").model_dump_json())
    # ...and a record with NO task_id key at all (would crash a bare subscript).
    broken = json.loads(_rec("k2").model_dump_json())
    broken.pop("task_id")
    p.write_text(json.dumps(good) + "\n" + json.dumps(broken) + "\n")

    out = regrade(p, tasks_dir, out_path=p)
    assert out == p

    lines = [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]
    keys = {ln["trial_key"] for ln in lines}
    assert keys == {"k1", "k2"}          # both records preserved
    # the broken record survived verbatim, still without a task_id
    broken_out = next(ln for ln in lines if ln["trial_key"] == "k2")
    assert "task_id" not in broken_out

    err = capsys.readouterr().err
    assert "WARNING" in err
    assert "STALE" in err
    assert "missing task_id" in err


def test_midloop_crash_leaves_original_byte_identical(tmp_path, monkeypatch):
    """(b) A mid-loop exception (grade raises on record 2) must leave the
    in-place source file byte-for-byte unchanged, with no raw outputs lost."""
    tasks_dir = _tasks_dir(tmp_path)
    p = tmp_path / "r.regraded.jsonl"
    store = ResultStore(p)
    for i in range(4):
        store.append(_rec(f"k{i}"))

    original_bytes = p.read_bytes()
    assert original_bytes.count(b"\n") == 4  # sanity: 4 records present

    calls = {"n": 0}

    def _boom(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("simulated disk full mid-loop")
        # first call would normally grade; return via the real grader
        return _real_grade(*args, **kwargs)

    _real_grade = engine.grade
    monkeypatch.setattr(engine, "grade", _boom)

    with pytest.raises(RuntimeError, match="simulated disk full"):
        regrade(p, tasks_dir, out_path=p)

    # The original file is untouched: same bytes, all 4 records with raw_output.
    assert p.read_bytes() == original_bytes
    lines = [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]
    assert len(lines) == 4
    assert all(ln["raw_output"] for ln in lines)

    # No stray temp file left behind in the directory.
    leftovers = list(tmp_path.glob("*.regrade.tmp"))
    assert leftovers == []


def test_unmapped_task_id_warns_but_regrades_the_rest(tmp_path, capsys):
    """A record whose task_id is simply not in the loaded task set passes
    through with a loud warning; mapped records are still regraded."""
    tasks_dir = _tasks_dir(tmp_path)
    p = tmp_path / "run.jsonl"
    store = ResultStore(p)
    store.append(_rec("k1", task_id="sql/t"))          # mapped
    store.append(_rec("k2", task_id="sql/does-not-exist"))  # unmapped

    out = regrade(p, tasks_dir)  # writes run.regraded.jsonl beside source
    lines = [json.loads(ln) for ln in out.read_text().splitlines() if ln.strip()]
    assert {ln["trial_key"] for ln in lines} == {"k1", "k2"}

    err = capsys.readouterr().err
    assert "WARNING" in err
    assert "sql/does-not-exist" in err
