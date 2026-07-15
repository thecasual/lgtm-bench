# Runbook: landing a new results drop

The exact steps to fold a finished run (new model, new language, more trials)
into the published data and report. Written for the open-weight Go/Rust drop
but every future drop follows the same path. Nothing here calls a model; the
only spend already happened when the run was produced.

## 0. What you need

- The finished `results/run-<hash>.jsonl` file(s) on the machine that ran them.
- A checkout with semgrep available (`semgrep` on PATH, `LGTM_SEMGREP_BIN`, or
  the sandbox path `/opt/semgrep-venv/bin/semgrep`). The regrade refuses to
  run Go/Rust trials without it; that refusal is a feature, not a bug: those
  languages have no other detector, so a semgrep-less regrade would silently
  grade everything secure.

## 1. Publish the raw run file (producer machine)

```bash
cp results/run-<hash>.jsonl results-published/
git add results-published/run-<hash>.jsonl
git commit -m "Add <model> run"
git pull --rebase origin <branch>
git push -u origin <branch>
```

Copy only the run files you mean to publish, never a partial or aborted run
(a partial run covers whichever tasks happened to execute first, which skews
that model's task mix).

## 2. Regrade offline (any machine with semgrep)

```bash
lgtm detect results-published/run-<hash>.jsonl
```

- Writes `run-<hash>.regraded.jsonl` beside the source; re-runs the current
  detector packs over the stored raw outputs. No model calls.
- Prints progress every 50 records. Planning number: about 1.3-1.5s per
  record, so a full 912-trial grid is roughly 20 minutes, two of them 40.
- The write is atomic: an interrupted regrade leaves the original file
  untouched. Re-run to completion.
- A loud WARNING about unmapped task_ids means the run was produced against a
  task set that has drifted from this checkout. Stop and reconcile; those
  records kept their stale verdicts.

Then replace the raw file with the regraded one (convention: published data
carries current-detector verdicts only):

```bash
git rm results-published/run-<hash>.jsonl
git add results-published/run-<hash>.regraded.jsonl
```

Cross-file dedup makes a raw + regraded pair harmless if one slips through
(the regraded record wins deterministically and a stderr line reports the
drop), but do not rely on it; keep the directory clean.

## 3. Validate before publishing numbers

```bash
# Verdict distribution sanity check per model/language
python3 - <<'EOF'
import json, collections, glob
c = collections.Counter()
for f in glob.glob('results-published/run-*.jsonl'):
    for line in open(f):
        r = json.loads(line)
        c[(r['model'], r.get('language','?'), r['verdict'])] += 1
for k in sorted(c): print(k, c[k])
EOF

# Read the flagged trials for any new model (the audit habit that caught the
# 42%/32% detector artifact)
lgtm evidence results-published/run-<hash>.regraded.jsonl \
     --verdict vulnerable --out /tmp/new-flagged.md
```

Read every flagged Go/Rust trial for a new model. The taint packs graded at
zero false positives on the audited population, but a new model can produce
shapes the corpus has not seen. Anything that looks like a false positive
becomes a corpus sample and a rule fix BEFORE the report ships; that loop is
`docs/EXTENDING.md` step 4.

## 4. Regenerate the published report and evidence

```bash
lgtm report results-published/run-*.jsonl --out docs/poc-report.md
lgtm report results-published/run-*.jsonl --format html --out docs/poc-report.html
lgtm evidence results-published/run-*.jsonl --out docs/poc-evidence.md
lgtm evidence results-published/run-*.jsonl --verdict vulnerable \
     --out docs/poc-evidence-vulnerable.md
lgtm export results-published/run-*.jsonl --tasks tasks --out docs/export.json
```

The report is a pure function of the JSONL: new models and languages slot
into every table, the K clause and model counts update themselves, and a
mixed-pack-version banner fires if any file skipped its regrade. If that
banner appears, go back to step 2.

## 5. Gate and ship

```bash
python -m pytest tests/ -q -o addopts=""      # includes the detector corpus
python3 - <<'EOF'
for f in ['docs/poc-report.md','docs/poc-report.html']:
    t = open(f, encoding='utf-8').read()
    assert t.count(chr(0x2014)) == 0 and t.count(chr(0x2013)) == 0, f
print('dash check clean')
EOF
git add -A && git commit -m "Fold <model> run into published report" && git push
```
