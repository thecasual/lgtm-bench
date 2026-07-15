# Extending lgtm-bench

Four things you'll want to do: add a model, add a language, add a category, or
add a task under review mode. None of them require regenerating existing
results. The report is a pure function of the JSONL in `results/` (or
`results-published/`), so you run the new thing, it appends new trial records,
and you re-run `lgtm report`. Nothing already computed is touched.

## Add a model

### A Claude model (subscription, via Claude Code)

```bash
lgtm run --models claude-opus-4-8 --conditions none --trials 2 --out results
```

Any model id your `claude` CLI accepts works. Multiple at once:
`--models a,b,c`. Keep `--concurrency 2` for multi-model runs so you don't
trip the subscription session rate limit.

### An open-source model (via your Ollama host)

Set the host once (already in `.env` here):

```bash
INFERENCE_HOST=you@your-box.ts.net   # user@host, host, host:port, or a full URL
```

Then run with the `ollama` runner. The model ids are whatever `ollama list`
shows on the host:

```bash
lgtm run --runner ollama --models llama3.2:3b,qwen3:8b \
         --conditions none --trials 2 --out results
```

Reasoning models (qwen3) and verbose models waste a lot of tokens on these
small tasks. Two flags cut that hard:

```bash
lgtm run --runner ollama --models qwen3:8b --conditions none --trials 2 \
         --no-think --max-tokens 400 --out results
```

`--no-think` disables the model's reasoning block (Ollama `think:false`);
`--max-tokens` caps generation (`num_predict`). Both are big speedups and
change nothing about grading.

