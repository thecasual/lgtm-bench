# Extending lgtm-bench

Two things you'll want to do: add a model, and add a language. Neither requires
regenerating existing results. The report is a pure function of the JSONL in
`results/` (or `results-published/`), so you run the new thing, it appends new
trial records, and you re-run `lgtm report`. Nothing already computed is touched.

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

1. **Rules** — `rules/semgrep/sql_<lang>.yaml` (`languages: [<lang>]`). Register
   the language in `lgtm_bench/detectors/__init__.py::get_pack` (copy the go or
   rust branch) and add a `sql-<lang>@x.y` entry to `PACK_VERSIONS`.
2. **Validity** — if the language isn't Python, add an `_is_valid_<lang>` in
   `lgtm_bench/grading.py` (the go/rust ones are a `func`/`fn` + balanced-brace
   heuristic; copy that). Python gets a real AST parse; other languages get a
   structural heuristic unless you wire in a real parser.
3. **Extraction** — add the language's fence tags to `_LANG_ALIASES` in
   `lgtm_bench/extract.py` (e.g. `"go": {"go", "golang"}`).
4. **Corpus** — `tests/detector_corpus/sql-<lang>/{safe,vulnerable}/` with
   labeled samples, and a `tests/test_corpus_<lang>.py` that grades them via
   `_run_pack`. This is the quality gate; iterate the rules until it's 100%.
5. **Tasks** — `tasks/sql-<lang>/*.yaml` with `language: <lang>`,
   `category: sql`, `mode: generate`, `conditions: [none]`, ids like
   `sql-<lang>/user-lookup-by-email`. Mirror the phrasing style of the existing
   tasks (realistic, never mention security).
6. **Fixtures (optional, for repo/edit conditions)** — add
   `fixtures/<lang>-clean/` and `fixtures/<lang>-dirty/`; the engine already
   routes repo-condition fixtures by language.

Then run and report exactly as for a model:

```bash
lgtm run --models claude-sonnet-5 --conditions none --task-filter sql-<lang> --out results
lgtm report results/*.jsonl --tasks tasks --out report.md
```

## Why nothing needs regenerating

`lgtm detect` (re-grade) and `lgtm report` read stored raw outputs; they never
call a model. Adding a model or language only appends new `results/*.jsonl`
records. Existing records keep their `detector_pack_version` and grades. So the
workflow is always: **run the new thing → re-report.** The only time you
re-grade everything is when you change a detector, and even then it's offline
and free (`lgtm detect results/*.jsonl`).

## A note on detector maturity

The Python SQL detector is the mature one: an AST/scope analysis hardened over
nine versions and a three-round adversarial audit. The Go and Rust packs (v0.3)
are Semgrep taint-mode rules that went through their own two-round adversarial
audit against the trial population: Go grades at zero false-positive and zero
false-negative, Rust at zero false-positive with a documented lower-bound gap (a
Vec-accumulate-then-join shape that open-source Semgrep's intraprocedural taint
can't follow, the one case that would need CodeQL). The corpus for each language
is the regression gate; grow it as you find shapes the rules miss.
