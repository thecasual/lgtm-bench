# Published raw results

Ground-truth per-trial records behind `docs/poc-report.md`, committed so the
report can be independently audited. Normal runs write to `results/` (gitignored);
these are a curated snapshot.

- `run-*.regraded.jsonl` — one JSON object per trial. Key fields:
  `model`, `task_id`, `mode`, `condition`, `variant_id`, `trial_index`,
  `prompt` (exact text sent), `raw_output` (full model response),
  `extracted_code` (what the detectors graded), `verdict`
  (`secure|vulnerable|invalid`), `findings[]` (each with `detector`, `rule_id`,
  `message`, `line`, `snippet`), `fixed_existing`/`flagged_existing`
  (edit tasks), `timing_ms`, `error` (runner errors, if any),
  `detector_pack_version`, `harness_version`.

## Read it as prose instead

`docs/poc-evidence.md` renders every trial (prompt → output → extracted code →
findings → verdict). `docs/poc-evidence-vulnerable.md` is the vulnerable subset.
Regenerate either with:

    lgtm evidence results-published/*.jsonl --out docs/poc-evidence.md
    lgtm evidence results-published/*.jsonl --verdict vulnerable --out audit.md

## Inspect a single trial from the shell

    python3 -c "import json,sys; [print(json.dumps(json.loads(l),indent=2)) \
      for l in open('results-published/run-f10fee11b727.regraded.jsonl') \
      if 'order-by-column' in l and 'vulnerable' in l]" | head -60
