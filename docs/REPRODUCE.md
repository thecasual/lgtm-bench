# Reproduce this report from scratch

Everything here runs on a **Claude subscription** via the `claude` CLI — no API
key, no per-token charges. You need Python 3.11+ and a logged-in `claude` CLI.

## 0. Setup

```bash
git clone <this repo> && cd lgtm-bench
pip install -e .          # installs the `lgtm` command
pip install semgrep       # optional second detector (recommended)
lgtm validate             # sanity-check tasks + fixture pair
python -m pytest tests/ -q   # the detector corpus must pass 100%
```

## 1. Regenerate the report from the published raw data (no model calls)

The raw per-trial results live in `results-published/`. To rebuild the exact
report and evidence files from them:

```bash
# Re-grade the stored model outputs under the current detector (free, offline)
for f in results-published/run-*.jsonl; do
  lgtm detect "$f" --tasks tasks --out "/tmp/$(basename "$f")"
done
lgtm report /tmp/run-*.jsonl --tasks tasks --out /tmp/report.md
lgtm report /tmp/run-*.jsonl --tasks tasks --format html --out /tmp/report.html
lgtm evidence /tmp/run-*.jsonl --out /tmp/evidence.md
diff <(git show HEAD:docs/poc-report.md) /tmp/report.md   # should match
```

The HTML report (`--format html`) is a single self-contained file (inline CSS +
SVG charts, no external assets) built for a "download report" link or hosting on
a blog. Rebrand it by editing the `BRAND` dict at the top of
`lgtm_bench/html_report.py`: palette, fonts, wordmark, title, and links live
there.

This proves the report is a pure function of the raw data + the committed
detector — nothing hand-edited.

## 2. Run a fresh benchmark against the models (spends subscription quota)

```bash
# Smallest meaningful run
lgtm run --models claude-haiku-4-5 --conditions none --trials 2 --out results

# The full run behind this report
./scripts/run_poc.sh          # 6 models × 3 conditions + edit tasks, ~440 trials
```

**Model selection** — `--models` takes any comma-separated list your `claude`
CLI accepts. This report used:
`claude-fable-5, claude-opus-4-8, claude-sonnet-5, claude-haiku-4-5,
claude-sonnet-4-5, claude-opus-4-1`.

**Two things learned the hard way:**
- Keep `--concurrency 2` for multi-model runs; higher trips the subscription
  session rate limit and trials come back as errors.
- Runs are **resumable** — re-run the identical command and only missing or
  errored trials are retried (results append to
  `results/run-<config-hash>.jsonl`, keyed by a per-trial `trial_key`).

## 3. Slice, re-grade, and audit

```bash
# Focus a run
lgtm run --models claude-sonnet-5 --conditions none \
         --task-filter order-by,dynamic-filter --variants v1-plain,v4-speed-pressure \
         --trials 3 --out results

# Read every flagged trial in full
lgtm evidence results/*.jsonl --verdict vulnerable --out audit.md

# Re-grade after a detector change, no re-spend
lgtm detect results/run-<hash>.jsonl --tasks tasks --out regraded.jsonl
```

## Glossary

| Term | Meaning |
|---|---|
| **VIR** | Vulnerability Introduction Rate — share of *gradable* answers that contain an injection. A lower bound (static detection under-counts). |
| **condition `none`** | Bare prompt, no repository context, all tools disabled — pure generation. |
| **`clean-repo` / `dirty-repo`** | The model works inside a fixture repo that is either safe or already contains vulnerable code. |
| **generate vs edit task** | `generate` = write new code; `edit` = modify an existing function for an unrelated reason (measures brownfield remediation). |
| **fix rate / flag rate** | On edit tasks: did the model silently *fix* a pre-existing vulnerability, and/or *flag* it in prose? |
| **flip rate** | Share of (task × condition × variant) cells where identical repeated prompts produced *different* verdicts — nondeterminism. |
| **safety-hint variant** | A prompt variant that explicitly asks for secure code; reported separately, never mixed into headline VIR. |
| **Wilson 95% CI** | Confidence interval for a proportion that behaves well at small n and near 0/1 — why every rate shows a range, not just a point. |
| **flip/eradicated/standing-risk** | Pre-registered category verdicts (spec §1): `eradicated` = VIR upper CI < 1%, `standing risk` = lower CI > 5%. |
| **trial_key** | Primary key of a JSONL record: `confighash\|model\|task\|condition\|variant\|trial_index`. Cited in the report; searchable in `results-published/` and `docs/poc-evidence.md`. |

For how verdicts are decided and validated, see `docs/METHODOLOGY.md`.
For the design, see `docs/TECH_SPEC.md`.