Notes:
- The Ollama runner only supports `--conditions none` (a raw model API has no
  filesystem, so it can't work inside a repo). Repo/edit conditions are
  Claude-Code-only.
- The host must be reachable from the machine you run `lgtm` on. If it's on a
  Tailscale tailnet, run `lgtm` from a machine on that tailnet.

### Then, regardless of model, just re-report

```bash
lgtm report results/*.jsonl --tasks tasks --out report.md
lgtm report results/*.jsonl --tasks tasks --format html --out report.html
```

The new model shows up in every table automatically. You do **not** re-grade or
re-run anything else. If you also want the published snapshot updated, copy the
new JSONL into `results-published/` and re-run report against that.

## Add a language

A "language pack" is: Semgrep rules + a labeled corpus + tasks. The grader
routes by `task.language`.

1. **Rules**: `rules/semgrep/sql_<lang>.yaml` (`languages: [<lang>]`). Register
   the language in `lgtm_bench/detectors/__init__.py::get_pack` (copy the go or
   rust branch) and add a `"sql-<lang>"` key to `PACK_VERSIONS`, mapped to the
   version string it should stamp on graded trials (e.g.
   `"sql-go": "sql-go@0.3.0"`). `PACK_VERSIONS` maps the short pack key to the
   full `pack@x.y.z` string; it does not use the `pack@x.y` string itself as a key.
2. **Validity**: if the language isn't Python, add an `_is_valid_<lang>` in
   `lgtm_bench/grading.py` (the go/rust ones are a `func`/`fn` + balanced-brace
   heuristic; copy that). Python gets a real AST parse; other languages get a
   structural heuristic unless you wire in a real parser.
3. **Extraction**: add the language's fence tags to `_LANG_ALIASES` in
   `lgtm_bench/extract.py` (e.g. `"go": {"go", "golang"}`).
4. **Corpus**: `tests/detector_corpus/sql-<lang>/{safe,vulnerable}/` with
   labeled samples, and a `tests/test_corpus_<lang>.py` that grades them via
   `_run_pack`. This is the quality gate; iterate the rules until it's 100%.
5. **Tasks**: `tasks/sql-<lang>/*.yaml` with `language: <lang>`,
   `category: sql`, `mode: generate`, `conditions: [none]`, ids like
   `sql-<lang>/user-lookup-by-email`. Mirror the phrasing style of the existing
   tasks (realistic, never mention security).
6. **Fixtures (optional, for repo/edit conditions)**: add
   `fixtures/<lang>-clean/` and `fixtures/<lang>-dirty/`; the engine already
   routes repo-condition fixtures by language.

Then run and report exactly as for a model:

```bash
lgtm run --models claude-sonnet-5 --conditions none --task-filter sql-<lang> --out results
lgtm report results/*.jsonl --tasks tasks --out report.md
```

### TypeScript, specifically

TypeScript shipped as the fourth language (`sql-typescript@0.1.0`), and it is
the reference example for "no in-process parser" languages: like Go and Rust,
lgtm-bench never parses TypeScript itself, so Semgrep taint mode is not a
convenience here, it is the only option. Three small additions made TypeScript
a first-class language:

- `_LANG_EXT` in `lgtm_bench/detectors/semgrep.py` gained `"typescript": ".ts"`
  so `SemgrepDetector` writes the scanned snippet to `snippet.ts` before
  invoking Semgrep with `languages: [typescript]` rules.
- `_is_valid_typescript` in `lgtm_bench/grading.py` uses the same structural
  heuristic as Go/Rust (a `function`/`=>`/`class` marker plus balanced braces),
  since there is no TypeScript AST in-process to parse against.
- `_LANG_ALIASES` in `lgtm_bench/extract.py` gained a `"typescript"` entry that
  also matches `ts`, `tsx`, `javascript`, `js`, and `node` fences, so a model
  that labels its code block `js` still extracts. `_largest_parseable_span`
  (the prose-fallback extractor) stays Python-only; TypeScript falls through to
  the whole-output fallback, the same as Go and Rust today.

Three category packs now use this same TypeScript plumbing:
`sql-typescript`, `command-injection-typescript`, and `xss-typescript` (see
"Add a category" below and `docs/METHODOLOGY.md` for each one's source/sink/
sanitizer model and audit status).

## Add a category

A "category" is a vulnerability class (SQL injection, OS command injection,
cross-site scripting, …), tracked independently of language. Adding one is
three small, mechanical edits plus the same rules/corpus/tasks work as adding
a language:

1. **Registry**: one line in `lgtm_bench/categories.py::CATEGORY_META`:
   `"<category-id>": {"label": "<human label>", "cwe": ["CWE-<n>"], "status": "active"}`.
   This is the single source of truth for the label and CWE anchor that
   `report.py` and `export.py` both read (`meta_for`/`cwe_for`/`label_for`);
   neither file keeps its own copy anymore.
2. **`PACK_VERSIONS`**: one key per `(category, language)` cell in
   `lgtm_bench/detectors/__init__.py`, keyed `"<category>-<language>"`
   (e.g. `"command-injection-python": "cmdi-python@0.1.0"`) except bare-python
   SQL, which is the one legacy exception keyed just `"sql"`. The value is a
   friendly slug string independent of the key itself.
3. **`get_pack` branch**: add `if name == "<category>": ...` in the same file,
   one `if language == "<lang>":` per language you support, returning either
   an AST detector (`[YourAstDetector()]`, if the language has an in-process
   parser and the sink set is small and syntactically explicit) or
   `_require_semgrep_pack("<lang>", "<category>_<lang>.yaml")` (every other
   language, since Semgrep taint mode is the only option without an
   in-process parser; see the `sql-typescript`/`command-injection-typescript`/
   `xss-typescript` cells for the taint-pack pattern, and
   `command-injection-python`'s `CmdiAstDetector` for the AST pattern). Use a
   **lazy import** inside the branch (`from .cmdi_ast import CmdiAstDetector`)
   so `lgtm_bench/detectors/__init__.py` still imports cleanly before the leaf
   detector file exists: registration and leaf-file authorship can land in
   parallel. An unhandled `language` raises `KeyError` rather than silently
   grading everything secure.

Then the rest is exactly the "Add a language" work, scoped to the new
category: `rules/semgrep/<category>_<lang>.yaml` (or a new AST detector
module), `tests/detector_corpus/<category>-<lang>/{safe,vulnerable}/`, a
corpus test, and `tasks/<category>-<lang>/*.yaml` with `category: <category>`.
If the category also wants review-mode or edit-mode flagging, add
`rules/lexicons/<category>.yaml` (regex terms `flags_issue` checks against
review/edit prose; see `rules/lexicons/command-injection.yaml` and
`rules/lexicons/xss.yaml` for the format).

`meta.axes.category` in `lgtm export` and the category-verdicts table in
`lgtm report` are already data-derived (they iterate whatever categories
appear in the loaded task set), so a new category shows up in both without
any further wiring.

## Review mode: a third interaction mode

Alongside `generate` (write new code) and `edit` (modify an existing fixture
function for an unrelated reason), `Mode.REVIEW` asks the model to **review**
a function that already contains a planted vulnerability, as prose, with no
rewrite: "review this before I merge", "anything you'd change here?". It
measures detection, not introduction, so it is reported in its own section
and excluded from headline VIR (VIR is filtered to `mode == "generate"`; see
`metrics.vir_by_model_condition`).

A review task:

- **requires `target`** in `path::function` form, naming the planted-vuln
  file/function the engine splices into the prompt (same `target` shape as an
  edit task, reused rather than reinvented).
- **must run under `conditions: [none]` only**: review is tool-free, no
  fixture repo is copied. The engine reads the target file straight out of
  the *dirty* fixture (`fixtures/flaskapp-dirty/` today) and appends it to the
  prompt as a fenced code block after `REVIEW_SUFFIX`
  (`lgtm_bench/engine.py`), so the vulnerable code is always in front of the
  model regardless of whether it would have gone looking for it with tools.
- **grades on prose, not code.** `grading.grade()` special-cases
  `Mode.REVIEW` *before* the code-validity gate (a review answer is prose, so
  the code-parses check would wrongly mark it `invalid`). Verdict is `secure`
  for any non-empty response and `invalid` for an empty one; the interesting
  signal is `flagged_existing`, set by the same lexicon detector
  (`detectors/lexicon.flags_issue`) that scores edit-mode flagging, run
  against the task's `category` lexicon.

`tasks/review-sql/*.yaml` is the shipped example: 7 tasks, each pointing at a
different planted-vuln function in `fixtures/flaskapp-dirty/`, phrased as
ordinary pre-merge review requests that never mention security. Extending
review mode to another category (command injection, XSS) needs no new engine
code, just tasks with `category: <cat>` and `detectors: [{pack: <cat>}]`
pointing at a fixture (or new planted-vuln fixture) for that category, plus
that category's lexicon file (see "Add a category" above).

Run and report it exactly like any other task filter:

```bash
lgtm run --models claude-sonnet-5 --conditions none --task-filter review-sql --out results
lgtm report results/*.jsonl --tasks tasks --out report.md   # own section, not folded into VIR
```

## Why nothing needs regenerating

`lgtm detect` (re-grade) and `lgtm report` read stored raw outputs; they never
call a model. Adding a model or language only appends new `results/*.jsonl`
records. Existing records keep their `detector_pack_version` and grades. So the
workflow is always: **run the new thing → re-report.** The only time you
re-grade everything is when you change a detector, and even then it's offline
and free (`lgtm detect results/*.jsonl`).

## Export for the web app

`lgtm export` emits the whole benchmark as one self-contained JSON document
(schema 1.0) for a React frontend to filter client-side:

```bash
lgtm export results-published/run-*.jsonl --tasks tasks --out export.json
```

It reuses the same input handling as `report` (cross-file dedup for free) and
computes every number through `lgtm_bench/metrics.py`, so the export agrees with
the report by construction. It is a pure function of its inputs: `generatedAt`
comes from the newest run timestamp in the data, never wall-clock, so identical
inputs produce byte-identical output.

The document is long/normalized: `results.*` are flat arrays of self-describing
cells that repeat their own axis keys (model, category, language, condition,
mode, variant as applicable). That is the load-bearing choice for the roadmap.
Adding a vulnerability category, a language, or a model appends rows to the
same arrays and one entry to `meta.axes.*` plus the relevant registry; the
document SHAPE never changes and `schemaVersion` stays `1.0` (a category, a
language, or a model is data, not a version bump). `results.reviewDetection`
is the one new results array review mode added; it carries the same flag-rate
shape as edit-mode remediation, per model (and category).

When you add one of those:
- A model: add one line to `MODEL_META` in `lgtm_bench/export.py`
  (displayName, vendor, family, weights, params, runner). An unknown id still
  exports via a prefix-inferred fallback, so a new model never crashes the run;
  the `MODEL_META` entry just makes its card read nicely.
- A category: add one line to `CATEGORY_META` in `lgtm_bench/categories.py`
  (label + CWE anchor list + status), the single registry `export.py` and
  `report.py` both read. SQL maps to CWE-89, command injection to CWE-78, XSS
  to CWE-79.

`meta.dataQuality.mixedPackLanguages` is non-empty whenever a language carries
more than one detector-pack version (a skipped regrade); the frontend should
render a caveat banner then rather than averaging mixed-version cells. Run the
export over the final regraded set so it is empty.

## A note on detector maturity

The Python SQL detector is the mature one: an AST/scope analysis hardened over
nine versions and a three-round adversarial audit. The Go and Rust packs (v0.3)
are Semgrep taint-mode rules that went through their own two-round adversarial
audit against the trial population: Go grades at zero false-positive and zero
false-negative, Rust at zero false-positive with a documented lower-bound gap (a
Vec-accumulate-then-join shape that open-source Semgrep's intraprocedural taint
can't follow, the one case that would need CodeQL). The corpus for each language
is the regression gate; grow it as you find shapes the rules miss.

Four new cells shipped at `v0.1.0` and have not yet been through that kind of
adversarial population audit: `sql-typescript`, `command-injection-python`,
`command-injection-typescript`, and `xss-typescript`. `sql-typescript` and
`command-injection-python` are structurally close to the audited packs
(taint mirrors go/rust, the AST detector mirrors `sql_ast.py`'s proven
CONST/allowlist machinery), so both are expected to converge quickly once
audited. `command-injection-typescript` and especially `xss-typescript` are
newer, less-proven surfaces (the shell-vs-argv split, and the JSX-autoescape/
DOMPurify/textContent sanitizer surface, respectively) and should not be cited
as audited numbers yet. See `docs/METHODOLOGY.md` for each pack's exact
source/sink/sanitizer model and honest status.
