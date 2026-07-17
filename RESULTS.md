# lgtm-bench: results summary (v1)

**One line:** asked ordinary coding questions that never mention security, LLMs
ship exploitable code often enough to matter, roughly one in six times as a
strict lower bound, and whether it happens is decided far more by which model
you use and how you phrase the request than by anything a reviewer would catch.

## What was measured

lgtm-bench asks models benign developer requests ("write a function that fetches
a user by email", "greet the user by name on a page") that carry no security
framing, then grades the generated code with static detectors. The headline
metric is the Vulnerability Introduction Rate (VIR): of the trials that produced
gradable code, how many carried a real, exploitable vulnerability. VIR is a
strict lower bound, static detection only counts what it can prove, so the true
rate is higher.

The published v1 run is about 3,900 trials across ten models (six Claude models,
four open-weight: llama3.2:3b, qwen2.5-coder:7b, qwen3:8b, qwen3:14b), three
vulnerability classes (SQL injection / CWE-89, OS command injection / CWE-78,
cross-site scripting / CWE-79), and four languages (Python, Go, Rust,
TypeScript), each request asked several ways (plain, terse, contextual, and a
"keep it short" speed-pressure phrasing). Every number below regenerates from the
committed raw outputs with `lgtm detect` and needs no model calls.

## Headline numbers

- **Pooled introduction rate: 15.5% (about 1 in 6), a strict lower bound.**
- **By class:** SQL 16.5%, XSS 12.8%, command injection 4.3%. The class averages
  hide the real split (below).
- **By language:** Go 19.2%, Python 17.8%, Rust 11.6%, TypeScript 7.4%.

These are small-per-cell point estimates: read them with the Wilson 95% CIs in
`docs/poc-report.md`, not as decision-grade figures. In particular the XSS and
command-injection numbers are Claude-only (no open-weight runs on those classes
yet, a v1.1 roadmap item) and, like every non-SQL cell, come from packs that had
only a flagged-only pilot audit, so they are conservative floors that can only
undercount.

## The three findings that matter

**1. Model choice is the biggest lever, and it is a 10x swing.** On the exact
same Python SQL tasks, the rate runs from ~0-2% on the strongest Claude models
(opus-4-1, opus-4-8) up through the mid tier (sonnet-5 ~14%, sonnet-4-5 ~22%,
haiku ~18%) to 15-31% on the open-weight models. Most tools pick the model for
you, often the cheaper mid-tier one, and nothing on screen tells you which.

**2. SQL is the best case; output encoding is the blind spot.** The industry
drilled "use parameterized queries" for twenty years, so models reach for it
almost reflexively. That reflex does not generalize. On XSS, the weaker Claude
models introduced reflected/stored issues 35-43% of the time; on command
injection, ~13-14%. The strong models stayed at 0% across all three classes, so
this is again a model-tier story, but the safe SQL habit clearly does not carry
over to the vulnerability classes vibe-coded apps are actually full of.

**3. Phrasing moves the rate about 2x.** The same task asked "quick one, keep it
short, don't overthink it" roughly doubles VIR versus a neutral phrasing
(speed-pressure 18.9% and terse 21.1% vs plain 12.1%). In matched pairs the model
writes an allow-list or validation on the calm prompt and deletes it on the
rushed one, so the safe knowledge is present and the framing decides whether it
fires.

## Limitations, stated plainly

VIR is a lower bound. Per-cell samples are small, so read a single cell with its
confidence interval, not on its own. The command-injection and XSS categories
currently have Claude-only data; the cross-language and open-weight comparisons
are strongest for SQL. Results measure the model plus the agent harness it ran
under (the default runner is Claude Code headless), not a bare model API, so the
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

Full method: `docs/METHODOLOGY.md`. Full report: `docs/poc-report.md`. Every
flagged trial: `docs/poc-evidence-vulnerable.md` (regenerate the full per-trial
dump with `lgtm evidence results-published/run-*.jsonl --out docs/poc-evidence.md`).
