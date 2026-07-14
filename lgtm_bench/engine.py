"""Run orchestration: grid enumeration, workdir prep, bounded concurrency,
resumable JSONL persistence (TECH_SPEC §3)."""
from __future__ import annotations

import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import HARNESS_VERSION
from .grading import grade
from .runner import get_runner
from .schema import (Condition, Mode, TaskSpec, TrialRecord, Variant,
                     load_tasks, run_config_hash, trial_key)
from .store import ResultStore

REPO_PREAMBLE = (
    "You are working in the repository at your current working directory — "
    "explore it and follow its conventions.\n\n")
GENERATE_SUFFIX = (
    "\n\nReply with the complete new code in a fenced code block; "
    "do not modify any files.")
EDIT_SUFFIX = (
    "\n\nReply with the complete updated function in a fenced code block; "
    "do not modify any files.")

FIXTURES = {
    Condition.CLEAN: "flaskapp-clean",
    Condition.DIRTY: "flaskapp-dirty",
}

# Repo-condition fixtures are language-specific. A task in language X under a
# clean/dirty condition uses fixtures/<mapped>; python keeps the flaskapp
# fixtures unchanged.
FIXTURES_BY_LANG = {
    "python": {Condition.CLEAN: "flaskapp-clean", Condition.DIRTY: "flaskapp-dirty"},
    "go": {Condition.CLEAN: "go-clean", Condition.DIRTY: "go-dirty"},
    "rust": {Condition.CLEAN: "rust-clean", Condition.DIRTY: "rust-dirty"},
}


def _fixture_name(language: str, condition: Condition) -> str:
    return FIXTURES_BY_LANG.get(language, FIXTURES_BY_LANG["python"])[condition]


@dataclass
class RunConfig:
    models: list[str]
    tasks_root: Path
    out_dir: Path
    conditions: list[Condition] = field(
        default_factory=lambda: [Condition.NONE, Condition.CLEAN, Condition.DIRTY])
    trials: int = 5
    runner_name: str = "claude-code"
    concurrency: int = 2
    variant_filter: Optional[list[str]] = None
    task_filter: Optional[list[str]] = None  # OR of substring matches on task id
    timeout_s: int = 300
    run_id: str = ""
    fixtures_root: Path = Path("fixtures")
    lexicon_dir: Optional[Path] = None
    max_tokens: Optional[int] = None   # ollama num_predict cap
    no_think: bool = False             # ollama think:false (reasoning models)


@dataclass
class TrialSpec:
    key: str
    model: str
    task: TaskSpec
    condition: Condition
    variant: Variant
    trial_index: int


def build_grid(tasks: list[TaskSpec], cfg: RunConfig, cfg_hash: str) -> list[TrialSpec]:
    grid: list[TrialSpec] = []
    for model in cfg.models:
        for task in tasks:
            if cfg.task_filter and not any(s in task.id for s in cfg.task_filter):
                continue
            conds = [c for c in task.conditions if c in cfg.conditions]
            for condition in conds:
                for variant in task.variants:
                    if cfg.variant_filter and variant.id not in cfg.variant_filter:
                        continue
                    for i in range(cfg.trials):
                        grid.append(TrialSpec(
                            key=trial_key(cfg_hash, model, task.id,
                                          condition.value, variant.id, i),
                            model=model, task=task, condition=condition,
                            variant=variant, trial_index=i))
    return grid


def assemble_prompt(task: TaskSpec, variant: Variant, condition: Condition) -> str:
    if condition == Condition.NONE:
        return variant.prompt.strip()
    suffix = EDIT_SUFFIX if task.mode == Mode.EDIT else GENERATE_SUFFIX
    return REPO_PREAMBLE + variant.prompt.strip() + suffix


def _prepare_workdir(spec: TrialSpec, cfg: RunConfig) -> Path:
    base = Path(tempfile.mkdtemp(prefix="lgtm-trial-"))
    if spec.condition == Condition.NONE:
        return base
    fixture = cfg.fixtures_root / _fixture_name(spec.task.language, spec.condition)
    if not fixture.exists():
        raise FileNotFoundError(f"fixture repo missing: {fixture}")
    dest = base / "repo"
    shutil.copytree(fixture, dest)
    return dest


def _fixture_version(cfg: RunConfig) -> Optional[str]:
    vf = cfg.fixtures_root / "VERSION"
    return vf.read_text().strip() if vf.exists() else None


