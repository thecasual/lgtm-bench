# lgtm-bench

A benchmark for measuring **how often LLMs introduce security vulnerabilities when handling
ordinary developer requests** — the code that "looks good to me" in review but carries a
latent bug.

lgtm-bench measures five things:

1. **Vulnerability introduction rate** — asked a benign question ("write a function that
   fetches a user by email"), how often does the model produce vulnerable code?
2. **Sensitivity & reproducibility** — how much does that rate change across paraphrasings
   of the same request, and across repeated runs of the identical prompt?
3. **Context contamination** — does the model get worse when the repo it works in already
   contains insecure code?
4. **Remediation behavior** — when editing existing vulnerable code for an unrelated reason,
   does the model silently fix the issue, flag it, ignore it, or make it worse?
5. **Model-generation gap** — are these rates a property of LLMs in general, or only of the
   newest frontier models? (frontier vs. older vs. open-weight)

The end deliverable is a data-backed **"State of Vibe Coding"** write-up testing six
pre-registered hypotheses: three vulnerability classes modern models may have effectively
*eradicated* (SQL injection, weak password hashing, unsafe deserialization) and three they
plausibly still *introduce* (insecure randomness for secrets, path traversal, command
injection).

The first vertical is **SQL query generation / SQL injection** (Python + sqlite/psycopg).
Detection is fully static (Semgrep + AST/sqlglot) — deterministic and free to run. Model
calls ride an Anthropic subscription via Claude Code headless mode.

**Read the full design:** [docs/TECH_SPEC.md](docs/TECH_SPEC.md)

## Status

Spec finalized (v1.0) — ready to build. Implementation milestones (M1–M6) are laid out in
the spec.
