# Published raw results

Ground-truth per-trial records behind [`RESULTS.md`](../RESULTS.md),
committed so the results can be independently audited. Start with the
[results](../RESULTS.md) for findings, [`docs/METHODOLOGY.md`](../docs/METHODOLOGY.md)
for how verdicts are decided and validated, and [`docs/REPRODUCE.md`](../docs/REPRODUCE.md)
to rebuild everything from scratch. Normal runs write to `results/` (gitignored);
these are a curated snapshot.

**Provenance:** run this to print the exact date range, run ids, model list,
detector pack version, and trial count for the snapshot in this directory,
so any reader can confirm what they're looking at:

    python3 -c "import json,glob,collections as C; \
      R=[json.loads(l) for f in glob.glob('results-published/*.jsonl') for l in open(f) if l.strip()]; \
      print('trials',len(R)); \
      print('runs',sorted({r['run_id'] for r in R})); \
      print('models',sorted({r['model'] for r in R})); \
      print('pack',sorted({r.get('detector_pack_version') for r in R})); \
      print('verdicts',dict(C.Counter(r['verdict'] for r in R)))"

- `run-*.regraded.jsonl`: one JSON object per trial. Key fields:
  `model`, `task_id`, `mode`, `condition`, `variant_id`, `trial_index`,
  `prompt` (exact text sent), `raw_output` (full model response),
  `extracted_code` (what the detectors graded), `verdict`
  (`secure|vulnerable|invalid`), `findings[]` (each with `detector`, `rule_id`,
  `message`, `line`, `snippet`), `fixed_existing`/`flagged_existing`
  (edit tasks), `timing_ms`, `error` (runner errors, if any),
  `detector_pack_version`, `harness_version`.

**Naming convention:** a run first lands as `run-<hash>.jsonl` (raw model
output, ungraded). Once `lgtm detect` grades it, the graded copy is committed
as `run-<hash>.regraded.jsonl` and the raw file is removed from this
directory, so every file here is always graded under a current detector pack,
never a stale raw dump. `<hash>` is the run's config hash, not a content hash,
so it stays stable across regrades of the same run.

## Files in this snapshot

Eight runs, 3938 trials total, all regraded under the current detector packs (see
`lgtm_bench/detectors/__init__.py::PACK_VERSIONS` for the exact per-(category, language)
version strings). Every file below is `mode: generate` except
`run-cdfef7c4b0a3.regraded.jsonl` (also carries `mode: edit` remediation trials) and
`run-8e3746cbfc1a.regraded.jsonl` (also carries `mode: review` trials).

| File | Run id(s) | Models | Language(s) / condition | Trials |
|---|---|---|---|---|
| `run-f10fee11b727.regraded.jsonl` | `2026-07-13T03-40-43Z` | claude-fable-5, claude-opus-4-8, claude-opus-4-1, claude-sonnet-5, claude-sonnet-4-5, claude-haiku-4-5 | Python SQL, `condition: none` | 312 |
| `run-cdfef7c4b0a3.regraded.jsonl` | `2026-07-13T03-55-29Z`, `2026-07-13T14-33-26Z`, `2026-07-13T14-41-21Z` | claude-fable-5, claude-sonnet-5, claude-sonnet-4-5, claude-haiku-4-5 | Python SQL, `clean-repo` + `dirty-repo` (generate and edit tasks) | 128 |
| `run-e8a4541a372d.regraded.jsonl` | `2026-07-14T15-26-28Z` | llama3.2:3b, qwen3:8b | Python SQL, `condition: none` (Ollama runner) | 200 |
| `run-0b9839185649.regraded.jsonl` | `2026-07-14T15-38-02Z` | claude-fable-5, claude-opus-4-8, claude-opus-4-1, claude-sonnet-5, claude-sonnet-4-5, claude-haiku-4-5 | Go + Rust SQL, `condition: none` | 384 |
| `run-b2c3d1212dc2.regraded.jsonl` | `2026-07-14T20-11-57Z` | llama3.2:3b, qwen3:8b | Go + Rust SQL, `condition: none` (Ollama runner) | 256 |
| `run-331ab1e81231.regraded.jsonl` | `2026-07-15T02-19-07Z` | qwen2.5-coder:7b | Python + Go + Rust SQL, `condition: none` (Ollama runner) | 912 |
| `run-3cb9e32d6a5d.regraded.jsonl` | `2026-07-15T02-09-30Z`, `2026-07-15T04-05-04Z` | qwen3:14b | Python + Go + Rust SQL, `condition: none` (Ollama runner) | 912 |
| `run-8e3746cbfc1a.regraded.jsonl` | `2026-07-15T16-39-29Z`, `2026-07-15T19-00-05Z` | claude-fable-5, claude-opus-4-8, claude-opus-4-1, claude-sonnet-5, claude-sonnet-4-5, claude-haiku-4-5 | Python + TypeScript: command injection, XSS, and TypeScript SQL, `condition: none` (`generate` and `review` modes) | 834 |

That's 10 distinct models across the snapshot (6 Claude, 4 open-weight: `llama3.2:3b`,
`qwen2.5-coder:7b`, `qwen3:8b`, `qwen3:14b`). Run the provenance snippet above at any time to
confirm these numbers against whatever is actually on disk, since this table is a
point-in-time summary and the directory listing is the source of truth.

## Read it as prose instead

`docs/poc-evidence-vulnerable.md` (the tracked vulnerable subset) renders every
flagged trial (prompt → output → extracted code → findings → verdict). The full
per-trial dump `docs/poc-evidence.md` (every trial) is not tracked; regenerate
it, or the subset, with:

    lgtm evidence results-published/*.jsonl --out docs/poc-evidence.md
    lgtm evidence results-published/*.jsonl --verdict vulnerable --out docs/poc-evidence-vulnerable.md

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
