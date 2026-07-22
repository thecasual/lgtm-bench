# Smoke test report: lgtm-bench reproducibility check

Date: 2026-07-17. Environment: fresh clone, Linux, Python 3.11.15, semgrep 1.170.0,
`claude` CLI 2.1.212 (subscription, headless). Orchestrated by claude-fable-5 with the
benchmark work executed by non-Fable models (claude-haiku-4-5 and claude-sonnet-5 as
subjects; sonnet/haiku subagents driving the steps). Total wall time about 35 minutes
with parallel fan-out.

## 1. Quick start (README commands)

| Command | Expected (per docs) | Result |
|---|---|---|
| `pip install -e .` | installs `lgtm` | OK (see issue 3 re: semgrep install) |
| `lgtm validate` | tasks + fixture integrity OK | PASS: "tasks: 63 OK; fixtures: 8 files, 9 dirty findings, 0 clean findings; validate: OK" |
| `python -m pytest tests/ -q` | "detector corpus must pass 100%", several minutes cold | PASS: 686 passed, 0 failed, 0 skipped in 24m42s |
| `lgtm run --runner mock ...` (offline dry run) | full pipeline, no model calls | PASS: 19 trials in 38s, verdicts produced (secure/vulnerable/invalid) |

## 2. Report reproducibility (REPRODUCE.md / RUNBOOK.md step 4)

Command: `lgtm report results-published/run-*.jsonl --tasks tasks --out repro-report.md`

Expected: report is "a pure function of the JSONL", should match the committed
`docs/poc-report.md`.

Result: **PASS, byte-identical** (`diff` vs `git show HEAD:docs/poc-report.md` empty).
The HTML report (`--format html`) also builds: 37,631 bytes, fully self-contained
(no external asset references).

## 3. Detector determinism (sampled regrade)

Command: `lgtm detect <file> --tasks tasks --out <copy>` on the two smallest published
files, then per-`trial_key` comparison against the published verdicts.

Expected: identical verdicts (published files already carry current-detector verdicts).

Result: **PASS, 328/328 identical** across `run-cdfef7c4b0a3` (128 records, 6m40s) and
`run-e8a4541a372d` (200 records, 7m22s): verdicts, findings counts, and detector pack
versions all match; zero warnings. Observed regrade throughput about 2.2-3.1s/record in
this container (docs plan for 1.3-1.5s/record; see issue 4).

A full-corpus regrade (3,938 records) was skipped deliberately: at observed throughput
it is a 2.5-3 hour serial job, outside the smoke-test budget. The sampled files plus the
byte-identical report above cover the same claim.

## 4. Live benchmark run vs published results

The README's "smallest meaningful run" was sliced with the README's own flags to fit a
smoke budget (see issue 1). Exact commands, run in parallel, both completed 76/76 trials
in about 9.5 minutes each, zero errored trials:

```
lgtm run --models claude-haiku-4-5 --conditions none --task-filter sql/ --variants v1-plain,v2-terse --trials 2 --out results
lgtm run --models claude-sonnet-5  --conditions none --task-filter sql/ --variants v1-plain,v2-terse --trials 2 --out results
```

(`--task-filter sql/` selects the Python SQL pack plus `review-sql/` by substring match.)

Python SQL generate VIR (vulnerable / gradable, review-mode and invalid excluded):

| Model | This run | Published (docs/poc-report.md, none) | Consistent? |
|---|---|---|---|
| claude-haiku-4-5 | 21.3% (10/47, CI 12-35) | 18% (CI 9-32, n=40) | Yes |
| claude-haiku-4-5, v1-plain | 12.5% (3/24) | pooled plain 12.1% (RESULTS.md) | Yes, near-exact |
| claude-haiku-4-5, v2-terse | 30.4% (7/23) | pooled terse 21.1%; "terse roughly doubles plain" | Yes directionally (2.4x plain) |
| claude-sonnet-5 | 2.1% (1/48, CI ~0-11) | 8% (CI 3-21, n=37) | Yes (CIs overlap) |
| claude-sonnet-5 | same | RESULTS.md narrative "~14%" | No: see issue 2 |

Review mode (`review-sql`, planted SQLi, prose review only): both models flagged the
vulnerability 28/28 (100%), matching the report's near-ceiling flag rates for Claude
models.

Verdict on the method: the pipeline runs end to end on a fresh machine, the published
report regenerates exactly from the raw data, regrading is deterministic, and a fresh
paid run of the same cells lands inside the published confidence intervals with the
phrasing effect (terse > plain) reproducing in the expected direction.

## Issues found (for maintainer review)

1. **README "smallest meaningful run" is not small.** `lgtm run --models
   claude-haiku-4-5 --conditions none --trials 2` now builds a **506-trial grid**
   (all 8 task packs match condition `none`), roughly 1.5-2+ hours at the default
   concurrency 2. The framing predates the new task packs. Suggest updating the
   example to include a `--task-filter`, or stating the expected trial count/runtime.
2. **RESULTS.md mixes slices for sonnet-5 (verified against raw JSONL).** The "Model
   choice" finding says "sonnet-5 ~14%" where the report's headline table says 8%
   (3-21, n=37). Re-verification against the raw records shows ~14% is NOT stale: it
   exactly matches a different slice, Python SQL generate+edit pooled across all
   conditions (10/69 = 14.5%, safety-hint excluded), where 7 of the 10 vulnerable
   records come from sonnet-5's dirty-repo edit cell (the 44% "left the vuln in
   place" behavior). The headline table is generate-only / condition-none (3/37 =
   8.1%). The paragraph's other numbers (opus ~0-2%, haiku ~18%, sonnet-4-5 ~22%)
   match BOTH slices, so only sonnet-5 exposes the mixture. Suggested fix: state the
   slice in the RESULTS.md sentence, or use the headline number (8%) consistently.
3. **`pip install semgrep` fails on stock Debian/Ubuntu images.** It aborts with
   "Cannot uninstall PyJWT 2.7.0, RECORD file not found" (Debian-installed PyJWT).
   Workaround: `pip install semgrep --ignore-installed PyJWT` (or a venv). Worth a
   one-line note in the quick start, since semgrep is required for 5 of the 8 packs.
4. **Regrade planning number optimistic in containers.** Observed ~2.2-3.1s/record vs
   the documented 1.3-1.5s/record (RUNBOOK step 2). Minor, but the full-corpus regrade
   estimate roughly doubles on shared/cloud hardware.
5. **Cosmetic: `--task-filter sql/` also matches `review-sql/`** (substring OR
   semantics). Harmless here (review mode is reported separately) but surprising when
   trying to select only the Python SQL generate pack; there is no filter that selects
   it exclusively because task names collide across language packs.

## Artifacts

- `run-f6de0718b1ba.jsonl`: fresh claude-haiku-4-5 run (76 records)
- `run-6b34550e1a9a.jsonl`: fresh claude-sonnet-5 run (76 records)
