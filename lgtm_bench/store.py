"""JSONL result store with resumability (TECH_SPEC §3.2)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .schema import TrialRecord


class ResultStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def existing_keys(self) -> set[str]:
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

    def load(self) -> list[dict]:
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
        return records


def load_records(paths: list[Path]) -> list[dict]:
    out: list[dict] = []
    for p in paths:
        out.extend(ResultStore(p).load())
    return out
