# lgtm-bench

A benchmark for measuring **how often LLMs introduce security vulnerabilities when handling
ordinary developer requests**: the code that "looks good to me" in review but carries a
latent bug.

lgtm-bench measures five things:

1. **Vulnerability introduction rate**: asked a benign question ("write a function that
   fetches a user by email"), how often does the model produce vulnerable code?
2. **Sensitivity & reproducibility**: how much does that rate change across paraphrasings
   of the same request, and across repeated runs of the identical prompt?
3. **Context contamination**: does the model get worse when the repo it works in already
   contains insecure code?
4. **Remediation behavior**: when editing existing vulnerable code for an unrelated reason,
   does the model silently fix the issue, flag it, ignore it, or make it worse?
5. **Model-generation gap**: are these rates a property of LLMs in general, or only of the
   newest frontier models? (frontier vs. older vs. open-weight)

The end deliverable is a data-backed **"State of Vibe Coding"** write-up testing six
pre-registered hypotheses: three vulnerability classes modern models may have effectively
*eradicated* (SQL injection, weak password hashing, unsafe deserialization) and three they
plausibly still *introduce* (insecure randomness for secrets, path traversal, command
injection).

Two of those six hypotheses now have shipped task suites and detectors: **SQL injection**
(`sql`, CWE-89, hypothesis H-W1) and **OS command injection** (`command-injection`, CWE-78,
hypothesis H-L3). A third category, **cross-site scripting** (`xss`, CWE-79), also has a
shipped task suite and detector; it was added after pre-registration and is not one of the
original six hypotheses, so read it as an extra category, not a hypothesis test. Detection is
fully static (Semgrep taint-mode rules plus, for Python, an AST detector): deterministic and
free to run. Model calls ride an Anthropic subscription via Claude Code headless mode.

Alongside the `generate` (write new code) and `edit` (modify existing code) task modes, a
third mode, **review**, shows the model a function that already contains a planted
vulnerability and asks for a prose code review only, no rewrite: it measures whether the
model *notices* an existing issue, not whether it introduces one, and is reported in its
own section rather than folded into the headline rate.

The models in the published run: **`claude-fable-5`** (a fast Claude model, the smaller
sibling in this generation, used here as the frugal default), **`claude-opus-4-8`** and
**`claude-opus-4-1`** (frontier), **`claude-sonnet-5`** and **`claude-sonnet-4-5`**
(mid-tier, current and prior generation), **`claude-haiku-4-5`** (small/fast).

**Read next:**
- [docs/poc-report.md](docs/poc-report.md): the benchmark report (findings, tables, limitations)
- [docs/METHODOLOGY.md](docs/METHODOLOGY.md): how verdicts are decided and how the grader was validated
- [docs/REPRODUCE.md](docs/REPRODUCE.md): reproduce the report from scratch, plus a glossary
- [docs/TECH_SPEC.md](docs/TECH_SPEC.md): the full design
- [docs/poc-evidence.md](docs/poc-evidence.md): every trial: prompt → output → findings → verdict

## Quick start

```bash
pip install -e .            # python 3.11+
# optional but recommended (second detector): pip install semgrep
lgtm validate               # check tasks + fixture pair integrity
python -m pytest tests/ -q  # detector corpus must pass 100%
```

The full test suite is semgrep-backed for several corpora; on the first run, or on a machine
without a warm semgrep cache, budget several minutes for `pytest tests/ -q` rather than
expecting it to return instantly (see `docs/RUNBOOK.md` for the per-record planning number
that governs the slowest step, offline detector regrading).

The default runner shells out to **Claude Code headless** (`claude -p`), so model calls ride
your existing Claude subscription: install and log in to the `claude` CLI first. No API key
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
can't work inside a repo). Beyond Python, there are Go, Rust, and TypeScript SQL task packs
(`--task-filter sql-go` / `sql-rust` / `sql-typescript`). The Go/Rust detectors are Semgrep
taint-mode packs (`sql-go@0.3.0`, `sql-rust@0.3.0`), validated against a labeled corpus and a
two-round adversarial audit that matched a hand-count of the trial population (Go zero
false-positive and zero false-negative; Rust zero false-positive, reported as a lower bound
because two dataflow shapes, a `Vec`-accumulate-then-join and a
`.keys().map().collect().join()` chain, sit below open-source Semgrep, giving three
documented false negatives).
[docs/poc-report.md](docs/poc-report.md) has the numbers.

Command injection and XSS ship as TypeScript Semgrep taint packs
(`--task-filter cmdi-typescript` / `xss-typescript`), plus command injection ships a Python
AST detector mirroring the SQL one (`--task-filter cmdi-python`). These four (category,
language) cells (current versions in
`lgtm_bench/detectors/__init__.py::PACK_VERSIONS`) have each been through a pilot audit of
their flagged Claude trials, narrower in scope than the population-level adversarial audit
Python/Go/Rust SQL received, so treat their numbers as directional, especially
`xss-typescript` (the widest sink set and trickiest sanitizer surface of the four). See
[docs/METHODOLOGY.md](docs/METHODOLOGY.md) for each pack's exact model and honesty caveat.

There is also a **review mode** (`--task-filter review-sql`): the model is shown a function
with a planted vulnerability and asked for a prose review, no rewrite; the flag rate is a
lexicon-based lower bound, reported in its own section, never mixed into VIR.

Adding a model, language, or category never requires regenerating existing results; the
report is a pure function of the JSONL. Full runbook:
[docs/EXTENDING.md](docs/EXTENDING.md).

Runs are **resumable**: re-running the same command skips completed trials (results append
to `results/run-<config-hash>.jsonl`). Useful flags: `--concurrency N` (default 2),
`--timeout S` per trial, `--runner mock` for an offline dry run of the whole pipeline.

### Grade and report

```bash
lgtm report results/*.jsonl --out report.md   # leaderboard, deltas, CIs, examples
lgtm detect results/run-….jsonl               # re-grade stored outputs after a detector
                                              # upgrade: no model calls, no re-spend
```

### Audit the results yourself

Every number in the report traces back to per-trial records. To read the full
evidence (the exact prompt, the raw model output, the code the harness
extracted, each scan finding, and the verdict):

```bash
lgtm evidence results/*.jsonl --out evidence.md                 # every trial
lgtm evidence results/*.jsonl --verdict vulnerable --out v.md   # just the flagged ones
lgtm evidence results/*.jsonl --task-filter order-by --model claude-sonnet-5
```

Rendered snapshots for this repo's run live at `docs/poc-evidence.md` (all
trials) and `docs/poc-evidence-vulnerable.md` (flagged subset); the raw JSONL
ground truth is under `results-published/`.

## Status

Harness implemented through M1-M4 plus the M5 edit-task/remediation slice, and now a slice of
the M5 category roadmap. Python SQL is the mature vertical; Go/Rust SQL packs (v0.3, Semgrep
taint mode, audited) and an Ollama runner for open-weight models are in. Three categories now
have shipped detectors (SQL/CWE-89, command injection/CWE-78, XSS/CWE-79); of those, only SQL
and command injection are pre-registered hypotheses (H-W1, H-L3) -- XSS is an added category,
not one of the six. The four newest (category, language) cells are pilot-audited taint/AST
packs pending the same population-level audit Python/Go/Rust SQL received (current versions in
`lgtm_bench/detectors/__init__.py::PACK_VERSIONS`), and review mode (does the model flag a
planted vulnerability in prose?) is in as a third interaction mode alongside generate/edit.
Milestones and remaining scope (the other four pre-registered category-roadmap hypotheses,
new languages, interprocedural Rust dataflow via CodeQL) are in the spec.
