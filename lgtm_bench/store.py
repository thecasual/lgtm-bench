"""JSONL result store with resumability (TECH_SPEC §3.2)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .schema import TrialRecord


class ResultStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def existing_keys(self) -> set[str]:
        """All trial_keys present in the file (successful or not)."""
        keys: set[str] = set()
        if not self.path.exists():
            return keys
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    keys.add(json.loads(line)["trial_key"])
                except (json.JSONDecodeError, KeyError):
                    continue  # tolerate a torn tail line from a crash
        return keys

    def completed_keys(self) -> set[str]:
        """trial_keys with at least one error-free record — the ones resume
        should skip. A trial whose only record carries a runner error (e.g. a
        rate-limit 429) is NOT complete and will be retried."""
        good: set[str] = set()
        bad: set[str] = set()
        if not self.path.exists():
            return good
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    key = rec["trial_key"]
                except (json.JSONDecodeError, KeyError):
                    continue
                if rec.get("error"):
                    bad.add(key)
                else:
                    good.add(key)
        return good

    def append(self, record: TrialRecord) -> None:
        # A crash can leave a torn final line with no trailing newline;
        # appending straight onto it would corrupt both records. Heal first.
        needs_newline = False
        if self.path.exists() and self.path.stat().st_size > 0:
            with open(self.path, "rb") as rf:
                rf.seek(-1, os.SEEK_END)
                needs_newline = rf.read(1) != b"\n"
        with open(self.path, "a") as f:
            if needs_newline:
                f.write("\n")
            f.write(record.model_dump_json() + "\n")
            f.flush()
            os.fsync(f.fileno())

    def load(self, dedup: bool = True) -> list[dict]:
        """Load records. With dedup (default), a trial_key that appears more
        than once — a retried trial whose earlier attempt errored — keeps only
        the LAST occurrence, and a later successful record wins over an earlier
        errored one."""
        records: list[dict] = []
        if not self.path.exists():
            return records
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        if not dedup:
            return records
        latest: dict[str, dict] = {}
        for rec in records:
            key = rec.get("trial_key")
            if key is None:
                continue
            prev = latest.get(key)
            # last write wins, but never let an errored retry clobber a good one
            if prev is not None and prev.get("error") is None and rec.get("error"):
                continue
            latest[key] = rec
        return list(latest.values())


def _is_regraded_path(path: Path) -> bool:
    """A *.regraded.jsonl file carries current-detector verdicts; a raw
    run-*.jsonl carries whatever verdicts the run was written with."""
    return path.name.endswith(".regraded.jsonl")


def load_records(paths: list[Path]) -> list[dict]:
    """Load and concatenate records from several result files, deduping on
    trial_key ACROSS files.

    The documented publish flow leaves run-X.jsonl and run-X.regraded.jsonl
    side by side, and a report glob matches both; concatenating blindly would
    double-count every trial and fold stale pre-regrade verdicts back in. Glob
    order is OS-arbitrary, so we cannot rely on last-wins. When the same
    trial_key appears more than once we keep exactly one record by a
    DETERMINISTIC priority:
      1. a non-error record beats an error record (same rule ResultStore.load
         applies within a single file);
      2. otherwise a record from a *.regraded.jsonl path beats one from a raw
         .jsonl (the regraded verdict is the current one);
      3. otherwise the record later in input order wins (documented tiebreak).
    These three keys compare lexicographically, so a single max() over
    (non_error, regraded, input_index) implements the full priority.
    """
    # Load each file's already-in-file-deduped records, tagging every record
    # with its source path and a global input index for the order tiebreak.
    tagged: list[tuple[dict, Path, int]] = []
    for p in paths:
        path = Path(p)
        for rec in ResultStore(path).load():
            tagged.append((rec, path, len(tagged)))

    def _priority(item: tuple[dict, Path, int]) -> tuple[int, int, int]:
        rec, path, idx = item
        non_error = 0 if rec.get("error") else 1
        regraded = 1 if _is_regraded_path(path) else 0
        return (non_error, regraded, idx)

    best: dict[str, tuple[dict, Path, int]] = {}
    for item in tagged:
        rec, _path, _idx = item
        key = rec.get("trial_key")
        if key is None:
            # A per-file load with dedup already drops keyless records, so this
            # is defensive; a keyless record cannot participate in dedup.
            continue
        prev = best.get(key)
        if prev is None or _priority(item) > _priority(prev):
            best[key] = item

    # If dedup actually removed anything, print ONE stderr summary line that
    # attributes the dropped records to the source file each came from.
    kept_idx = {idx for (_r, _p, idx) in best.values()}
    dropped_by_file: dict[str, int] = {}
    for rec, path, idx in tagged:
        if rec.get("trial_key") is not None and idx not in kept_idx:
            dropped_by_file[str(path)] = dropped_by_file.get(str(path), 0) + 1
    if dropped_by_file:
        total = sum(dropped_by_file.values())
        detail = ", ".join(f"{f}: {n}" for f, n in sorted(dropped_by_file.items()))
        print(f"[lgtm] load_records: dropped {total} duplicate trial record(s) "
              f"across files ({detail})", file=sys.stderr)

    # Return in stable input order (by the chosen record's index) so callers see
    # a deterministic sequence regardless of the arbitrary glob order.
    return [rec for (rec, _p, _idx) in sorted(best.values(), key=lambda it: it[2])]
