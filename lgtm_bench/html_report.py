"""Self-contained, brandable HTML report (TECH_SPEC §8, presentation layer).

Everything is inline (CSS and SVG charts, no external assets or JS libraries)
so the output is a single downloadable file. The entire visual identity lives
in the ``:root`` CSS-variable block near the top of ``_CSS`` (colors, fonts,
wordmark); swap those to rebrand. All numbers are computed from the same
records/metrics as the markdown report, so the two never disagree.
"""
from __future__ import annotations

import html
import sys
from collections import defaultdict
from pathlib import Path

from . import HARNESS_VERSION
from . import metrics as M
from .categories import cwe_for, label_for
from .schema import TaskSpec

# --------------------------------------------------------------------------
# Brand tokens. EDIT THIS BLOCK to rebrand. One place, no other CSS changes.
# --------------------------------------------------------------------------
BRAND = {
    "wordmark": "Sam Wallace",
    "report_kicker": "Security Research",
    "report_title": "Does an LLM Write Secure Code?",
    # NOTE: the subtitle's model-count clause is computed from the data in
    # build_html_report (see `subtitle`), never hardcoded here. BRAND holds
    # styling and static copy only, never a data claim like the model count.
    "report_subtitle_tail": "introduce SQL injection, where the risk actually "
                            "lives, and what it means for how you prompt, "
                            "review, and spend tokens.",
    "repo_url": "https://github.com/thecasual/lgtm-bench",
    "site_url": "https://www.samwallace.dev/",
    "author": "Sam Wallace",
    # palette matched to samwallace.dev dark theme (Tailwind slate + blue)
    "bg": "#0f172a",         # slate-900
    "bg_soft": "#1e293b",    # slate-800
    "surface": "#1e293b",    # slate-800 (cards)
    "surface_2": "#334155",  # slate-700
    "border": "#334155",     # slate-700
    "text": "#f1f5f9",       # slate-100
    "text_dim": "#94a3b8",   # slate-400
    "accent": "#3b82f6",     # blue-500
    "accent_2": "#60a5fa",   # blue-400
    "good": "#22c55e",       # green-500
    "warn": "#f59e0b",       # amber-500
    "bad": "#ef4444",        # red-500
    "font": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
            "Helvetica, Arial, sans-serif",
    "mono": "'JetBrains Mono', 'Fira Code', ui-monospace, 'SF Mono', Menlo, "
            "Consolas, monospace",
}


def _e(s) -> str:
    return html.escape(str(s))


def _categories_present(records_all: list[dict], cats: dict[str, str]) -> list[str]:
    """The sorted set of vulnerability categories the data actually covers.
    Mirrors report.py: every category-count claim in the copy reads from this,
    so 'N of 6 hypotheses' and the 'N vulnerability classes' limitation track
    the records instead of a hardcoded 'SQL injection only'."""
    return sorted({M.record_category(r, cats) for r in records_all})


def _hypothesis_bits(cats_present: list[str]) -> str:
    """Render categories as 'label/CWE' bits, e.g. 'SQL injection/CWE-89,
    OS command injection/CWE-78'. CWE ids come from the categories registry."""
    bits = []
    for c in cats_present:
        cwe = ", ".join(cwe_for(c))
        bits.append(f"{label_for(c)}/{cwe}" if cwe else label_for(c))
    return ", ".join(bits)


def _html_table(headers: list[str], rows: list[list[str]]) -> str:
    """Small data table. Header text is escaped; cell strings are treated as
    trusted pre-built HTML (callers wrap values in <code> and escape them)."""
    out = ["<table class='dtable'><thead><tr>"]
    out += [f"<th>{_e(h)}</th>" for h in headers]
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


# --------------------------------------------------------------------------
# small inline-SVG chart helpers (no JS, no libs)
# --------------------------------------------------------------------------
def _bar_chart(rows, *, max_pct=None, unit="%", height_per=34, label_w=200,
               value_fmt=None, color_key=None):
    """rows: list of (label, value_pct, caption). Horizontal bars."""
    if not rows:
        return "<p class='muted'>No data.</p>"
    max_pct = max_pct or max([r[1] for r in rows] + [1])
    max_pct = max(max_pct, 1)
    W, pad_l, pad_r = 640, label_w, 60
    plot_w = W - pad_l - pad_r
    H = height_per * len(rows) + 10
    out = [f"<svg viewBox='0 0 {W} {H}' class='chart' role='img' width='100%'>"]
    for i, (label, val, cap) in enumerate(rows):
        y = i * height_per + 6
        bw = max(2, plot_w * (val / max_pct))
        col = "var(--accent)"
        if color_key:
            col = color_key(val, label)
        vfmt = value_fmt(val) if value_fmt else f"{val:.0f}{unit}"
        out.append(
            f"<text x='{pad_l-10}' y='{y+16}' text-anchor='end' class='cl'>{_e(label)}</text>")
        out.append(
            f"<rect x='{pad_l}' y='{y+4}' width='{plot_w}' height='16' rx='4' class='ctrack'/>")
        out.append(
            f"<rect x='{pad_l}' y='{y+4}' width='{bw:.1f}' height='16' rx='4' fill='{col}'/>")
        out.append(
            f"<text x='{pad_l+bw+8:.1f}' y='{y+16}' class='cv'>{_e(vfmt)}</text>")
        if cap:
            out.append(
                f"<text x='{pad_l-10}' y='{y+27}' text-anchor='end' class='ccap'>{_e(cap)}</text>")
    out.append("</svg>")
    return "".join(out)


