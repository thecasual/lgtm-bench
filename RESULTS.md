# lgtm-bench: results summary (v1)

**One line:** asked ordinary coding questions that never mention security, LLMs
ship exploitable code often enough to matter, and whether it happens is decided
far more by which model you use, which vulnerability class, and how you phrase
the request than by anything a reviewer would catch: strong models sit near zero
across the board, while small open-weight models ship command injection about
half the time.

## At a glance

Share of answers that carried an exploitable vulnerability, writing new code
from benign prompts (bare prompt or clean repo, safety-hint variants excluded;
strict lower bounds):

| Vulnerability class | Strong models* | Mid tier** | Open-weight*** |
|---|---|---|---|
| SQL injection (4 languages) | 0.5% (2/396) | 9.7% (38/390) | 24.3% (292/1204) |
| Command injection (Python + TS) | 0% (0/121) | 11.8% (13/110) | 53.4% (496/929) |
| Cross-site scripting (TS) | 0% (0/68) | 23.0% (14/61) | 47.1% (230/488) |

\* opus-4-1, opus-4-8, fable-5 · \*\* sonnet-5, sonnet-4-5, haiku-4-5 ·
\*\*\* llama3.2:3b, qwen2.5-coder:7b, qwen3:8b

Pick a strong model and the risk nearly disappears, in every class. Pick a
mid-tier or small model, the default in many coding tools, and it climbs fast:
roughly 1 in 10 SQL answers, 1 in 4 XSS, and, on the small open-weight models,
about half of all command-injection answers ship exploitable. Details, per-model
splits, and confidence intervals below and in the machine-readable `docs/export.json`.

Read the tier as capability, not license. The small open-weight models here are
the least-capable coding tier, which is why they land worst; open weights are not
the cause (at frontier scale, open models like DeepSeek and Qwen match the leading
proprietary ones, and independent benchmarks agree, see `docs/related-work.md`).
These particular models earn their place because they run on a single consumer GPU
or a laptop, so they are the ones a developer actually reaches for locally: free to
run, but at a ~39% first-draft rate the scan-and-fix rework is where the cost lands.

## What was measured

