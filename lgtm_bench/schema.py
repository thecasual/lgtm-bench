"""Task YAML and trial-record models (TECH_SPEC §2-§4)."""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class Condition(str, Enum):
    NONE = "none"
    CLEAN = "clean-repo"
    DIRTY = "dirty-repo"


class Mode(str, Enum):
    GENERATE = "generate"
    EDIT = "edit"


class ArtifactKind(str, Enum):
    FUNCTION = "function"
    RAW_SQL = "raw-sql"
    ENDPOINT = "endpoint"


class Verdict(str, Enum):
    SECURE = "secure"
    VULNERABLE = "vulnerable"
    INVALID = "invalid"


class Variant(BaseModel):
    id: str
    prompt: str
    safety_hint: bool = False


class DetectorRef(BaseModel):
    pack: str


class TaskSpec(BaseModel):
    id: str
    category: str
    mode: Mode = Mode.GENERATE
    title: str
    language: str = "python"
    dialect: str = "sqlite"
    artifact: ArtifactKind = ArtifactKind.FUNCTION
    conditions: list[Condition]
    target: Optional[str] = None  # edit mode: "relative/path.py::function_name"
    variants: list[Variant]
    detectors: list[DetectorRef] = Field(default_factory=lambda: [DetectorRef(pack="sql")])

    @field_validator("variants")
    @classmethod
    def _unique_variant_ids(cls, v: list[Variant]) -> list[Variant]:
        ids = [x.id for x in v]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate variant ids: {ids}")
        if not ids:
            raise ValueError("task must define at least one variant")
        return v

    @model_validator(mode="after")
    def _edit_mode_rules(self) -> "TaskSpec":
        if self.mode == Mode.EDIT:
            if not self.target or "::" not in self.target:
                raise ValueError("edit task requires target 'path.py::function_name'")
            if Condition.NONE in self.conditions:
                raise ValueError("edit tasks cannot run under condition 'none'")
        return self

    @property
    def packs(self) -> list[str]:
        return [d.pack for d in self.detectors]

    @property
    def target_file(self) -> Optional[str]:
        return self.target.split("::")[0] if self.target else None

    @property
    def target_function(self) -> Optional[str]:
        return self.target.split("::")[1] if self.target else None


class Finding(BaseModel):
    detector: str
    rule_id: str
    message: str
    line: Optional[int] = None
    snippet: Optional[str] = None


class TrialRecord(BaseModel):
    trial_key: str
    run_id: str
    model: str
    task_id: str
    mode: Mode
    language: str = "python"
    condition: Condition
    variant_id: str
    trial_index: int
    prompt: str
    raw_output: str
    extracted_code: str
    verdict: Verdict
    fixed_existing: Optional[bool] = None
    flagged_existing: Optional[bool] = None
    findings: list[Finding] = Field(default_factory=list)
    timing_ms: int = 0
    error: Optional[str] = None
    harness_version: str = ""
    detector_pack_version: str = ""
    runner: str = "claude-code"
    fixture_version: Optional[str] = None


def load_task(path: Path) -> TaskSpec:
    with open(path) as f:
        data = yaml.safe_load(f)
    try:
        return TaskSpec.model_validate(data)
    except Exception as e:
        raise ValueError(f"{path}: {e}") from e


def load_tasks(root: Path) -> list[TaskSpec]:
    """Load all task YAMLs under a directory (or a single file)."""
    if root.is_file():
        return [load_task(root)]
    tasks = [load_task(p) for p in sorted(root.rglob("*.yaml"))]
    ids = [t.id for t in tasks]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise ValueError(f"duplicate task ids: {dupes}")
    return tasks


def run_config_hash(models: list[str], task_ids: list[str], conditions: list[str],
                    trials: int, harness_version: str) -> str:
    payload = json.dumps(
        {"models": sorted(models), "tasks": sorted(task_ids),
         "conditions": sorted(conditions), "trials": trials, "hv": harness_version},
        sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def trial_key(cfg_hash: str, model: str, task_id: str, condition: str,
              variant_id: str, trial_index: int) -> str:
    return "|".join([cfg_hash, model, task_id, condition, variant_id, str(trial_index)])
