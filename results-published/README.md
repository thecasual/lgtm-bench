# Published raw results

Ground-truth per-trial records behind [`docs/poc-report.md`](../docs/poc-report.md),
committed so the report can be independently audited. Start with the
[report](../docs/poc-report.md) for findings, [`docs/METHODOLOGY.md`](../docs/METHODOLOGY.md)
for how verdicts are decided and validated, and [`docs/REPRODUCE.md`](../docs/REPRODUCE.md)
to rebuild everything from scratch. Normal runs write to `results/` (gitignored);
these are a curated snapshot.

**Provenance:** run this to print the exact date range, run ids, model list,
detector pack version, and trial count for the snapshot in this directory —
so any reader can confirm what they're looking at:

    python3 -c "import json,glob,collections as C; \
      R=[json.loads(l) for f in glob.glob('results-published/*.jsonl') for l in open(f) if l.strip()]; \
      print('trials',len(R)); \
      print('runs',sorted({r['run_id'] for r in R})); \
      print('models',sorted({r['model'] for r in R})); \
      print('pack',sorted({r.get('detector_pack_version') for r in R})); \
      print('verdicts',dict(C.Counter(r['verdict'] for r in R)))"

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

## Inspect trials from the shell

Parse the JSON properly (substring matching on raw lines is fragile). This
prints every vulnerable `order-by-column` trial with its findings:

    python3 - <<'PY'
    import json, glob
    for f in glob.glob("results-published/*.jsonl"):
        for line in open(f):
            if not line.strip(): continue
            r = json.loads(line)
            if r["verdict"] == "vulnerable" and "order-by-column" in r["task_id"]:
                print(r["trial_key"])
                print(r["extracted_code"])
                print("findings:", [x["rule_id"] for x in r["findings"]])
                print("-" * 60)
    PY

Look up one specific trial by its `trial_key` (the key cited in the report):

    python3 -c "import json,glob,sys; [print(json.dumps(json.loads(l),indent=2)) \
      for f in glob.glob('results-published/*.jsonl') for l in open(f) \
      if l.strip() and json.loads(l)['trial_key']==sys.argv[1]]" \
      'f10fee11b727|claude-haiku-4-5|sql/order-by-column|none|v4-speed-pressure|0'

Count verdicts across the whole run:

    python3 -c "import json,glob,collections; c=collections.Counter(json.loads(l)['verdict'] \
      for f in glob.glob('results-published/*.jsonl') for l in open(f) if l.strip()); print(dict(c))"