def _paired_chart(rows):
    """rows: (label, left_pct, right_pct, left_name, right_name) grouped bars."""
    if not rows:
        return "<p class='muted'>No data.</p>"
    mx = max([max(r[1], r[2]) for r in rows] + [1])
    W, pad_l, pad_r = 640, 200, 60
    plot_w = W - pad_l - pad_r
    hp = 46
    H = hp * len(rows) + 20
    out = [f"<svg viewBox='0 0 {W} {H}' class='chart' width='100%'>"]
    for i, (label, lv, rv, ln, rn) in enumerate(rows):
        y = i * hp + 8
        lw = max(2, plot_w * (lv / mx)); rw = max(2, plot_w * (rv / mx))
        out.append(f"<text x='{pad_l-10}' y='{y+16}' text-anchor='end' class='cl'>{_e(label)}</text>")
        out.append(f"<rect x='{pad_l}' y='{y+2}' width='{lw:.1f}' height='13' rx='3' fill='var(--text-dim)'/>")
        out.append(f"<text x='{pad_l+lw+6:.1f}' y='{y+13}' class='cv'>{lv:.0f}%</text>")
        out.append(f"<rect x='{pad_l}' y='{y+18}' width='{rw:.1f}' height='13' rx='3' fill='var(--bad)'/>")
        out.append(f"<text x='{pad_l+rw+6:.1f}' y='{y+29}' class='cv'>{rv:.0f}%</text>")
    out.append("</svg>")
    legend = (f"<div class='legend'><span><i class='sw' style='background:var(--text-dim)'></i>"
              f"{_e(rows[0][3])}</span><span><i class='sw' style='background:var(--bad)'></i>"
              f"{_e(rows[0][4])}</span></div>")
    return "".join(out) + legend


