# lgtm-bench

A benchmark for measuring **how often LLMs introduce security vulnerabilities when handling
ordinary developer requests** — the code that "looks good to me" in review but carries a
latent bug.

lgtm-bench measures three things:

1. **Vulnerability introduction rate** — asked a benign question ("write a function that
   fetches a user by email"), how often does the model produce vulnerable code?
2. **Sensitivity & reproducibility** — how much does that rate change across paraphrasings
   of the same request, and across repeated runs of the identical prompt?
3. **Context contamination** — does the model get worse when the repo it works in already
   contains insecure code?

The first vertical is **SQL query generation / SQL injection** (Python + sqlite/psycopg).
Detection is fully static (Semgrep + AST/sqlglot) — deterministic and free to run. Model
calls ride an Anthropic subscription via Claude Code headless mode.

**Read the full design:** [docs/TECH_SPEC.md](docs/TECH_SPEC.md)

## Status

Design phase — the tech spec is the current deliverable. Implementation milestones (M1–M4)
are laid out in the spec.
