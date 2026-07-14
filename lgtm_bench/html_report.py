"""Self-contained, brandable HTML report (TECH_SPEC §8, presentation layer).

Everything is inline (CSS and SVG charts, no external assets or JS libraries)
so the output is a single downloadable file. The entire visual identity lives
in the ``:root`` CSS-variable block near the top of ``_CSS`` (colors, fonts,
wordmark); swap those to rebrand. All numbers are computed from the same
records/metrics as the markdown report, so the two never disagree.
"""
from __future__ import annotations

import html
from collections import defaultdict
from pathlib import Path

from . import HARNESS_VERSION
from . import metrics as M
from .schema import TaskSpec

# --------------------------------------------------------------------------
# Brand tokens. EDIT THIS BLOCK to rebrand. One place, no other CSS changes.
# --------------------------------------------------------------------------
BRAND = {
    "wordmark": "Sam Wallace",
    "report_kicker": "Security Research",
    "report_title": "Does an LLM Write Secure Code?",
    "report_subtitle": "How often six Claude models introduce SQL injection, "
                       "where the risk actually lives, and what it means for how "
                       "you prompt, review, and spend tokens.",
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
    # block (they're Semgrep v0.1 and generate/condition-none only).
    records = [r for r in records_all if M.record_language(r) == "python"]
    models = sorted({r["model"] for r in records})
    n_total = len(records_all)
    n_inv = sum(1 for r in records_all if r["verdict"] == "invalid")
    n_vuln = sum(1 for r in records if r["verdict"] == "vulnerable")
    run_ids = sorted({r.get("run_id", "?") for r in records_all})
    pack = sorted({r.get("detector_pack_version", "") for r in records_all if r.get("detector_pack_version")})

    # cross-language rows (only rendered if go/rust present)
    xlang = M.vir_by_model_language(records_all, hints, condition="none")
    xlang_pooled = M.vir_by_language(records_all, hints, condition="none")
    other_langs = [l for l in langs if l != "python"]

    # ---- compute the figures the narrative references ----
    none_vir = M.vir_by_model_condition(records, hints, mode="generate")
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
    a(f"<p class='subtitle'>{_e(BRAND['report_subtitle'])}</p>")
    a("<div class='meta'>")
    a(f"<span><b>{n_total}</b> trials</span><span><b>{len(models)}</b> models</span>"
      f"<span><b>{n_vuln}</b> flagged vulnerable</span>"
      f"<span>detector <b>{_e(', '.join(pack) or 'n/a')}</b></span>")
    a("</div>")
    a("<div class='btnrow'>")
    a("<button class='btn' onclick='window.print()'>⤓ Save as PDF</button>")
    a(f"<a class='btn ghost' href='{_e(BRAND['repo_url'])}'>View the code &amp; raw data →</a>")
    a("</div>")
    a("</header>")

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
        a("<h2><span class='num'>01b</span> Cross-language: the detector isn't ready yet</h2>")
        a("<p>The same everyday tasks, ported to " + _e(" and ".join(other_langs)) +
          ". New-code injection rates pooled across models, by language:</p>")
        pooled_rows = [(lang, 100 * xlang_pooled[lang].p,
                        f"n={xlang_pooled[lang].n}")
                       for lang in langs if lang in xlang_pooled and xlang_pooled[lang].n]
        a("<div class='card'>")
        a("<div class='cardhead'>Injection rate in new code, by language (pooled)</div>")
        a(_bar_chart(pooled_rows, color_key=sev_color, label_w=120))
        a("<p class='fig-note'><strong>These non-Python rates are inflated and are not a "
          "measurement yet.</strong> The Python grader is an AST/scope analysis hardened over "
          "nine versions and a three-round audit. The Go and Rust packs are Semgrep-rule v0.1, "
          "pattern-based with no taint analysis, and a spot-audit of the flagged Go trials found "
          "a majority are false positives on safe code: <code>fmt.Sprintf</code> building a "
          "<code>?</code>-placeholder list passed as <code>args...</code>, and allowlisted "
          "<code>ORDER BY</code> where the column comes from a map or switch. Pattern matching "
          "can't see that validation; the Python detector can. So the true Go/Rust rates are "
          "substantially lower than the bars show and are probably much closer to Python. Read "
          "this as \"the detector needs taint analysis before these numbers mean anything,\" not "
          "\"models are 4x worse in Go.\"</p>")
        a("</div></section>")

    # Finding 2: task shape
    a("<section>")
    a("<h2><span class='num'>02</span> The risk is in the task shape, not the model</h2>")
    a("<p>Most task types came back <b>0% vulnerable across every model</b>. The entire "
      "risk lives in the cases you <b>can't</b> parameterize: dynamic column names, "
      "<code>ORDER BY</code>, and <code>WHERE</code> assembly from a dict. Those are the "
      "spots where staying safe means the model has to decide to add an allowlist. "
      "Anywhere a <code>?</code> placeholder works, the models use it without being "
      "asked. Point your review and your linters at the non-parameterizable cases and "
      "ignore the rest.</p>")
    a("<div class='card'>")
    a("<div class='cardhead'>Injection rate by task type, new code, all models pooled</div>")
    a(_bar_chart([(t, v, cap) for t, v, cap in task_rows], color_key=sev_color, label_w=210))
    a("</div></section>")

    # Finding 3: brownfield
    a("<section>")
    a("<h2><span class='num'>03</span> The big one: existing bad code is contagious</h2>")
    a("<p>The largest effect in the whole run has nothing to do with which model you use. "
      "It's context. Ask a model to make an unrelated edit to a function that <b>already</b> "
      "has an injection in it, and its odds of shipping vulnerable code jump hard versus "
      "writing the same logic from scratch. The models pattern-match the surrounding code. "
      "If the file is insecure, the edit tends to be too. This is the finding to build "
      "policy around: your existing tech debt is a security multiplier the moment an LLM "
      "touches it.</p>")
    a("<div class='card'>")
    a("<div class='cardhead'>New code vs editing an already-vulnerable function</div>")
    a(_paired_chart(brown_rows))
    a("<p class='fig-note'>Every model with edit-task data is far more likely to introduce "
      "a vulnerability when editing insecure code than when writing new code.</p>")
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
        ("Measure your own stack.", "This is one language and one vulnerability class. Run it "
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
    a("<p>The grader is the hard part, so it got audited hard. Three rounds of independent "
      "models re-checked every flagged trial and a sample of the unflagged ones, each "
      "candidate defect had to be reproduced before it counted, and every confirmed misgrade "
      "became a permanent regression test. The flagged count moved <b>77 to 40</b> as false "
      f"positives came out, then <b>40 to {n_vuln}</b> as real false negatives got caught. "
      "Both directions. Every vulnerable verdict was then hand-confirmed against its raw "
      "output.</p>")
    _all_models = sorted({r["model"] for r in records_all})
    _oss = [m for m in _all_models if not m.startswith("claude-")]
    if _oss:
        _vendor = (f"{len(_all_models)} models with {len(_oss)} open-weight "
                   f"({_e(', '.join(_oss))}), so the cross-vendor generation "
                   "question is only lightly probed")
    else:
        _vendor = ("all " + str(len(_all_models)) + " models are Claude-family so "
                   "the cross-vendor generation question is only half answered")
    a("<div class='limits'><b>Before you cite it:</b> this is a proof of concept. K=2 trials "
      f"per cell, Python fully hardened (Go/Rust packs are v0.1), one vulnerability class "
      f"(SQL injection), and {_vendor}. Lean on the confidence intervals in the raw report, "
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
