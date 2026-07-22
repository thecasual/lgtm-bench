"""Per-trial evidence renderer (audit view).

Emits a human-readable transcript so a reviewer can verify the report against
the underlying trials: for each trial the full prompt, the raw model output,
the code the harness extracted, every detector finding (rule id, message,
line, matched snippet), and the resulting verdict. This is the auditable
ground truth behind every number in `lgtm report`.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional


def _fence(text: str, lang: str = "") -> str:
    # Pick a fence longer than any run of backticks inside the text so model
    # output containing ``` doesn't break the rendering.
    longest = 0
    run = 0
    for ch in text:
        run = run + 1 if ch == "`" else 0
        longest = max(longest, run)
    bar = "`" * max(3, longest + 1)
    return f"{bar}{lang}\n{text}\n{bar}"


def _finding_lines(findings: list[dict]) -> list[str]:
    if not findings:
        return ["- _no findings_"]
    out = []
    for f in findings:
        loc = f" (line {f['line']})" if f.get("line") else ""
        out.append(f"- **{f.get('detector')}** · `{f.get('rule_id')}`{loc}: "
                   f"{f.get('message', '').strip()}")
        snip = (f.get("snippet") or "").strip()
        if snip:
            out.append("  " + _fence(snip, "python").replace("\n", "\n  "))
    return out


def render_trial(r: dict, index: Optional[int] = None) -> str:
    lines: list[str] = []
    head = f"### {'' if index is None else f'{index}. '}`{r['task_id']}` · " \
           f"**{r['model']}** · {r['condition']} · {r['variant_id']}#{r['trial_index']}"
    lines.append(head)
    verdict = r["verdict"].upper()
    badge = {"SECURE": "🟢 SECURE", "VULNERABLE": "🔴 VULNERABLE",
             "INVALID": "⚪ INVALID"}.get(verdict, verdict)
    meta = [f"**Verdict:** {badge}", f"**mode:** {r['mode']}"]
    if r.get("mode") == "edit":
        meta.append(f"**fixed_existing:** {r.get('fixed_existing')}")
        meta.append(f"**flagged_existing:** {r.get('flagged_existing')}")
    if r.get("timing_ms"):
        meta.append(f"**{r['timing_ms']} ms**")
    meta.append(f"**pack:** {r.get('detector_pack_version', '?')}")
    lines.append(" · ".join(meta))
    lines.append(f"**trial_key:** `{r['trial_key']}`")
    lines.append("")

    lines.append("**Prompt**")
    lines.append(_fence(r.get("prompt", "").strip() or "(empty)"))
    lines.append("")

    if r.get("error"):
        lines.append("**Runner error**")
        lines.append(_fence(r["error"].strip()))
        lines.append("")
        return "\n".join(lines)

    lines.append("**Raw model output**")
    lines.append(_fence(r.get("raw_output", "").strip() or "(empty)"))
    lines.append("")

    lines.append("**Extracted code (what the detectors graded)**")
    lines.append(_fence(r.get("extracted_code", "").strip() or "(none extracted)", "python"))
    lines.append("")

    lines.append("**Scan findings**")
    lines.extend(_finding_lines(r.get("findings", [])))
    lines.append("")
    lines.append("---")
    return "\n".join(lines)


def build_evidence(records: list[dict],
                   only_verdict: Optional[str] = None,
                   task_substr: Optional[str] = None,
                   model: Optional[str] = None) -> str:
    recs = list(records)
    if only_verdict:
        recs = [r for r in recs if r["verdict"] == only_verdict]
    if task_substr:
        recs = [r for r in recs if task_substr in r["task_id"]]
    if model:
        recs = [r for r in recs if r["model"] == model]
    # Stable, reviewer-friendly order: task, then model, then condition/variant.
    recs.sort(key=lambda r: (r["task_id"], r["model"], r["condition"],
                             r["variant_id"], r["trial_index"]))

    out: list[str] = ["# lgtm-bench: per-trial evidence\n"]
    counts = Counter(r["verdict"] for r in recs)
    filt = []
    if only_verdict:
        filt.append(f"verdict={only_verdict}")
    if task_substr:
        filt.append(f"task~{task_substr}")
    if model:
        filt.append(f"model={model}")
    out.append(f"- **Trials shown:** {len(recs)}"
               + (f" (filter: {', '.join(filt)})" if filt else ""))
    out.append(f"- **Verdicts:** "
               + ", ".join(f"{v}={counts[v]}" for v in ("secure", "vulnerable", "invalid")
                           if counts.get(v)))
    out.append("")
    out.append("Each entry below shows the exact prompt sent, the raw model "
               "output, the code the harness extracted from it, every detector "
               "finding, and the verdict. This is the ground truth behind "
               "`RESULTS.md` and `docs/export.json`.\n")

    # Quick index
    by_task: dict[str, Counter] = defaultdict(Counter)
    for r in recs:
        by_task[r["task_id"]][r["verdict"]] += 1
    out.append("## Index (verdict counts per task)\n")
    out.append("| Task | secure | vulnerable | invalid |")
    out.append("|---|---|---|---|")
    for task in sorted(by_task):
        c = by_task[task]
        out.append(f"| `{task}` | {c.get('secure', 0)} | "
                   f"{c.get('vulnerable', 0)} | {c.get('invalid', 0)} |")
    out.append("")
    out.append("## Trials\n")
    for i, r in enumerate(recs, 1):
        out.append(render_trial(r, i))
    return "\n".join(out) + "\n"
