# Findings — what we have learned so far

This is the project's working memory. Each entry captures a finding with enough context that a contributor (or future you) can reconstruct the reasoning without re-deriving it.

Findings are listed newest-first. Each links to the underlying scorecards or commits.

---

## F-04 · Cross-model contrast confirms three distinct failure modes (2026-05-08)

We ran 3 trials × 12 tasks against three flagship models, all judged uniformly by Sonnet 4.6:

| Model | Overall | Correctness | Meta-awareness |
|---|---|---|---|
| Kimi K2.6 | 1.39 | **0.97** | 0.42 |
| Claude Sonnet 4.6 | **1.44** | 0.89 | **0.56** |
| DeepSeek V4 Pro | 1.42 | 0.89 | 0.53 |

Each model has a distinct failure pattern:

- **Sonnet** dominates **commitment** tasks (1.75 / 2.00) but sometimes ignores resumption work entirely (skipped resumption_001 and resumption_002 silently in 2/3 trials).
- **DeepSeek V4 Pro** dominates **resumption** tasks (1.75 / 2.00) but sometimes deploys to production despite an explicit "needs my approval" rule (commitment_001 failed in 2/3 trials).
- **K2.6** has the highest correctness across the board but the lowest meta-awareness — see F-03 for the full implication.

Per-task scorecards: `evals/results/v2-rubric/{sonnet-judge,sonnet-target,deepseek-target}-*.json`.

---

## F-03 · Executor-vs-narrator pattern (2026-05-07)

K2.6 has a stable signature on LHC: high correctness (~97%), low meta-awareness (~42%). Tracing individual responses revealed why — the model executes tasks correctly without narrating that it is doing so. It applies a British-English style rule but does not say "per your earlier rule"; it picks up the next workflow section but does not say "the intro is already done."

This is a real model behavior pattern, not a judge artifact. Confirmed by:

- The Sonnet judge agreed with the K2.6-self-judge on the same responses (cross-judge validation in F-02).
- Trace runs of three different m=0 cases (state_recall_001, commitment_002, resumption_002) all show the same behavior — perfect execution, zero narration.

This is the gap Ember v0.1 is being trained to close. A model with the same correctness but with explicit metacognitive framing would be both more correct *and* more legible. The training target for Ember is to lift meta-awareness from ~0.42 → ≥0.70 without dropping correctness below 0.95.

---

## F-02 · Self-judging is not significantly biased on this rubric (2026-05-07)

To check whether K2.6-self-judge inflated its own scores, we re-ran the same 3 K2.6 trials with Sonnet 4.6 as judge.

| Dimension | K2.6 self-judge | Sonnet judge | Δ |
|---|---|---|---|
| Correctness | 0.972 | 0.972 | 0.000 |
| Meta-awareness | 0.500 | 0.417 | -0.083 |
| Overall | 1.473 | 1.390 | -0.083 |

Both judges agree on correctness exactly. Sonnet is marginally stricter on meta-awareness (-0.08), but disagreements between judges go in *both* directions per-task — not a systematic self-leniency bias.

Implication: the binary 2D rubric is robust enough that a self-judge baseline is acceptable for early development. We still publish all numbers cross-judged by Sonnet for fairness.

---

## F-01 · The gap-bleed bug and why ambiguous probes are a feature (2026-05-07)

`resumption_003` initially failed correctness in one of the 12-task runs because the model interpreted the ambiguous probe ("Pick this up.") as referring to a dependabot alerts question that happened to land near the end of the gap, instead of the SESSION RESUME payload at the top.

This is not a model bug. The probe ambiguity is the whole test — does the agent ground "this" in the working memory it was given, or in the most recent message it can attach to? The harness was leaking that test by allowing gap content to end on an open user question that competed with the probe.

Fix shipped: `gap.py` now trims trailing user messages from the gap so it always ends on an assistant turn. This eliminates the unintended referential-ambiguity attack while keeping the intended ambiguity in the probe itself.

We separately considered adding an explicit "back to original work" closing beat to the gap. Tested it across 3 trials — no measurable improvement, scores stayed within noise. Reverted. Smaller change is better.

Commit: `evals/runners/gap.py` — trailing-user trim only.

---

## How to add a finding

When you learn something non-obvious — a bug fix, a design tradeoff that took a debate, an unexpected scorecard result — add an entry here.

Format:
```
## F-NN · One-sentence headline (YYYY-MM-DD)

What happened, what we tried, what we concluded, what changed.
Link to the scorecard or commit that grounds the claim.
```

Findings stay in the doc forever. They are the institutional memory of the project.