lgtm-bench asks models benign developer requests ("write a function that fetches
a user by email", "greet the user by name on a page") that carry no security
framing, then grades the generated code with static detectors. The headline
metric is the Vulnerability Introduction Rate (VIR): of the trials that produced
gradable code, how many carried a real, exploitable vulnerability. VIR is a
strict lower bound, static detection only counts what it can prove, so the true
rate is higher.

The published v1 run is about 5,700 trials across ten models (six Claude models,
four open-weight: llama3.2:3b, qwen2.5-coder:7b, qwen3:8b, qwen3:14b), three
vulnerability classes (SQL injection / CWE-89, OS command injection / CWE-78,
cross-site scripting / CWE-79), and four languages (Python, Go, Rust,
TypeScript), each request asked several ways (plain, terse, contextual, and a
"keep it short" speed-pressure phrasing). The three open-weight models below the
14B ran all three classes; qwen3:14b ran SQL only. Every number below regenerates
from the committed raw outputs with `lgtm detect` and needs no model calls.

## Headline numbers

- **Pooled introduction rate: 26.5% (about 1 in 4), a strict lower bound.**
- **By class:** SQL 16.6%, XSS 39.5%, command injection 43.9%. The class averages
  hide the real split (below): command injection is near-zero on strong models
  and about half on the small open-weight ones.
- **By language:** Go 19.2%, Python 19.7%, Rust 11.6%, TypeScript 47.0%.

The pooled rate rose from an earlier Claude-heavy 15.5% once the open-weight
models were run on command injection and XSS, the two classes they handle worst;
it is a trial-weighted pool, so read it with the composition in mind and lean on
the per-model, per-class tables. These are still small-per-cell point estimates:
read them with the Wilson 95% CIs in `docs/export.json`, not as decision-grade
figures. The non-SQL cells come from taint packs that had a pilot audit plus a
per-flag adversarial re-audit of the open-weight run (zero false positives on the
flagged set), so they remain conservative lower bounds that can only undercount.

The XSS by-class rate rose from 27.1% to 39.5% (and TypeScript pooled from 41.3%
to 47.0%) with the detectors@0.4.0 upgrade. That is a detector-recall
improvement, not a behavior change: the new return-HTML sink now catches real
html-email-from-form false negatives that the 0.3.x detector missed, so the XSS
blind spot is measured more accurately, not newly introduced.

**Is the strong-tier near-zero reliable, or just a small sample?** A dedicated
depth run of about 2,300 extra strong-model trials (results-published/depth-runs/,
kept out of the aggregates above because it deliberately over-samples the safe
models) answers this directly: strong-tier command injection came in at 0 of
969 trials (Wilson upper 95% CI about 0.4%), and strong-tier XSS at 1 of 522
(upper CI about 1.1%). The depth run also swept the mid-tier sonnet-5, so the
four-model totals are 0 of 1,248 and 2 of 662. At that scale the near-zero
result holds up, it is not an underpowered small-sample zero.

**The first eradicated cell.** The pre-registered rule calls a (model, category,
language) cell *eradicated* only when its Wilson upper 95% CI drops below 1%,
which needs roughly 380 zero-event trials. To test whether that bar is reachable
at all, we drove a single strong cell to depth: claude-opus-4-8 on Python command
injection came in at 0 of 478 gradable trials, Wilson upper 95% CI 0.80%. That
clears the bar: it is the first cell in the benchmark to earn *eradicated*, a
formal statement that on these tasks, at this sample size, opus-4-8 does not
introduce Python command injection. It is one cell, not a general claim, but it
shows the strong-tier zero is real enough to survive the strictest test the
benchmark defines.

## The three findings that matter

**1. Model choice is the biggest lever, and it is a 10x swing.** On the exact
same Python SQL tasks, the rate runs from ~0-2% on the strongest Claude models
(opus-4-1, opus-4-8) up through the mid tier (sonnet-5 ~8%, sonnet-4-5 ~22%,
haiku ~18%) to 16-31% on the open-weight models. (All figures here are the
report's headline slice: new code, bare prompt, no repo context. Sonnet-5 is
the one model that reads notably worse, ~14%, once brownfield edits inside an
already-vulnerable repo are pooled in; see the per-model remediation
records in `docs/export.json`.) Most tools pick the model for
you, often the cheaper mid-tier one, and nothing on screen tells you which.

**2. SQL is the best case; command injection and output encoding are the blind
spots, and XSS is now the worse of the two.** The industry drilled "use
parameterized queries" for twenty years, so models reach for it almost
reflexively. That reflex does not generalize. On XSS the mid-tier Claude models
introduced reflected/stored issues 23.0% of the time, and the small open-weight
models land around 47.1%, close to command injection's open-weight rate; on
command injection the split is starker still, near-zero on the strong
models but about half (53.4%) on the small open-weight ones. The strong models
stayed at or near zero across all three classes (0/121 on command injection and
0/68 on XSS, and ~0.5% on SQL, where opus-4-8 and fable each shipped one
injection under rushed phrasing), so this is again a model-tier story, but the
safe SQL habit clearly does not carry over to the vulnerability classes
vibe-coded apps are actually full of. The detector-recall fix that raised the
XSS numbers (see Headline numbers, above) did not change any model's behavior,
it measured what was already there, so this is the same finding stated with a
more accurate number, not a new one.

**3. Phrasing moves the rate about 1.5x.** Pooled across all models, compressing
or rushing the same task lifts VIR over a neutral phrasing (terse 33.2% and
speed-pressure 25.0% vs plain 21.5%). In matched pairs the model
writes an allow-list or validation on the calm prompt and deletes it on the
rushed one, so the safe knowledge is present and the framing decides whether it
fires.

## Limitations, stated plainly

VIR is a lower bound. Per-cell samples are small, so read a single cell with its
confidence interval, not on its own. Command injection and XSS now have
open-weight data for three of the four small models (qwen3:14b ran SQL only), so
the cross-vendor comparison holds for those classes too, though the cross-language
matrix is still fullest for SQL (Go and Rust remain SQL-only). Results measure
the model plus the agent harness it ran under (the default runner is Claude Code
headless), not a bare model API, so the
harness is part of the system under test. This is a research proof of concept for
comparing models and prompts, not a security certification of any model or any
application.

## How this compares to other work

These numbers sit at the conservative end of a consistent recent literature
(Veracode's 2025/2026 GenAI reports, SafeGenBench, SecureAgentBench, SUSVIBES).
Ours is lower because it grades single functions statically on benign prompts
rather than whole applications by live exploit. Where the scope matches, it
agrees: Veracode's per-class split (SQL well defended, XSS failing the large
majority of the time) mirrors ours almost exactly. See `docs/related-work.md`.

## Reproduce

```bash
for f in results-published/run-*.jsonl; do
  lgtm detect "$f" --tasks tasks --out "/tmp/$(basename "$f")"
done
lgtm report /tmp/run-*.jsonl --tasks tasks --out /tmp/report.md
```

Full method: `docs/METHODOLOGY.md`. Machine-readable results: `docs/export.json`. Every
flagged trial: `docs/poc-evidence-vulnerable.md` (regenerate the full per-trial
dump with `lgtm evidence results-published/run-*.jsonl --out docs/poc-evidence.md`).
