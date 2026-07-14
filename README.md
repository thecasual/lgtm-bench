# lgtm-bench

A benchmark for measuring **how often LLMs introduce security vulnerabilities when handling
ordinary developer requests** — the code that "looks good to me" in review but carries a
latent bug.

lgtm-bench measures five things:

1. **Vulnerability introduction rate** — asked a benign question ("write a function that
   fetches a user by email"), how often does the model produce vulnerable code?
2. **Sensitivity & reproducibility** — how much does that rate change across paraphrasings
   of the same request, and across repeated runs of the identical prompt?
3. **Context contamination** — does the model get worse when the repo it works in already
   contains insecure code?
4. **Remediation behavior** — when editing existing vulnerable code for an unrelated reason,
   does the model silently fix the issue, flag it, ignore it, or make it worse?
5. **Model-generation gap** — are these rates a property of LLMs in general, or only of the
   newest frontier models? (frontier vs. older vs. open-weight)

The end deliverable is a data-backed **"State of Vibe Coding"** write-up testing six
pre-registered hypotheses: three vulnerability classes modern models may have effectively
*eradicated* (SQL injection, weak password hashing, unsafe deserialization) and three they
plausibly still *introduce* (insecure randomness for secrets, path traversal, command
injection).

The first vertical is **SQL query generation / SQL injection** (Python + sqlite/psycopg).
Detection is fully static (Semgrep + AST/sqlglot) — deterministic and free to run. Model
calls ride an Anthropic subscription via Claude Code headless mode.

The models in the published run: **`claude-fable-5`** (a fast Claude model — the smaller
sibling in this generation, used here as the frugal default), **`claude-opus-4-8`** and
**`claude-opus-4-1`** (frontier), **`claude-sonnet-5`** and **`claude-sonnet-4-5`**
(mid-tier, current and prior generation), **`claude-haiku-4-5`** (small/fast).

**Read next:**
- [docs/poc-report.md](docs/poc-report.md) — the benchmark report (findings, tables, limitations)
- [docs/METHODOLOGY.md](docs/METHODOLOGY.md) — how verdicts are decided and how the grader was validated
- [docs/REPRODUCE.md](docs/REPRODUCE.md) — reproduce the report from scratch, plus a glossary
- [docs/TECH_SPEC.md](docs/TECH_SPEC.md) — the full design
- [docs/poc-evidence.md](docs/poc-evidence.md) — every trial: prompt → output → findings → verdict

## Quick start

```bash
pip install -e .            # python 3.11+
# optional but recommended (second detector): pip install semgrep
lgtm validate               # check tasks + fixture pair integrity
python -m pytest tests/ -q  # detector corpus must pass 100%
```

The default runner shells out to **Claude Code headless** (`claude -p`), so model calls ride
your existing Claude subscription — install and log in to the `claude` CLI first. No API key
is used or needed.

### Run a benchmark

```bash
# Smallest meaningful run: one model, bare-prompt condition, 2 trials/variant
lgtm run --models claude-haiku-4-5 --conditions none --trials 2 --out results

# Compare models: comma-separated model ids (anything your `claude` CLI accepts)
lgtm run --models claude-fable-5,claude-sonnet-5,claude-sonnet-4-5,claude-haiku-4-5 \
         --conditions none --trials 2 --out results

# Repo conditions (clean vs contaminated fixture) and edit tasks
lgtm run --models claude-sonnet-5 --conditions clean-repo,dirty-repo --trials 2 --out results

# Slice the grid: --task-filter (csv of id substrings) and --variants (csv of variant ids)
lgtm run --models claude-sonnet-5 --conditions none \
         --task-filter user-lookup,order-by --variants v1-plain,v4-speed-pressure \
         --trials 3 --out results

# The full three-stage PoC run used for the initial report:
./scripts/run_poc.sh
```

### Open-source models (Ollama) and other languages

Claude models ride the subscription. Open-weight models run through an Ollama host you
point at with `INFERENCE_HOST` (`user@host`, `host`, `host:port`, or a full URL):

```bash
INFERENCE_HOST=you@your-box.ts.net \
lgtm run --runner ollama --models llama3.2:3b,qwen3:8b --conditions none --trials 2 --out results
# reasoning/verbose models: --no-think --max-tokens 400 cut wasted tokens hard
```

The Ollama runner is `--conditions none` only (a raw model API has no filesystem, so it
can't work inside a repo). Beyond Python, there are Go and Rust SQL task packs
(`--task-filter sql-go` / `sql-rust`). The Go/Rust detectors are Semgrep-rule v0.1 and
pattern-based (no taint analysis yet), so treat their rates as directional, not settled —
[docs/poc-report.md](docs/poc-report.md) says exactly why. Adding a model or a language never
requires regenerating existing results; the report is a pure function of the JSONL. Full
runbook: [docs/EXTENDING.md](docs/EXTENDING.md).

Runs are **resumable**: re-running the same command skips completed trials (results append
to `results/run-<config-hash>.jsonl`). Useful flags: `--concurrency N` (default 2),
`--timeout S` per trial, `--runner mock` for an offline dry run of the whole pipeline.

### Grade and report

```bash
lgtm report results/*.jsonl --out report.md   # leaderboard, deltas, CIs, examples
lgtm detect results/run-….jsonl               # re-grade stored outputs after a detector
                                              # upgrade — no model calls, no re-spend
```

### Audit the results yourself

Every number in the report traces back to per-trial records. To read the full
evidence — the exact prompt, the raw model output, the code the harness
extracted, each scan finding, and the verdict:

```bash
lgtm evidence results/*.jsonl --out evidence.md                 # every trial
lgtm evidence results/*.jsonl --verdict vulnerable --out v.md   # just the flagged ones
lgtm evidence results/*.jsonl --task-filter order-by --model claude-sonnet-5
```

Rendered snapshots for this repo's run live at `docs/poc-evidence.md` (all
trials) and `docs/poc-evidence-vulnerable.md` (flagged subset); the raw JSONL
ground truth is under `results-published/`.

## Status

Harness implemented through M1-M4 plus the M5 edit-task/remediation slice. Python SQL is the
mature vertical; Go/Rust SQL packs and an Ollama runner for open-weight models are in as v0.1.
Milestones and remaining scope (new categories, taint-aware Go/Rust detectors) are in the spec.