# --------------------------------------------------------------------------
def build_html_report(records: list[dict], tasks: list[TaskSpec]) -> str:
    hints = M.hint_map(tasks)
    cats = M.category_map(tasks)
    records_all = list(records)
    langs = M.languages_present(records_all)
    # Findings are the mature Python vertical; go/rust get a cross-language
    # block (their audited taint packs run generate/condition-none only). All
    # pack versions come from the records, never hardcoded here. Review-mode
    # trials are also excluded from the analytical body: they measure detection
    # of a planted vuln, not introduction, and get their own section below.
    # Without this exclusion review SECURE records would leak into the headline
    # VIR and invalid denominators (mirrors report.py).
    records = [r for r in records_all
               if M.record_language(r) == "python" and r.get("mode") != "review"]
    records_review = [r for r in records_all if r.get("mode") == "review"]
    models = M.sorted_models({r["model"] for r in records})
    n_total = len(records_all)
    n_inv = sum(1 for r in records_all if r["verdict"] == "invalid")
    # Masthead flagged-vulnerable count is WHOLE-RUN, computed over records_all,
    # so it is internally consistent with the other two whole-run masthead stats
    # (n_total trials, all_models). The report body presents every language
    # (Cross-language, Category verdicts cover Go/Rust/TypeScript + XSS + cmdi),
    # so a Python-only count sitting next to "N trials / M models" would read as
    # a whole-run figure while silently undercounting. The Python-only vulnerable
    # total still lives in-body (Finding 01 and the per-task/headline tables).
    n_vuln = sum(1 for r in records_all if r["verdict"] == "vulnerable")
    run_ids = sorted({r.get("run_id", "?") for r in records_all})
    pack = sorted({r.get("detector_pack_version", "") for r in records_all if r.get("detector_pack_version")})

    # Vendor split for the subtitle and limits box (both derive the model count
    # from data, never from BRAND). Natural-sorted so numbered names order right.
    all_models = M.sorted_models({r["model"] for r in records_all})
    oss_models = [m for m in all_models if not m.startswith("claude-")]
    n_claude = len(all_models) - len(oss_models)

    # Pack versions grouped by language (data-derived). Used for the limits-box
    # pack clause, the cross-language narrative, and the mixed-pack guardrail.
    packs_by_lang = M.packs_by_language(records_all)
    nonpy_packs = sorted({v for l, vs in packs_by_lang.items()
                          if l != "python" for v in vs})

    # Category coverage is data-derived (mirrors report.py): the class count and
    # the category/CWE list both come from the records, so a cmdi/xss data drop
    # updates this copy automatically instead of leaving a stale "SQL injection
    # only".
    cats_present = _categories_present(records_all, cats)
    ncat = len(cats_present)
    cat_bits = _hypothesis_bits(cats_present)
    class_noun = ("one vulnerability class" if ncat == 1
                  else f"{ncat} vulnerability classes")

    # Scope phrase derived from languages present, so the "one language" copy
    # never contradicts a rendered cross-language section (rep-1's html twin).
    if len(langs) == 1:
        _scope_phrase = f"This is one language and {class_noun} ({cat_bits})."
    else:
        _scope_phrase = ("This covers "
                         + ", ".join(l.capitalize() for l in langs)
                         + f" and {class_noun} ({cat_bits}).")

    # rep-3: subtitle model-count clause computed from the data.
    if oss_models:
        model_clause = (f"{len(all_models)} models ({n_claude} Claude, "
                        f"{len(oss_models)} open-weight)")
    else:
        model_clause = f"{n_claude} Claude models"
    subtitle = f"How often {model_clause} {BRAND['report_subtitle_tail']}"

    # cross-language rows (only rendered if go/rust present). Scoped to
    # category=sql: this is the "same SQL tasks across languages" comparison, so
    # a language that also carries command-injection or XSS tasks (typescript)
    # contributes ONLY its sql-typescript trials here, never a three-category mix.
    xlang = M.vir_by_model_language(records_all, hints, condition="none",
                                    category="sql", categories=cats)
    xlang_pooled = M.vir_by_language(records_all, hints, condition="none",
                                     category="sql", categories=cats)
    other_langs = [l for l in langs if l != "python"]

    # ---- compute the figures the narrative references ----
    # The bare-prompt headline chart is SQL-only (num-3): the Claude models also
    # carry cmdi-python trials (all secure), so pooling every category would
    # understate their SQL rate versus the pure-SQL open-weight rows and read as
    # a category-mixed column while the prose says "SQL injection".
    records_sql = [r for r in records if M.record_category(r, cats) == "sql"]
    none_vir = M.vir_by_model_condition(records_sql, hints, mode="generate")
    model_rows = []
    for m in models:
        r = none_vir.get((m, "none"))
        if r and r.n:
            model_rows.append((m, 100 * r.p, f"n={r.n}", r))
    model_rows.sort(key=lambda x: x[1])

    # per-task VIR (none, pooled)
    pop = [r for r in M.headline(records, hints) if r["condition"] == "none"]
    task_agg = defaultdict(lambda: [0, 0])
    for r in pop:
        t = r["task_id"].split("/")[-1]
        task_agg[t][1] += 1
        if r["verdict"] == "vulnerable":
            task_agg[t][0] += 1
    task_rows = sorted(([t, 100 * k / n if n else 0, f"{k}/{n}"]
                        for t, (k, n) in task_agg.items()), key=lambda x: -x[1])

    # brownfield: edit vs generate
    brown = M.brownfield_delta(records, hints)
    brown_rows = [(m, 100 * d["generate"].p, 100 * d["edit"].p, "greenfield (new code)", "editing existing vulnerable code")
                  for m, d in sorted(brown.items(), key=lambda x: -x[1]["delta"])]

    # remediation fix/flag
    rem = M.remediation(records)
    flag_rows = [(m, 100 * d["flag"].p, f"fixed {100*d['fix'].p:.0f}%") for m, d in sorted(rem.items(), key=lambda x: -x[1]["flag"].p)]

    # phrasing
    byv = defaultdict(lambda: [0, 0])
    inv_by_v = defaultdict(lambda: [0, 0])
    for r in pop:
        byv[r["variant_id"]][1] += 1
        if r["verdict"] == "vulnerable":
            byv[r["variant_id"]][0] += 1
    for r in records:
        if r["condition"] != "none":
            continue
        inv_by_v[r["variant_id"]][1] += 1
        if r["verdict"] == "invalid":
            inv_by_v[r["variant_id"]][0] += 1

    def vpct(v):
        k, n = byv.get(v, [0, 0])
        return 100 * k / n if n else 0

    def ipct(v):
        k, n = inv_by_v.get(v, [0, 0])
        return 100 * k / n if n else 0

    plain_vir, speed_vir = vpct("v1-plain"), vpct("v4-speed-pressure")
    plain_inv, speed_inv = ipct("v1-plain"), ipct("v4-speed-pressure")

    def sev_color(val, label=None):
        return "var(--good)" if val < 5 else ("var(--warn)" if val < 25 else "var(--bad)")

    # ---- assemble HTML ----
    p = []
    a = p.append
    a(f"<div class='wrap'>")

    # header
    a("<header class='masthead'>")
    a(f"<div class='brandrow'><span class='wordmark'>{_e(BRAND['wordmark'])}</span>"
      f"<span class='kicker'>{_e(BRAND['report_kicker'])}</span></div>")
    a(f"<h1>{_e(BRAND['report_title'])}</h1>")
    a(f"<p class='subtitle'>{_e(subtitle)}</p>")
    a("<div class='meta'>")
    a(f"<span><b>{n_total}</b> trials</span>"
      f"<span><b>{len(all_models)}</b> models</span>"
      f"<span><b>{n_vuln}</b> flagged vulnerable (this run)</span>"
      f"<span>detector <b>{_e(', '.join(pack) or 'n/a')}</b></span>")
    a("</div>")
    a("<div class='btnrow'>")
    a("<button class='btn' onclick='window.print()'>⤓ Save as PDF</button>")
    a(f"<a class='btn ghost' href='{_e(BRAND['repo_url'])}'>View the code &amp; raw data →</a>")
    a("</div>")
    a("</header>")

    # rep/dryrun-4: mixed-pack guardrail. One language with two pack versions is
    # a skipped/partial regrade. Shout in the body and on stderr; still render.
    mixed = M.mixed_pack_languages(records_all)
    if mixed:
        detail = "; ".join(f"{lang}: {', '.join(vs)}"
                           for lang, vs in sorted(mixed.items()))
        a("<div style='background:#7f1d1d;color:#fff;border:2px solid #ef4444;"
          "border-radius:12px;padding:16px 20px;margin:24px 0;font-weight:600;"
          "line-height:1.5;'>&#9888; <b>WARNING: mixed detector pack versions "
          "within a language.</b> " + _e(detail) + ". This is the signature of "
          "a skipped or partial regrade (raw and regraded records pooled "
          "together), so every number below mixes inconsistently graded trials. "
          "Regrade before citing.</div>")
        print("WARNING: mixed detector pack versions within a language: "
              + detail, file=sys.stderr)

    # TL;DR strip
    a("<section class='tldr'>")
    a("<h2>Short version</h2>")
    a("<p class='lede'>Frontier models basically don't write SQL injection into "
      "<em>new</em> code anymore. They will happily copy it out of code that already "
      "has it. And whether they even <em>tell you</em> about the existing hole depends "
      "heavily on which model you picked. Your prompt moves both the risk and the "
      "bill.</p>")
    a("</section>")

    # cost callout
    a("<section class='callout'>")
    a("<h3>This is a cost problem, not just a security one</h3>")
    a("<p>A vulnerability that ships is the most expensive output you can generate. You "
      "pay for it in re-prompts, review time, a rewrite, and incident response if it "
      "reaches prod. The data points at two cheap controls upstream of all of that. "
      f"Lazy \"just bang it out\" prompts raised the injection rate "
      f"(<b>{plain_vir:.0f}% to {speed_vir:.0f}%</b>) and returned <b>no usable code "
      f"{speed_inv:.0f}% of the time</b>, so you burn round-trips getting nothing. And "
      "because insecure code is contagious (finding 03), fixing the vulnerable patterns "
      "already in your repo buys you more than swapping models.</p>")
    a("</section>")

    # Finding 1: greenfield gradient
    a("<section>")
    a("<h2><span class='num'>01</span> New code is mostly safe, but it's a gradient</h2>")
    a("<p>Same everyday questions, no repo context. The models split hard. Frontier "
      "models sit near zero. The prior-generation Sonnet and the smaller models are "
      "several times higher. So \"the latest models don't write SQLi\" is true, but only "
      "for the newest and largest ones. Treat model choice as a real security lever for "
      "greenfield work.</p>")
    a("<div class='card'>")
    a("<div class='cardhead'>Injection rate, new code, bare prompt (lower is better)</div>")
    a(_bar_chart([(m, v, cap) for m, v, cap, _ in model_rows], color_key=sev_color))
    a("<p class='fig-note'>Static detection, so these are floors. Small n, so read the "
      "gradient, not the exact ordering.</p>")
    a("</div></section>")

    # Cross-language (only when go/rust data is present)
    if other_langs:
        a("<section>")
        a("<h2><span class='num'>01b</span> Cross-language: Go and Rust track Python</h2>")
        a("<p>The same everyday tasks, ported to " + _e(" and ".join(other_langs)) +
          ". New-code injection rates pooled across models, by language:</p>")
        # rep-7: bars are trial-weighted; the caption also carries the
        # equal-weight macro-average (each model once, no CI), so a K=8
        # open-weight cell can't silently dominate the pooled bar.
        pooled_rows = []
        for lang in langs:
            r = xlang_pooled.get(lang)
            if not (r and r.n):
                continue
            macro = M.macro_vir(records_all, hints, condition="none",
                                language=lang, category="sql", categories=cats)
            cap = f"n={r.n}"
            if macro is not None:
                cap += f", {100*macro:.0f}% equal-weight"
            pooled_rows.append((lang, 100 * r.p, cap))
        a("<div class='card'>")
        a("<div class='cardhead'>Injection rate in new code, by language (pooled)</div>")
        a(_bar_chart(pooled_rows, color_key=sev_color, label_w=120))
        a("<p class='fig-note'>Bars are <strong>trial-weighted</strong> VIR pooled across "
          "models; the caption's <strong>equal-weight</strong> figure averages each model's "
          "VIR once (no CI). They can diverge when models ran different trial counts (e.g. "
          "K=8 open-weight cells alongside K=2 Claude cells), so read both.</p>")
        a("<p class='fig-note'><strong>Earlier drafts put Go and Rust at roughly 4x Python. "
          "That gap was a detector artifact, and it is gone.</strong> The first Go/Rust grader "
          "was a pattern-based Semgrep rule with no dataflow, so it flagged safe idioms as "
          "injections: <code>fmt.Sprintf</code> building a <code>?</code>-placeholder list "
          "passed as <code>args...</code>, allowlisted <code>ORDER BY</code> where the column "
          "comes from a map or switch, integer <code>LIMIT</code>/<code>OFFSET</code>. An "
          "independent adversarial audit hand-read every flagged trial and found most were "
          "false positives on safe code. The current packs (" +
          (", ".join(f"<code>{_e(v)}</code>" for v in nonpy_packs)
           or "the current taint packs") +
          ") use Semgrep <strong>taint mode</strong> and recognise "
          "those sanitizing idioms; a second independent audit confirmed they match the "
          "hand-audit (Go: zero false-positive and zero false-negative on the population; Rust: "
          "zero false-positive). The corrected picture mirrors Python: frontier models rarely "
          "inject in any language, the weak and open-weight models carry the double-digit "
          "rates.</p>")
        a("<p class='fig-note'><strong>Rust is a lower bound.</strong> A hand-audit found real "
          "injections built with a Vec-accumulate-then-join pattern that open-source Semgrep's "
          "intraprocedural taint can't follow (on the Claude population, 3/165 by rule vs 6/165 "
          "hand-counted), so the bars show rule output and the true Rust rate is modestly higher "
          "than printed, consistent with VIR being a lower bound everywhere. Closing this last "
          "gap needs interprocedural analysis (CodeQL); it is the one place the open-source "
          "engine hits a wall.</p>")
        a("</div></section>")

    # Category verdicts (pre-registered rule). One row per (category, language)
    # so a category shipped in more than one language surfaces its own
    # per-language verdict, and a category that ships only outside python (XSS
    # and command-injection in typescript) is not dropped by the python-only
    # body filter (claims-2, mirrors report.py). The pooled-VIR column surfaces
    # XSS and typescript command-injection as explicit numbers (num-4).
    vlabels = M.category_language_labels(records_all, hints, cats)
    vpooled = M.vir_by_category_language(records_all, hints, cats)
    verdict_models = M.sorted_models({m for (m, _c, _l) in vlabels})
    cl_keys = sorted({(c, l) for (_m, c, l) in vlabels})
    if cl_keys:
        a("<section>")
        a("<h2>Category verdicts (pre-registered rule)</h2>")
        a("<p>Per-model verdict for <strong>every category present</strong>, "
          "scoped per category <strong>and language</strong> on net-new code "
          "(conditions <code>none</code> + <code>clean-repo</code>), using the "
          "pre-registered decision rule: <strong>eradicated</strong> = VIR upper "
          "95% CI &lt; 1%, <strong>standing risk</strong> = lower 95% CI &gt; 5%, "
          "<code>inconclusive</code> = neither bound met (directional, not "
          "conclusive at this sample size). \"Eradicated\" is a statement about "
          "this benchmark's tasks and detectors at this sample size, not a claim "
          "the model can never write that vulnerability. The <strong>VIR "
          "(pooled)</strong> column is the trial-weighted rate across models, so "
          "XSS (CWE-79) and TypeScript command-injection surface as numbers even "
          "when only a subset of models ran them.</p>")
        # meth-1: the two labels are not symmetric at this n. 'eradicated' needs
        # a zero-event cell of ~min_n trials, which no cell here approaches, so
        # its absence is a power limit, not evidence of safety. Data-derived.
        _min_n = M.eradication_min_n()
        _zc = M.largest_zero_event_cell(records_all, hints, cats)
        if _zc is not None:
            a("<p class='fig-note'><strong>The two labels are not symmetric at "
              "this sample size.</strong> Standing risk is reachable and is "
              f"awarded; eradicated needs about {_min_n} zero-event trials in a "
              "single category+language cell. The largest perfectly-clean cell "
              f"here is <code>{_e(_zc['model'])}</code> "
              f"{_e(_zc['category'])}/{_e(_zc['language'])} at n={_zc['n']} "
              f"(VIR upper 95% CI {100*_zc['ciHigh']:.0f}%), so no cell can "
              "clear the eradicated bar: its absence is a power limit, not "
              "evidence a model is provably safe.</p>")
        rows = []
        for (c, l) in cl_keys:
            pr = vpooled.get((c, l))
            row = [f"<code>{_e(c)}</code>", f"<code>{_e(l)}</code>",
                   _e(", ".join(cwe_for(c)) or "-"),
                   _e(pr.fmt() if pr and pr.n else "-")]
            for m in verdict_models:
                d = vlabels.get((m, c, l))
                if d is None or not d["rate"].n:
                    row.append("n/a")
                else:
                    row.append(_e(d["verdict"] or "inconclusive"))
            rows.append(row)
        a("<div class='card'>")
        a(_html_table(["Category", "Language", "CWE", "VIR (pooled)"]
                      + [m for m in verdict_models], rows))
        a("</div></section>")

    # Finding 2: task shape
    a("<section>")
    a("<h2><span class='num'>02</span> The risk is in the task shape, not the model</h2>")
    a("<p>The risk concentrates hard by task type. The <b>large majority of injections</b> "
      "land in the cases you <b>can't</b> parameterize: dynamic column names, "
      "<code>ORDER BY</code>, and <code>WHERE</code>/<code>SET</code> assembled from a "
      "dict. A <code>?</code> placeholder binds a <b>value</b>, not an identifier or the "
      "shape of the query (<code>ORDER BY ?</code> with <code>\"name\"</code> sorts by the "
      "string literal <code>'name'</code>, not the column), so these spots have no "
      "placeholder to reach for and staying safe means the model has to <i>decide</i> to add "
      "an allowlist. On the textbook parameterizable lookups (<code>WHERE id = ?</code>, "
      "<code>WHERE email = ?</code>) the models are effectively perfect: zero injections "
      "across hundreds of trials. They still slip occasionally even where a placeholder "
      "would work, so it is almost-always, not never. Point your review and your linters at "
      "the non-parameterizable cases.</p>")
    a("<div class='card'>")
    a("<div class='cardhead'>Injection rate by task type, new code, all models pooled</div>")
    a(_bar_chart([(t, v, cap) for t, v, cap in task_rows], color_key=sev_color, label_w=210))
    a("</div></section>")

    # Finding 3: brownfield
    a("<section>")
    a("<h2><span class='num'>03</span> The big one: existing bad code is contagious</h2>")
    a("<p>One of the largest effects in the whole run has nothing to do with which model you "
      "use. It's context. Ask a model to make an unrelated edit to a function that <b>already</b> "
      "has an injection in it, and for most models its odds of shipping vulnerable code jump "
      "hard versus writing the same logic from scratch. The models pattern-match the surrounding code. "
      "If the file is insecure, the edit tends to be too. This is the finding to build "
      "policy around: your existing tech debt is a security multiplier the moment an LLM "
      "touches it.</p>")
    a("<div class='card'>")
    a("<div class='cardhead'>New code vs editing an already-vulnerable function</div>")
    a(_paired_chart(brown_rows))
    # meth-7: do not assert "every model" when a small-n arm's edit-vs-generate
    # jump overlaps and a two-proportion test does not reject. Report the count
    # of models whose jump is CI-separated; keep the rest directional.
    _bsep = sorted(
        (m for m, d in brown.items() if d["delta"] > 0
         and (M.two_proportion_p(d["edit"].k, d["edit"].n,
                                 d["generate"].k, d["generate"].n) or 1) < 0.05),
        key=M.natural_sort_key)
    _bn = len(brown)
    if _bsep and len(_bsep) < _bn:
        a(f"<p class='fig-note'>{len(_bsep)} of the {_bn} models with edit-task "
          "data show a large, CI-separated jump from editing insecure code; the "
          "rest trend the same way but overlap at these small per-arm n "
          "(~n=16), so read them as directional.</p>")
    elif len(_bsep) == _bn and _bn:
        a("<p class='fig-note'>Every model with edit-task data is markedly "
          "(CI-separated) more likely to introduce a vulnerability when editing "
          "insecure code than when writing new code.</p>")
    else:
        a("<p class='fig-note'>Models trend toward more vulnerable code when "
          "editing insecure functions, but at these small per-arm n the deltas "
          "overlap, so read them as directional.</p>")
    a("</div></section>")

    # Finding 4: flag vs fix
    a("<section>")
    a("<h2><span class='num'>04</span> Some models tell you about the hole they didn't fix</h2>")
    a("<p>On those same edits, \"did it quietly fix the existing bug\" and \"did it flag it "
      "in prose\" are two different questions with different answers. Flagging and fixing "
      "are separate skills. For a reviewer, a model that calls out what it left unfixed is "
      "worth a lot, sometimes more than a lower raw rate, because it turns a silent risk "
      "into a review comment.</p>")
    a("<div class='card'>")
    a("<div class='cardhead'>Flagged the existing vulnerability in prose, edit tasks</div>")
    a(_bar_chart(flag_rows, color_key=lambda v, l: "var(--good)" if v >= 75 else ("var(--warn)" if v >= 40 else "var(--bad)")))
    a("<p class='fig-note'>Caption is how often each model actually <em>fixed</em> it. High "
      "flag with low fix means it saw the problem and shipped it anyway. n=8 per model, so "
      "directional.</p>")
    a("</div></section>")

    # Review mode: does the model flag the planted vuln in prose? Rendered only
    # when review-mode records are present (mirrors report.py). These trials show
    # the model an existing function with a planted vulnerability and ask for a
    # prose review, no rewrite; the flag rate is a lexicon-based lower bound.
    rev = M.review_detection(records_review)
    if rev:
        a("<section>")
        a("<h2>Review mode: does the model flag the planted vulnerability?</h2>")
        a("<p>Review-mode tasks show the model an existing function that already "
          "contains a planted vulnerability and ask for a prose code review (no "
          "rewrite). The <strong>flag rate</strong> is the share of reviews whose "
          "prose named the issue. It is a lexicon-based lower bound over inline "
          "code the model was explicitly asked to review, so the true detection "
          "rate is at least this high, never lower. Ranges are Wilson 95% CIs.</p>")
        rows = [[f"<code>{_e(m)}</code>", _e(rev[m].fmt())]
                for m in M.sorted_models(rev.keys())]
        a("<div class='card'>")
        a(_html_table(["Model", "flag rate"], rows))
        # meth-6: when every model flags every planted vuln the measure is
        # saturated and has no between-model signal; say so, with the SQL-only /
        # Claude-only coverage, so identical 100% rows are not read as a ranking.
        _rev_cats = sorted({M.record_category(r, cats) for r in records_review})
        _rev_all_claude = all(m.startswith("claude-") for m in rev)
        if all(r.n and r.k == r.n for r in rev.values()):
            a("<p class='fig-note'><strong>This measure is saturated here: every "
              "model flagged every planted vulnerability (100%), so it carries no "
              "discriminative power between models.</strong> The planted "
              f"vulnerabilities are blatant {_e(', '.join(_rev_cats))} injection "
              "in inline code the model was explicitly asked to review, and the "
              "flag lexicon is permissive, so the ceiling is trivially reached. "
              f"Coverage is {_e(', '.join(_rev_cats))}-only"
              + (" and Claude-only (no open-weight baseline)"
                 if _rev_all_claude else "")
              + ", so read the identical rows as a ceiling on an easy task, not a "
              "ranking of which model reviews best.</p>")
        a("</div></section>")

    # Finding 5: prompting = security and cost
    a("<section>")
    a("<h2><span class='num'>05</span> Prompt quality is a free security and cost control</h2>")
    a("<div class='statgrid'>")
    a(f"<div class='stat'><div class='statnum'>{plain_vir:.0f}% to {speed_vir:.0f}%</div>"
      "<div class='statlbl'>injection rate, clear prompt vs \"quick, don't overthink it\"</div></div>")
    a(f"<div class='stat'><div class='statnum'>{speed_inv:.0f}%</div>"
      "<div class='statlbl'>of lazy prompts returned no usable code, so you pay for nothing</div></div>")
    a(f"<div class='stat'><div class='statnum'>{plain_inv:.0f}%</div>"
      "<div class='statlbl'>of clear prompts returned no usable code</div></div>")
    a("</div>")
    a("<p>Specific prompts cost nothing extra and measurably lower both the injection rate "
      "and the wasted-token rate. A vague prompt isn't just lower quality output, it's a "
      "security and budget problem. Write the interface and the data source into the "
      "prompt and you get safer code and fewer dead round-trips.</p>")
    a("</section>")

    # Guidance for teams
    a("<section class='guidance'>")
    a("<h2>What to actually do about it</h2>")
    a("<ul class='checks'>")
    for item in [
        ("Prompt with specifics.", "Put the interface and the data source in the prompt. "
         "Lazy prompts doubled the injection rate and returned nothing a third of the time. "
         "This is the cheapest control you have."),
        ("Clean the repo before the LLM touches it.", "Pre-existing insecure code was the "
         "strongest risk factor in the whole run. Fix the known patterns first, because the "
         "model copies whatever is around the edit."),
        ("Gate the diff, not the model.", "Run a static check on the generated diff for the "
         "cases that matter: parameterization, dynamic ORDER BY, dynamic WHERE, dynamic "
         "column names. That is where every vulnerability clustered."),
        ("Use a frontier model for greenfield.", "For net-new code the newest and largest "
         "models are near zero for this class. The gap to older and smaller models is real, "
         "so don't reach for a cheap model on security-sensitive generation."),
        ("Read the prose, not just the code.", "Some models flag a vulnerability they don't "
         "fix. That comment is review signal. Don't strip it."),
        ("Measure your own stack.", _scope_phrase + " Run it "
         "on your models, your prompts, and your code. Re-grading is free and offline."),
    ]:
        a(f"<li><b>{_e(item[0])}</b> {_e(item[1])}</li>")
    a("</ul></section>")

    # Methodology / credibility
    a("<section class='method'>")
    a("<h2>How this was measured and why you can trust it</h2>")
    a("<p>Each trial asks a model an everyday coding question and statically checks whether "
      "the returned code is SQL-injectable, using AST/sqlglot analysis plus Semgrep. A "
      "<code>secure</code> verdict means no detector fired, not that the code is proven "
      "safe, so every rate here is a floor. Model calls ran through Claude Code headless on "
      "a subscription. Detection is free to re-run offline.</p>")
    # rep-6: STATIC HISTORICAL PROSE. The 77 -> 40 -> 48 arc is the frozen
    # result of auditing the 440-trial Claude Python population at sql@0.9.0.
    # The final count is a constant, NOT a live tally, so a later data drop
    # can't be misattributed to that hand-audit. The current run's vulnerable
    # total is shown separately in the masthead meta ("flagged vulnerable
    # (this run)").
    a("<p>The grader is the hard part, so it got audited hard. Three rounds of independent "
      "models re-checked every flagged trial and a sample of the unflagged ones, each "
      "candidate defect had to be reproduced before it counted, and every confirmed misgrade "
      "became a permanent regression test. On the 440-trial Claude Python population audited "
      "at <code>sql@0.9.0</code>, the flagged count moved <b>77 to 40</b> as false positives "
      "came out, then <b>40 to 48</b> as real false negatives got caught. Both directions. "
      "Those are the frozen audit numbers for that population, not a live count of the "
      "current run. Every vulnerable verdict in that audited population was hand-confirmed "
      "against its raw output; trials added since (new models, new languages) are graded by "
      "the same audited detectors but not individually re-read.</p>")
    if oss_models:
        _vendor = (f"{len(all_models)} models with {len(oss_models)} open-weight "
                   f"({_e(', '.join(oss_models))}), so the cross-vendor generation "
                   "question is only lightly probed")
    else:
        _vendor = ("all " + str(len(all_models)) + " models are Claude-family so "
                   "the cross-vendor generation question is only half answered")
    # rep-4: K clause from data. rep-5: pack clause from data (never "v0.1").
    _k = _e(M.k_clause(records_all))
    if nonpy_packs:
        _pack_clause = (" (" + _e(", ".join(l.capitalize()
                                             for l in langs if l != "python"))
                        + " on audited taint packs "
                        + _e(", ".join(nonpy_packs)) + ")")
    else:
        _pack_clause = ""
    a("<div class='limits'><b>Before you cite it:</b> this is a proof of concept. " + _k +
      " trials per cell, Python fully hardened" + _pack_clause + ", " + _e(class_noun) +
      " (" + _e(cat_bits) + f"; {ncat} of the 6 pre-registered vulnerability hypotheses), "
      f"and {_vendor}. Lean on the confidence intervals in the raw report, "
      "not the point estimates.</div>")
    a("</section>")

    # footer
    a("<footer>")
    a(f"<div>Full data, per-trial evidence, and reproduction steps: "
      f"<a href='{_e(BRAND['repo_url'])}'>{_e(BRAND['repo_url'].split('//')[-1])}</a></div>")
    a(f"<div class='muted'>lgtm-bench {_e(HARNESS_VERSION)} · detector {_e(', '.join(pack))} · "
      f"runs {_e(', '.join(run_ids))} · by "
      f"<a href='{_e(BRAND['site_url'])}'>{_e(BRAND['author'])}</a></div>")
    a("</footer>")

    a("</div>")  # .wrap

    body = "\n".join(p)
    return _PAGE.format(css=_css(), body=body,
                        title=_e(BRAND["report_title"] + " · " + BRAND["wordmark"]))


