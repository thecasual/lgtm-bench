# Related work: how lgtm-bench sits in the recent literature

Five studies from roughly the last year measure the same thing this benchmark
does: how often large language models emit insecure code. They use different
scopes (single function vs whole application), different graders (static
analysis vs live exploits), and different prompts (security-critical vs
ordinary). Read together, they draw a consistent picture, and lgtm-bench lands
exactly where that picture predicts: at the conservative end, because our metric
is a strict lower bound on single-function, benign-prompt generations.

This document exists so a reader can check our numbers against independent work
without taking our word for anything. Every figure below is from the cited
source; every lgtm-bench figure is reproducible from `results-published/` via
`lgtm detect` (no model calls).

## The five

1. **Veracode, GenAI Code Security Report (2025, updated Spring 2026).** Over 100
   LLMs on benign, security-relevant coding tasks across Java, Python, C#, and
   JavaScript. Headline: **45% of generated samples introduced an OWASP Top 10
   vulnerability.** Broken out by class, **SQL injection failed ~20% of the time
   while cross-site scripting failed ~86% of the time** (roughly 12-13% of XSS
   samples were secure). The Spring 2026 update reports the gap did not close as
   models got more capable. Industry white paper.
   arXiv: n/a. https://www.veracode.com/blog/spring-2026-genai-code-security/

2. **SafeGenBench (Cheng et al., arXiv:2506.05692, Jun 2025).** An automatic
   benchmark that grades generated code with both static application security
   testing (SAST) and an LLM judge, across common development scenarios and
   vulnerability types. Headline: under zero-shot prompting the average security
   pass rate is **37.44%**, i.e. roughly **62% of generated code carried a
   vulnerability**, and several state-of-the-art models still score poorly. This
   is the closest methodological cousin to lgtm-bench (static detection over
   generated snippets). https://arxiv.org/abs/2506.05692

3. **SecureAgentBench / SecureVibeBench (arXiv:2509.22097, Sep 2025).** Agentic
   "vibe coding" tasks that require multi-file edits in real repositories, graded
   for both functionality and security. Headline: the strongest configuration
   tested, SWE-agent driving **Claude Sonnet 4.5, produced code that was both
   functional and secure only 23.8% of the time.** https://arxiv.org/abs/2509.22097

4. **Is Vibe Coding Safe? / SUSVIBES (arXiv:2512.03262, Dec 2025).** 200
   feature-request tasks from real open-source projects that led human
   programmers to vulnerable implementations. Headline: SWE-Agent with **Claude 4
   Sonnet was 61% functionally correct but only 10.5% secure** (about 89% of the
   functionally correct solutions were still exploitable). Critically, they also
   found that **augmenting the request with vulnerability hints did not mitigate
   the problem** on these large tasks. https://arxiv.org/abs/2512.03262

5. **Understanding the (In)Security of Vibe-Coded Applications
   (arXiv:2606.23130, Jun 2026).** A qualitative field study of applications
   built by AI agents. It catalogs recurring failure patterns, placeholder logic,
   unfiltered input, and secret exposure, and attributes them to systematic agent
   limitations: context/memory loss over long trajectories and insufficient
   security knowledge. https://arxiv.org/abs/2606.23130

## How the numbers compare

