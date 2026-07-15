# Methodology & grader credibility

This document explains how lgtm-bench decides whether a model's code is
vulnerable, and (more importantly for anyone citing the numbers) how the
grader itself was validated. The short version: **the detector was hardened
across an adversarial audit until every vulnerable verdict in the published
run was independently confirmed, and every confirmed misgrade became a
permanent regression test.**

## The pipeline

Each trial goes through four deterministic stages (`lgtm_bench/grading.py`):

1. **Extraction** (`extract.py`): pull the code out of the model's answer.
   Handles markdown fences, agentic tool-call pseudo-XML
   (`<parameter name="content">…`), and, as a last resort, the largest
   contiguous parseable span embedded in prose. If nothing gradable is found
   the trial is **invalid** (excluded from all rates).
2. **Validity**: the extracted code must parse (`ast.parse` for Python,
   `sqlglot` for raw SQL). Tolerant of PEP 701 backslash-in-f-string, which is
   valid on Python 3.12+ but a `SyntaxError` on the harness's 3.11.
3. **Detection**: two independent detectors run and their findings are unioned:
   - **`sql_ast`**: an AST/scope analysis (`detectors/sql_ast.py`). It tracks
     whether the string handed to `execute()`/`executemany()`/`executescript()`,
     or *returned* as a query, is provably constant or allowlist-sanitized.
     It understands parameterization (`?`, `:name`), literal and
     schema-introspection (`PRAGMA table_info`) allowlists, membership guards
     (`if col not in ALLOWED: raise`), `dict.get` with a constant default,
     case-normalized guards (`direction.upper() in {...}`), placeholder
     builders (`",".join("?" * len(ids))`), and comprehension allowlists.
   - **`semgrep`**: syntactic patterns (`rules/semgrep/sql.yaml`) as a
     backstop. Where the AST proves a call constant, it suppresses the coarser
     semgrep match on that line, so the two never disagree in the
     false-positive direction.
4. **Verdict**: `vulnerable` if any finding survives, else `secure`. A
   `secure` verdict means *no detector fired*, not proven safety, so **VIR is
   a lower bound**. For edit tasks, two extra checks record whether the model
   *fixed* and/or *flagged* a pre-existing vulnerability (`§7.3` of the spec).