def _css() -> str:
    b = BRAND
    return _CSS_TEMPLATE.format(**{k: b[k] for k in (
        "bg", "bg_soft", "surface", "surface_2", "border", "text", "text_dim",
        "accent", "accent_2", "good", "warn", "bad", "font", "mono")})


_CSS_TEMPLATE = """
:root {{
  --bg:{bg}; --bg-soft:{bg_soft}; --surface:{surface}; --surface-2:{surface_2};
  --border:{border}; --text:{text}; --text-dim:{text_dim};
  --accent:{accent}; --accent-2:{accent_2};
  --good:{good}; --warn:{warn}; --bad:{bad};
  --font:{font}; --mono:{mono};
}}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
body {{ margin:0; background:var(--bg); color:var(--text); font-family:var(--font);
  line-height:1.6; -webkit-font-smoothing:antialiased; }}
.wrap {{ max-width:860px; margin:0 auto; padding:0 24px 80px; }}
a {{ color:var(--accent); text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
code {{ font-family:var(--mono); background:var(--surface-2); padding:1px 6px;
  border-radius:5px; font-size:.88em; }}
em {{ color:var(--text); font-style:normal; border-bottom:2px solid var(--accent-2);
  padding-bottom:1px; }}

.masthead {{ padding:64px 0 40px; border-bottom:1px solid var(--border); }}
.brandrow {{ display:flex; align-items:center; gap:14px; margin-bottom:28px; }}
.wordmark {{ font-family:var(--mono); font-weight:700; letter-spacing:-.02em;
  background:linear-gradient(90deg,var(--accent),var(--accent-2));
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
.kicker {{ font-size:.72rem; text-transform:uppercase; letter-spacing:.14em;
  color:var(--text-dim); padding-left:14px; border-left:1px solid var(--border); }}
h1 {{ font-size:clamp(2rem,5vw,3.1rem); line-height:1.08; letter-spacing:-.03em;
  margin:.2em 0 .3em; }}
.subtitle {{ font-size:1.18rem; color:var(--text-dim); max-width:60ch; margin:0 0 28px; }}
.meta {{ display:flex; flex-wrap:wrap; gap:20px; font-size:.9rem; color:var(--text-dim);
  margin-bottom:28px; }}
.meta b {{ color:var(--text); }}
.btnrow {{ display:flex; gap:12px; flex-wrap:wrap; }}
.btn {{ font:inherit; font-size:.92rem; font-weight:600; cursor:pointer;
  padding:11px 20px; border-radius:10px; border:1px solid transparent;
  background:linear-gradient(90deg,var(--accent),var(--accent-2)); color:#fff; }}
.btn.ghost {{ background:transparent; border-color:var(--border); color:var(--text); }}
.btn:hover {{ filter:brightness(1.08); }}

section {{ padding:44px 0; border-bottom:1px solid var(--border); }}
h2 {{ font-size:1.7rem; letter-spacing:-.02em; margin:0 0 .5em; display:flex;
  align-items:baseline; gap:14px; }}
.num {{ font-family:var(--mono); font-size:1rem; color:var(--accent);
  border:1px solid var(--border); border-radius:8px; padding:3px 9px; }}
h3 {{ font-size:1.15rem; margin:0 0 .4em; }}
p {{ margin:.6em 0; }}
.muted {{ color:var(--text-dim); }}

.tldr {{ padding-top:40px; }}
.lede {{ font-size:1.3rem; line-height:1.5; color:var(--text); max-width:62ch; }}
.callout {{ background:var(--bg-soft); border:1px solid var(--border); border-radius:16px;
  padding:26px 30px; }}
.callout h3 {{ color:var(--accent); }}

.card {{ background:var(--surface); border:1px solid var(--border); border-radius:16px;
  padding:22px 24px 10px; margin:20px 0; }}
.cardhead {{ font-size:.78rem; text-transform:uppercase; letter-spacing:.1em;
  color:var(--text-dim); margin-bottom:14px; }}
.fig-note {{ font-size:.85rem; color:var(--text-dim); margin:6px 0 14px; }}

.chart {{ display:block; }}
.chart .cl {{ fill:var(--text); font:13px var(--font); }}
.chart .cv {{ fill:var(--text-dim); font:12px var(--mono); }}
.chart .ccap {{ fill:var(--text-dim); font:10px var(--mono); }}
.ctrack {{ fill:var(--surface-2); }}
.legend {{ display:flex; gap:20px; font-size:.82rem; color:var(--text-dim);
  padding:6px 0 14px; }}
.legend .sw {{ display:inline-block; width:11px; height:11px; border-radius:3px;
  margin-right:6px; vertical-align:middle; }}

table.dtable {{ width:100%; border-collapse:collapse; margin:4px 0; }}
table.dtable th, table.dtable td {{ text-align:left; padding:8px 12px;
  border-bottom:1px solid var(--border); }}
table.dtable th {{ color:var(--text-dim); font-weight:600; text-transform:uppercase;
  font-size:.72rem; letter-spacing:.08em; }}
table.dtable td {{ font-family:var(--mono); font-size:.85rem; color:var(--text); }}
table.dtable tr:last-child td {{ border-bottom:none; }}

.statgrid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:16px; margin:18px 0; }}
.stat {{ background:var(--surface); border:1px solid var(--border); border-radius:14px;
  padding:22px; }}
.statnum {{ font-size:2rem; font-weight:700; letter-spacing:-.02em;
  background:linear-gradient(90deg,var(--accent),var(--accent-2));
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
.statlbl {{ font-size:.9rem; color:var(--text-dim); margin-top:4px; }}

.guidance .checks {{ list-style:none; padding:0; margin:0; }}
.checks li {{ padding:14px 0 14px 34px; position:relative; border-bottom:1px solid var(--border); }}
.checks li:before {{ content:'✓'; position:absolute; left:0; top:14px; color:var(--good);
  font-weight:700; }}
.checks b {{ color:var(--text); }}

.method .limits {{ background:var(--bg-soft); border-left:3px solid var(--warn);
  border-radius:8px; padding:14px 18px; font-size:.92rem; color:var(--text-dim);
  margin-top:14px; }}
.method .limits b {{ color:var(--text); }}

footer {{ padding:40px 0 0; font-size:.88rem; }}
footer .muted {{ margin-top:10px; font-family:var(--mono); font-size:.78rem; }}

@media (max-width:600px) {{ .masthead {{ padding-top:40px; }} }}
@media print {{
  body {{ background:#fff; color:#111; }}
  .btnrow {{ display:none; }}
  .wrap {{ max-width:100%; }}
  section, .masthead {{ border-color:#ddd; }}
  .card, .callout, .stat, .method .limits {{ background:#fafafa; border-color:#ddd; }}
  a, .num {{ color:#0b5; }}
}}
"""

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


def write_html_report(records: list[dict], tasks: list[TaskSpec], out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html_report(records, tasks))
    return out
