"""Cross-file dedup in load_records (store.py).

The publish flow leaves run-X.jsonl and run-X.regraded.jsonl side by side, and
a report glob matches both. load_records must keep exactly one record per
trial_key with a deterministic priority: non-error beats error, then regraded
path beats raw path, then later input order wins.
"""
from __future__ import annotations

import json

from lgtm_bench.schema import Condition, Mode, TrialRecord, Verdict
from lgtm_bench.store import ResultStore, load_records


def _record(key: str, verdict: Verdict = Verdict.SECURE,
            error: str | None = None,
            detector_pack_version: str = "") -> TrialRecord:
    return TrialRecord(
        trial_key=key, run_id="run-1", model="mock-model",
        task_id="sql/unit-case", mode=Mode.GENERATE, condition=Condition.NONE,
        variant_id="v1", trial_index=0, prompt="p", raw_output="out",
        extracted_code="code", verdict=verdict, error=error,
        detector_pack_version=detector_pack_version)


def test_regraded_wins_over_raw_for_same_key(tmp_path):
    """Same trial_key in run-X.jsonl and run-X.regraded.jsonl: the regraded
    verdict is the one kept, and the trial is counted exactly once."""
    raw = tmp_path / "run-abc.jsonl"
    regraded = tmp_path / "run-abc.regraded.jsonl"
    ResultStore(raw).append(
        _record("k1", Verdict.SECURE, detector_pack_version="0.1.0"))
    ResultStore(regraded).append(
        _record("k1", Verdict.VULNERABLE, detector_pack_version="0.3.0"))

    # Pass raw first (regraded is not merely last-in-order); priority must still
    # pick the regraded record deterministically.
    out = load_records([raw, regraded])
    assert len(out) == 1
    assert out[0]["verdict"] == "vulnerable"
    assert out[0]["detector_pack_version"] == "0.3.0"

    # Order of paths must not change the winner (glob order is OS-arbitrary).
    out_rev = load_records([regraded, raw])
    assert len(out_rev) == 1
    assert out_rev[0]["verdict"] == "vulnerable"


def test_non_error_beats_error_across_files(tmp_path):
    """A non-error record beats an error record regardless of which file (raw
    or regraded) it came from."""
    raw = tmp_path / "run-abc.jsonl"
    regraded = tmp_path / "run-abc.regraded.jsonl"
    # The error record lives in the regraded file, the good one in raw; rule 1
    # (non-error beats error) dominates rule 2 (regraded beats raw).
    ResultStore(regraded).append(_record("k1", Verdict.INVALID, error="429"))
    ResultStore(raw).append(_record("k1", Verdict.SECURE))

    out = load_records([raw, regraded])
    assert len(out) == 1
    assert out[0]["error"] is None
    assert out[0]["verdict"] == "secure"


def test_later_input_order_breaks_tie(tmp_path):
    """Two raw files, both non-error, same key: later-in-input-order wins."""
    a = tmp_path / "run-a.jsonl"
    b = tmp_path / "run-b.jsonl"
    ResultStore(a).append(_record("k1", Verdict.SECURE))
    ResultStore(b).append(_record("k1", Verdict.VULNERABLE))
    # b is later in input order -> its record wins.
    out = load_records([a, b])
    assert len(out) == 1 and out[0]["verdict"] == "vulnerable"
    # reverse the order -> a now wins
    out_rev = load_records([b, a])
    assert len(out_rev) == 1 and out_rev[0]["verdict"] == "secure"


def test_distinct_keys_all_kept(tmp_path):
    a = tmp_path / "run-a.jsonl"
    b = tmp_path / "run-b.jsonl"
    ResultStore(a).append(_record("k1"))
    ResultStore(b).append(_record("k2"))
    out = load_records([a, b])
    assert {r["trial_key"] for r in out} == {"k1", "k2"}


def test_drop_summary_printed_once_to_stderr(tmp_path, capsys):
    """When dedup drops records, exactly one stderr summary line with a count
    and per-source-file attribution is printed."""
    raw = tmp_path / "run-abc.jsonl"
    regraded = tmp_path / "run-abc.regraded.jsonl"
    ResultStore(raw).append(_record("k1"))
    ResultStore(raw).append(_record("k2"))
    ResultStore(regraded).append(_record("k1", Verdict.VULNERABLE))
    ResultStore(regraded).append(_record("k2", Verdict.VULNERABLE))

    load_records([raw, regraded])
    err = capsys.readouterr().err
    summary_lines = [ln for ln in err.splitlines() if "load_records" in ln]
    assert len(summary_lines) == 1
    line = summary_lines[0]
    assert "dropped 2" in line
    # the raw file lost both of its records (regraded won each key)
    assert str(raw) in line


def test_no_summary_when_nothing_dropped(tmp_path, capsys):
    a = tmp_path / "run-a.jsonl"
    ResultStore(a).append(_record("k1"))
    ResultStore(a).append(_record("k2"))
    load_records([a])
    err = capsys.readouterr().err
    assert "load_records" not in err


def test_return_shape_is_list_of_dict(tmp_path):
    a = tmp_path / "run-a.jsonl"
    ResultStore(a).append(_record("k1"))
    out = load_records([a])
    assert isinstance(out, list)
    assert all(isinstance(r, dict) for r in out)
    # round-trips through json (plain dicts, not models)
    json.dumps(out)