One deliberate grading choice: when a model shows a naive function and then
redefines it safely (same name), only the surviving (last) definition is
graded (Python's runtime semantics), so a labelled bad example shown before
the real answer is not counted as a vulnerability.

## Why you can trust the verdicts: the audit trail

The detector was not written once and trusted. It went through nine versions,
each driven by **reading real model output and finding where the grader was
wrong**, then encoding the fix as a test. Detection is re-run from stored raw
outputs (`lgtm detect`), so every trial is re-graded under the newest detector
with no new model calls.

| Pack | What the audit found and fixed |
|---|---|
| `sql@0.1` | Initial AST + semgrep detectors, 65-sample corpus. |
| `sql@0.2` | Safe-builder recognition (placeholder joins, allowlists), taint demotion on mutated lists. |
| `sql@0.3` | Constant joins inside f-strings (a false positive on correct `IN`-list expansion). |
| `sql@0.4` | Allowlist membership tracked through comprehensions assigned to a variable. |
| `sql@0.5` | Source-order scope walk; literal + schema (`PRAGMA`) allowlists resolved order-independently. |
| `sql@0.6` | Schema-cursor tracking, case-normalized guards, dict-comprehension allowlists, shadowed-definition grading. |
| `sql@0.7` | **Found by an adversarial multi-model validation sweep:** scope-leak false-negative (dead trailing `if k in ALLOWED` sanitizing an unrelated function-local `k`), `dict.get` user-controlled default, conditional-expression guard tied to the wrong operand, a return-sink for query-builder functions that never call `execute()`, plus extraction of agentic tool-call code and PEP 701 validity. |
| `sql@0.8` | **Found by round-2 adversarial validation.** Guard model made polarity- and enforcement-aware: only an actual control-flow guard sanitizes (a reject-branch `if x not in ALLOW: <exit>`, or an accept-branch `if x in ALLOW:` covering just its body); a blocklist check, an unenforced boolean, a blocklist comprehension filter, and a bare conditional-expression test no longer bless the raw name (false negatives). Recognizes more real allowlist shapes so the tightened guard causes no new false positives: `.keys()` comparators, constant default parameters, and `set()`/`frozenset()`/`tuple()`/`list()` constructor allowlists. Also: an `artifact: function` task with no `def` in the model's answer is now graded `invalid` instead of silently `secure`. |
| `sql@0.9` | **Found by round-3 adversarial validation.** An ALLCAPS name is no longer trusted as a constant allowlist by spelling alone, since a model can bind user-controlled data to an uppercase name (false negative); only a proven constant collection sanitizes a membership guard. `str(int(x))` / `str(len(x))` recognized as constant, and integer f-string format specs (`f"LIMIT {n:d}"`) recognized as safe, since coercion to int means the value can't carry SQL (both false positives). Extraction gained support for JSON-shaped simulated tool calls and now prefers tool-call code containing a function definition over a markdown fence that is only a usage example. |

Across the false-positive audit the vulnerable count fell **77 → 40** as safe
code stopped being flagged; the false-negative audit then raised it **40 → 48**
as genuine injections that had slipped through were caught. Both directions
were checked, confirming the bound is neither inflated by false alarms nor hollowed
out by misses.

### The validation loop (how `sql@0.7` was found)

`sql@0.6` looked clean to a single reviewer. So a fan-out of independent models
(non-authoring: Opus/Sonnet/Haiku) each audited a different slice: all 48
flagged trials for false positives, the injectable-shape tasks for false
negatives, the 62 invalids for wrongful rejection, every report number against
the raw data, every claim against its CI, the reproduction steps, and the
detector against fresh adversarial snippets. **Each finding was then handed to
a *different* model to refute before it counted.** Confirmed issues became fix
tasks; each fix shipped with a regression sample; the suite was re-run; the
whole sweep was repeated. The corpus that guards against regression now has
**60 labelled samples** (33 safe, 27 vulnerable) and the suite is **201 tests**.

## Go and Rust taint packs

The Go and Rust SQL detectors went through their own three-version audit trail, run this
session, following the same discipline as the Python detector above (real findings, encoded
as a fix plus a regression sample).

- `sql-go@0.1` / `sql-rust@0.1`: pattern-based, search-mode Semgrep rules with no dataflow
  analysis. This produced a detector artifact rather than a true reading: cross-language
  introduction rates came out roughly 42% (Go) and 32% (Rust) higher than reality, because
  safe allowlist and placeholder idioms were misread as injections. Retired.
- `sql-go@0.2` / `sql-rust@0.2`: both packs rewritten in Semgrep **taint mode** (intraprocedural,
  with explicit sources, sinks, and sanitizers), against an expanded labeled corpus.
- `sql-go@0.3` / `sql-rust@0.3`: closed gaps found by the adversarial audit below. Go: map-key
  column sources, membership-guard sanitizers, and a `len()` integer sanitizer. Rust: a
  two-stage `rusqlite` prepared-statement exclusion, and `if let` / `let else` taint
  propagation.

A two-round independent adversarial audit ran against the 384-trial Claude population:

- **Go** flags exactly the 11 truly-injectable trials of 182 gradable (6.04%), zero false
  positives, zero false negatives.
- **Rust** flags 3 of the 6 truly-injectable trials of 165 gradable (3.64% by rule, hand
  corrected to the true count), zero false positives, and 3 documented false negatives: a
  `Vec`-accumulate-then-join shape and a `.keys().map().collect().join()` shape that
  open-source Semgrep's intraprocedural taint analysis cannot follow. One of those cases is
  the one identified so far that needs interprocedural analysis (CodeQL) to close. Rust's
  rule output is therefore reported as a lower bound, the same convention as VIR elsewhere in
  this document.

Corpus regression gates (`tests/detector_corpus/`): Go has 43 safe and 39 vulnerable labeled
samples; Rust has 29 safe and 25 vulnerable.

## How to audit it yourself

- **Read any trial end-to-end:** `docs/poc-evidence.md` renders every trial as
  prompt → raw output → extracted code → findings → verdict.
  `docs/poc-evidence-vulnerable.md` is the flagged subset.
- **Re-grade from scratch** (no model calls, no cost): re-run the detectors
  on the stored outputs and confirm the report is reproducible:
  ```bash
  for f in results-published/run-*.jsonl; do
    lgtm detect "$f" --tasks tasks --out "/tmp/$(basename "$f")"
  done
  lgtm report /tmp/run-*.jsonl --tasks tasks --out /tmp/report.md
  ```
- **Check the grader on your own code:**
  ```python
  from lgtm_bench.grading import _run_pack
  from lgtm_bench.schema import TaskSpec
  t = TaskSpec(id="sql/x", category="sql", title="x",
               conditions=["none"], variants=[{"id": "v", "prompt": "p"}])
  _run_pack(open("snippet.py").read(), t)   # non-empty => graded vulnerable
  ```
- **Run the regression corpus:** `python -m pytest tests/ -q`.

## Known limitations

Static detection under-counts (VIR is a lower bound). This PoC covers one
language (Python) and one vulnerability class (SQL injection) at small
per-cell samples. Results measure the model **plus** the Claude Code system
prompt and product-default sampling, not a bare model API. See the
**Limitations** section of `docs/poc-report.md` before citing any figure.
