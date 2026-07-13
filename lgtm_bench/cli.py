"""CLI entrypoints (TECH_SPEC §9): lgtm run | detect | report | validate."""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Optional

import typer

from .engine import RunConfig, execute_run, regrade
from .schema import Condition, Mode, TaskSpec, load_tasks
from .store import load_records

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


@app.command()
def run(
    models: str = typer.Option(..., help="comma-separated model ids"),
    tasks: Path = typer.Option(Path("tasks"), help="task YAML dir or file"),
    trials: int = typer.Option(5, help="trials per variant (K)"),
    conditions: str = typer.Option("none,clean-repo,dirty-repo"),
    out: Path = typer.Option(Path("results")),
    runner: str = typer.Option("claude-code", help="claude-code | mock"),
    concurrency: int = typer.Option(2),
    variants: Optional[str] = typer.Option(None, help="variant id filter (csv)"),
    task_filter: Optional[str] = typer.Option(None, help="csv of task-id substrings (OR)"),
    timeout: int = typer.Option(300, help="per-trial timeout (s)"),
    fixtures: Path = typer.Option(Path("fixtures")),
):
    cfg = RunConfig(
        models=_csv(models), tasks_root=tasks, out_dir=out,
        conditions=[Condition(c) for c in _csv(conditions)],
        trials=trials, runner_name=runner, concurrency=concurrency,
        variant_filter=_csv(variants) if variants else None,
        task_filter=_csv(task_filter) if task_filter else None,
        timeout_s=timeout, fixtures_root=fixtures,
        lexicon_dir=Path("rules/lexicons") if Path("rules/lexicons").exists() else None,
    )
    out_path = execute_run(cfg)
    typer.echo(f"results: {out_path}")


@app.command()
def detect(
    results: Path = typer.Argument(..., help="results JSONL to re-grade"),
    regrade_flag: bool = typer.Option(True, "--regrade/--no-regrade"),
    tasks: Path = typer.Option(Path("tasks")),
    out: Optional[Path] = typer.Option(None),
):
    if not regrade_flag:
        raise typer.BadParameter("only --regrade is supported")
    lex = Path("rules/lexicons")
    dest = regrade(results, tasks, out, lex if lex.exists() else None)
    typer.echo(f"re-graded: {dest}")


@app.command()
def evidence(
    results: list[Path] = typer.Argument(..., help="one or more results JSONL files"),
    out: Path = typer.Option(Path("evidence.md")),
    verdict: Optional[str] = typer.Option(None, help="filter: secure|vulnerable|invalid"),
    task_filter: Optional[str] = typer.Option(None, help="filter: task-id substring"),
    model: Optional[str] = typer.Option(None, help="filter: exact model id"),
):
    """Render a human-readable per-trial audit transcript (prompt, output,
    extracted code, scan findings, verdict) — the ground truth behind report."""
    from .evidence import build_evidence
    records = load_records(results)
    if not records:
        typer.echo("no records found", err=True)
        raise typer.Exit(1)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_evidence(records, verdict, task_filter, model))
    typer.echo(f"evidence: {out}")


@app.command()
def report(
    results: list[Path] = typer.Argument(..., help="one or more results JSONL files"),
    tasks: Path = typer.Option(Path("tasks")),
    out: Path = typer.Option(Path("report.md")),
):
    from .report import write_report
    records = load_records(results)
    if not records:
        typer.echo("no records found", err=True)
        raise typer.Exit(1)
    write_report(records, load_tasks(tasks), out)
    typer.echo(f"report: {out}")


# -- validate ----------------------------------------------------------------

def _py_functions(path: Path) -> dict[str, tuple]:
    """module-relative function signatures: name -> (args...)"""
    out: dict[str, tuple] = {}
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError as e:
        raise ValueError(f"{path}: fixture does not parse: {e}") from e
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = tuple(a.arg for a in node.args.args)
    return out


def _scan_fixture(root: Path) -> list:
    """All sql-pack findings across a fixture's python files (with the same
    AST-clears-semgrep suppression the grading pipeline uses)."""
    from .grading import _run_pack
    from .schema import ArtifactKind
    dummy = TaskSpec(id="fixture/scan", category="sql", title="scan",
                     conditions=[Condition.NONE],
                     artifact=ArtifactKind.FUNCTION,
                     variants=[{"id": "v", "prompt": "x"}])
    findings = []
    for py in sorted(root.rglob("*.py")):
        code = py.read_text()
        for f in _run_pack(code, dummy):
            findings.append((str(py.relative_to(root)), f))
    return findings


@app.command()
def validate(
    tasks: Path = typer.Option(Path("tasks")),
    fixtures: Path = typer.Option(Path("fixtures")),
):
    failures: list[str] = []
    loaded = []
    try:
        loaded = load_tasks(tasks)
        typer.echo(f"tasks: {len(loaded)} OK")
    except Exception as e:
        failures.append(f"task schema: {e}")

    clean, dirty = fixtures / "flaskapp-clean", fixtures / "flaskapp-dirty"
    if clean.exists() and dirty.exists():
        c_files = {str(p.relative_to(clean)) for p in clean.rglob("*") if p.is_file()}
        d_files = {str(p.relative_to(dirty)) for p in dirty.rglob("*") if p.is_file()}
        if c_files != d_files:
            failures.append(f"fixture file sets differ: {c_files ^ d_files}")
        for rel in sorted(c_files & d_files):
            if rel.endswith(".py"):
                cf, df = _py_functions(clean / rel), _py_functions(dirty / rel)
                if set(cf) != set(df):
                    failures.append(f"{rel}: function sets differ: {set(cf) ^ set(df)}")
                else:
                    for name in cf:
                        if cf[name] != df[name]:
                            failures.append(f"{rel}::{name}: signatures differ")
        clean_findings = _scan_fixture(clean)
        if clean_findings:
            failures.append(
                "clean fixture has findings: "
                + ", ".join(f"{f0}:{f1.rule_id}" for f0, f1 in clean_findings[:5]))
        dirty_findings = _scan_fixture(dirty)
        if not dirty_findings:
            failures.append("dirty fixture has NO findings — pair is not a contrast")
        # every edit-task target must be vulnerable in the dirty fixture
        dirty_hit_files = {f0 for f0, _ in dirty_findings}
        for t in loaded:
            if t.mode == Mode.EDIT:
                for root, label in ((clean, "clean"), (dirty, "dirty")):
                    tf = root / (t.target_file or "")
                    if not tf.exists():
                        failures.append(f"{t.id}: target file missing in {label}: {t.target_file}")
                    elif t.target_function not in _py_functions(tf):
                        failures.append(f"{t.id}: target function missing in {label}")
                if t.target_file and t.target_file not in dirty_hit_files:
                    failures.append(
                        f"{t.id}: dirty target {t.target_file} has no findings — "
                        "fixed_existing would be meaningless")
        typer.echo(f"fixtures: {len(c_files)} files, "
                   f"{len(dirty_findings)} dirty findings, "
                   f"{len(clean_findings)} clean findings")
    else:
        typer.echo("fixtures: not present (skipping pair check)")

    if failures:
        for f in failures:
            typer.echo(f"FAIL: {f}", err=True)
        raise typer.Exit(1)
    typer.echo("validate: OK")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