Our pooled introduction rate is **15.6% (1 in 6), a strict lower bound**, over
benign single-function prompts that never mention security, across ten models
(strong Claude models near 0% pull the pool down; our mid-tier models sit at
15-25%, on top of everyone else's range).

| Study | Task scope | Grader | Headline insecure rate |
| --- | --- | --- | --- |
| lgtm-bench (this repo) | single function, benign prompt | static (lower bound) | 15.6% pooled; 0-24% by model |
| Veracode 2025/2026 | single task, security-relevant | SAST | 45% overall; SQL ~20%, XSS ~86% |
| SafeGenBench (2506.05692) | scenario snippet | SAST + LLM judge | ~62% |
| SecureAgentBench (2509.22097) | multi-file repo task | live exploit + tests | 76.2% not both-secure-and-correct |
| SUSVIBES (2512.03262) | real-world feature request | live exploit + tests | 89.5% of correct code insecure |
| Vibe-Coded (In)Security (2606.23130) | whole application | manual audit | qualitative, "pervasive" |

The magnitudes look far apart until you account for scope, and then they line up:

- **Task size explains most of the spread.** The high numbers (62%, 76%, 89%)
  come from whole-application or multi-file agentic tasks graded by running real
  exploits. Our number is per-function, single-shot, and static-only. A static
  lower bound on one small function *should* sit well below a live-exploit rate
  on a whole app. Same direction, different denominator.
- **Where the scope matches, we agree closely.** Veracode's per-class split is
  the clearest apples-to-apples comparison, and it mirrors ours almost exactly:
  SQL is the solved reflex (Veracode ~20% fail; our strong models ~0-4%, pooled
  ~17%) while XSS is the blind spot (Veracode ~86% fail; our weaker models 35-43%,
  strong models still 0%). Two independent graders, same SQL-vs-XSS shape.
- **Our mid-tier model numbers land inside their ranges.** Both SecureAgentBench
  and SUSVIBES ran Claude Sonnet-class models and found them insecure on the
  large-task majority; our controlled cut puts `claude-sonnet-4-5` at 17% (SQL),
  35% (XSS), 13.5% (command injection) on small tasks. Consistent tier, consistent
  direction.

## How lgtm-bench extends this work

Each of the five leaves a gap this benchmark is built to fill.

1. **Benign prompts, not security-relevant ones.** SafeGenBench, SUSVIBES, and
   the Veracode set prompt tasks that are already flagged as security-critical, or
   reconstruct scenarios known to produce vulnerabilities. lgtm-bench measures the
   *introduction rate on ordinary prompts that never mention security* ("sort
   products by a column", "greet the user by name"), which is the actual condition
   a developer who is just rubber-stamping output is in. VIR as a strict lower
   bound is a deliberately conservative, benign-condition metric none of the five
   report directly.

2. **The within-vendor model lever, isolated.** The prior work compares vendors,
   or model vs no-model. None isolate the spread *inside one vendor's lineup on
   identical tasks*. We show a 10x gap (`opus-4-8` at 2% vs `sonnet-4-5` at 24% on
   the same Python SQL tasks), which is the single most actionable fact for a user
   whose tool silently picks the model for them.

3. **The prompt-phrasing effect, with same-model before/after pairs.** We show a
   one-line tone change ("keep it short, don't overthink it") roughly doubles the
   rate and deletes a guard the model writes on the calm prompt. This is a
   controlled variant sweep, not an aggregate. See `docs/examples.md`.

4. **The agent wrapper named as part of the system under test.** SecureAgentBench
   and SUSVIBES run agents but treat the agent as the subject. We separate model
   from harness and show the *same task* flipping between a clean-room headless
   run (vulnerable) and a context-rich interactive session (secure), making the
   wrapper's contribution explicit rather than baked in. See `docs/examples.md`.

5. **Fully offline reproducibility.** Every number here regenerates from stored
   raw outputs with no model calls (`lgtm detect`), with versioned detector packs
   and a resumable store, so a skeptic can re-grade the exact population.

## One tension we take seriously

SUSVIBES found that adding vulnerability hints to the request **did not** help on
their large real-world tasks. We found a one-line safety hint drove the rate to
zero on the (smaller, single-shot) tasks where we tried it. These are not in
conflict; they bracket a boundary. On a single function generated in one shot, a
hint sits right next to the code and fires. On a long multi-file agent trajectory,
the hint is diluted and lost to the context/memory limits that
arXiv:2606.23130 documents. The honest, combined takeaway is narrower than
"just ask it to check": asking helps for small, single-shot generations and
should not be trusted to carry through a large agentic build. lgtm-bench measures
the former regime; SUSVIBES and SecureAgentBench measure the latter.

## References

- Veracode. *2025 GenAI Code Security Report* and *Spring 2026 GenAI Code
  Security Update*. https://www.veracode.com/blog/spring-2026-genai-code-security/
- Cheng et al. *SafeGenBench: A Benchmark Framework for Security Vulnerability
  Detection in LLM-Generated Code.* arXiv:2506.05692, 2025.
  https://arxiv.org/abs/2506.05692
- *SecureAgentBench / SecureVibeBench: Benchmarking Secure Code Generation under
  Realistic Vulnerability Scenarios.* arXiv:2509.22097, 2025.
  https://arxiv.org/abs/2509.22097
- *Is Vibe Coding Safe? Benchmarking Vulnerability of Agent-Generated Code in
  Real-World Tasks (SUSVIBES).* arXiv:2512.03262, 2025.
  https://arxiv.org/abs/2512.03262
- *Understanding the (In)Security of Vibe-Coded Applications.* arXiv:2606.23130,
  2026. https://arxiv.org/abs/2606.23130

Earlier foundational work this benchmark also builds on, for completeness (older
than a year): Pearce et al., "Asleep at the Keyboard?" (IEEE S&P 2022,
arXiv:2108.09293); Perry, Srivastava, Kumar, Boneh, "Do Users Write More Insecure
Code with AI Assistants?" (ACM CCS 2023, arXiv:2211.03622); Bhatt et al., "Purple
Llama CyberSecEval" (arXiv:2312.04724, 2023); BaxBench (ICML 2025,
arXiv:2502.11844).
