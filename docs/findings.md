# Findings — what we have learned so far

This is the project's working memory. Each entry captures a finding with enough context that a contributor (or future you) can reconstruct the reasoning without re-deriving it.

Findings are listed newest-first. Each links to the underlying scorecards or commits.

---

> **⚠ Status as of 2026-05-09 — Ember v0.1.5 is retired, did not ship.**
> The LHC v0.2 sweep (decontaminated, audit-validated) shows Ember v0.1.5 underperforms its base model (Qwen3-8B) by 0.25 on the production-relevant `current` gap mode (95% CI [-0.46, -0.06]). Per the pre-registered DECISION.md gates, this fails G1-G4 decisively. v0.1.5's apparent advantage on LHC v0.1 was a contamination artifact (`based_on` derivative seeds in training data overlapped exactly with the test scenarios). All Ember leaderboard claims from F-04 and earlier should be treated as **historical**, not authoritative.
>
> Full backstory: [`journal/2026-05-08-external-review-and-decontamination.md`](journal/2026-05-08-external-review-and-decontamination.md) (the review that triggered the rebuild) and [`journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md`](journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md) (the sweep that confirmed the regression). The 48 v0.2 scorecards are at [`evals/results/published/lhc-v0.2/`](../evals/results/published/lhc-v0.2/).

---

## F-05 · LHC v0.2 leaderboard, 8B-class open models (2026-05-09)

LHC v0.2 is the decontaminated benchmark we built after the external review. 24 hand-curated tasks, no `based_on` overlap with anything in `data/seeds/*` or `data/synthetic/*`, 4 gap modes (none / placeholder / neutral / current), stable sha256-seeded gaps, full-prompt-and-response audit trail in every scorecard. All four benchmark-validity gates passed (G9 judge stability, G10 rank inversion, G11 CI discrimination, G13 variance attribution). Manual audit (G12) passed at 0%.

We ran 4 models × 4 gap modes × 3 trials = 48 scorecards, judged by Claude Opus 4.7. Mean across all gap modes (max 2.00):

| Rank | Model | Mean | Notes |
|------|-------|------|-------|
| #1 | **Qwen3-8B base** | **1.413** | The base model Ember was fine-tuned from. Best in class on this benchmark. |
| #2 | Ministral-8B-2512 | 1.351 | Mistral's December 2025 release. Best on resumption (1.281). |
| #3 (tie) | Ember v0.1.5 iter-900 | 1.285 | Our fine-tune. Worse than its own base by 0.128 mean. |
| #3 (tie) | Llama-3.1-8B | 1.285 | Meta's flagship 8B. |

**Per-category breakdown (all gap modes pooled):**

| Model | state_recall | commitment | resumption |
|-------|-------------:|-----------:|-----------:|
| Qwen3-8B base | 1.271 | 1.740 | 1.229 |
| Ministral-8B-2512 | 1.062 | 1.708 | 1.281 |
| Ember v0.1.5 | 1.042 | **1.625** | 1.188 |
| Llama-3.1-8B | 1.177 | 1.531 | 1.146 |

The largest Ember-vs-base regression is on **commitment** (1.625 vs 1.740, Δ -0.115). That is the category v0.1.5's hand-written act-then-narrate seeds were specifically designed to fix. The seeds did not fix it; they appear to have made it worse.

**Deterministic baseline reference:** A 100-line Python parser (no LLM in the forward pass) scored **0.75 on resumption** alone. It scored 2/2 on `resumption_v2_004` (warehouse tracker) and `resumption_v2_008` (the inconsistency-detection task — Ember's archetype nemesis from v0.1's `resumption_004`). For those structured-state tasks specifically, *parsing beats every fine-tuned 8B model we tested*, including Ember. See [`evals/results/published/lhc-v0.2/deterministic-baseline.json`](../evals/results/published/lhc-v0.2/deterministic-baseline.json).

Scorecards: [`evals/results/published/lhc-v0.2/sweep/`](../evals/results/published/lhc-v0.2/sweep/). Full verdict (all 13 gates + decision): [`evals/results/published/lhc-v0.2/verdict.json`](../evals/results/published/lhc-v0.2/verdict.json). Pre-registered methodology: [`evals/v0.2/DECISION.md`](../evals/v0.2/DECISION.md).

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