def run_trial(spec: TrialSpec, cfg: RunConfig, runner, fixture_version) -> TrialRecord:
    prompt = assemble_prompt(spec.task, spec.variant, spec.condition)
    workdir = _prepare_workdir(spec, cfg)
    try:
        gen = runner.generate(spec.model, prompt, spec.condition, workdir)
    finally:
        root = workdir if spec.condition == Condition.NONE else workdir.parent
        shutil.rmtree(root, ignore_errors=True)

    if gen.error is not None:
        from .schema import Verdict
        return TrialRecord(
            trial_key=spec.key, run_id=cfg.run_id, model=spec.model,
            task_id=spec.task.id, mode=spec.task.mode,
            language=spec.task.language, condition=spec.condition,
            variant_id=spec.variant.id, trial_index=spec.trial_index,
            prompt=prompt, raw_output="", extracted_code="",
            verdict=Verdict.INVALID, error=gen.error,
            timing_ms=gen.duration_ms, harness_version=HARNESS_VERSION,
            runner=cfg.runner_name, fixture_version=fixture_version)

    g = grade(spec.task, gen.raw_output, spec.condition, cfg.lexicon_dir)
    return TrialRecord(
        trial_key=spec.key, run_id=cfg.run_id, model=spec.model,
        task_id=spec.task.id, mode=spec.task.mode,
        language=spec.task.language, condition=spec.condition,
        variant_id=spec.variant.id, trial_index=spec.trial_index,
        prompt=prompt, raw_output=gen.raw_output, extracted_code=g.extracted_code,
        verdict=g.verdict, findings=g.findings,
        fixed_existing=g.fixed_existing, flagged_existing=g.flagged_existing,
        timing_ms=gen.duration_ms, harness_version=HARNESS_VERSION,
        detector_pack_version=g.detector_pack_version,
        runner=cfg.runner_name, fixture_version=fixture_version)


def execute_run(cfg: RunConfig) -> Path:
    tasks = load_tasks(cfg.tasks_root)
    if not cfg.run_id:
        cfg.run_id = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    cfg_hash = run_config_hash(cfg.models, [t.id for t in tasks],
                               [c.value for c in cfg.conditions],
                               cfg.trials, HARNESS_VERSION)
    out_path = cfg.out_dir / f"run-{cfg_hash}.jsonl"
    store = ResultStore(out_path)
    done = store.completed_keys()  # errored trials are retried on resume

    grid = build_grid(tasks, cfg, cfg_hash)
    todo = [s for s in grid if s.key not in done]
    print(f"[lgtm] grid={len(grid)} trials, done={len(grid) - len(todo)}, "
          f"todo={len(todo)}, out={out_path}", file=sys.stderr)

    runner = get_runner(cfg.runner_name)
    if hasattr(runner, "timeout_s"):
        runner.timeout_s = cfg.timeout_s
    if cfg.max_tokens is not None and hasattr(runner, "max_tokens"):
        runner.max_tokens = cfg.max_tokens
    if cfg.no_think and hasattr(runner, "no_think"):
        runner.no_think = True
    fixture_version = _fixture_version(cfg)

    completed = 0
    with ThreadPoolExecutor(max_workers=cfg.concurrency) as pool:
        futures = {pool.submit(run_trial, s, cfg, runner, fixture_version): s
                   for s in todo}
        for fut in as_completed(futures):
            spec = futures[fut]
            try:
                record = fut.result()
            except Exception as e:  # keep the run alive; record the failure
                from .schema import Verdict
                record = TrialRecord(
                    trial_key=spec.key, run_id=cfg.run_id, model=spec.model,
                    task_id=spec.task.id, mode=spec.task.mode,
                    language=spec.task.language, condition=spec.condition,
                    variant_id=spec.variant.id,
                    trial_index=spec.trial_index, prompt="", raw_output="",
                    extracted_code="", verdict=Verdict.INVALID,
                    error=f"harness: {e!r}", harness_version=HARNESS_VERSION,
                    runner=cfg.runner_name, fixture_version=fixture_version)
            store.append(record)
            completed += 1
            print(f"[lgtm] {completed}/{len(todo)} {record.model} "
                  f"{record.task_id} {record.condition.value} "
                  f"{record.variant_id}#{record.trial_index} -> "
                  f"{record.verdict.value}"
                  + (f" ({record.error[:60]})" if record.error else ""),
                  file=sys.stderr, flush=True)
    return out_path


def regrade(results_path: Path, tasks_root: Path, out_path: Optional[Path] = None,
            lexicon_dir: Optional[Path] = None) -> Path:
    """Re-grade stored raw outputs with current detectors (§9), no model calls."""
    tasks = {t.id: t for t in load_tasks(tasks_root)}
    src = ResultStore(results_path)
    dest_path = out_path or results_path.with_suffix(".regraded.jsonl")
    # Read everything BEFORE touching dest: with dest == source, unlinking
    # first would destroy the run's raw outputs irrecoverably. Dedup so a
    # retried trial's successful record supersedes its earlier error row.
    records = src.load(dedup=True)
    if not records and results_path.resolve() == dest_path.resolve():
        raise ValueError(f"refusing in-place regrade of unreadable/empty {results_path}")
    if dest_path.exists():
        dest_path.unlink()
    dest = ResultStore(dest_path)
    for rec in records:
        task = tasks.get(rec["task_id"])
        record = TrialRecord.model_validate(rec)
        if task is None or record.error is not None:
            dest.append(record)
            continue
        g = grade(task, record.raw_output, record.condition, lexicon_dir)
        record.verdict = g.verdict
        record.findings = g.findings
        record.extracted_code = g.extracted_code
        record.fixed_existing = g.fixed_existing
        record.flagged_existing = g.flagged_existing
        record.detector_pack_version = g.detector_pack_version
        dest.append(record)
    return dest_path
