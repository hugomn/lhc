# Findings — what we have learned so far

This is the project's working memory. Each entry captures a finding with enough context that a contributor (or future you) can reconstruct the reasoning without re-deriving it.

Findings are listed newest-first. Each links to the underlying scorecards or commits.

---

> **⚠ Status as of 2026-05-10 — Ember v0.1.5 is retired, did not ship.**
> Under matched local MLX inference, Ember v0.1.5 is statistically indistinguishable from base Qwen3-8B on LHC v0.2; it does not meet the bar for release. The original sweep (2026-05-09) compared Ember (local MLX, with `/no_think`) against base Qwen3-8B (OpenRouter, no `/no_think`); external review flagged this as an inference-config confound. The 2026-05-10 diagnostic re-ran both models locally under matched config at n=3 with fresh server starts: Δ E−Q on `current` = +0.042 (95% CI [−0.139, +0.222]); Δ on `neutral` = −0.014 (95% CI [−0.139, +0.111]). Both CIs cross zero. v0.1.5's apparent advantage on LHC v0.1 was a contamination artifact (`based_on` derivative seeds in training data overlapped exactly with the test scenarios). All Ember leaderboard claims from F-04 and earlier should be treated as **historical**, not authoritative.
>
> Full backstory across four review rounds: [`journal/2026-05-08-external-review-and-decontamination.md`](journal/2026-05-08-external-review-and-decontamination.md) (round 1: contamination + hash-seed bug); [`journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md`](journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md) (sweep verdict); [`journal/2026-05-10-mlx-replication-and-diagnostic-closure.md`](journal/2026-05-10-mlx-replication-and-diagnostic-closure.md) (rounds 2–4: inference confound, MLX replication observation, final framing). All scorecards (sweep + diagnostic) at [`evals/results/published/lhc-v0.2/`](../evals/results/published/lhc-v0.2/).

---

## F-05 · LHC v0.2 leaderboard, 8B-class open models (2026-05-09, revised 2026-05-10)

LHC v0.2 is the decontaminated benchmark we built after the round-1 external review. 24 hand-curated tasks, no `based_on` overlap with anything in `data/seeds/*` or `data/synthetic/*`, 4 gap modes (none / placeholder / neutral / current), stable sha256-seeded gaps, full-prompt-and-response audit trail in every scorecard. All four benchmark-validity gates passed (G9 judge stability, G10 rank inversion, G11 CI discrimination, G13 variance attribution). Manual audit (G12) passed at 0%.

### The original confounded leaderboard (2026-05-09)

We ran 4 models × 4 gap modes × 3 trials = 48 scorecards, judged by Claude Opus 4.7. Mean across all gap modes (max 2.00):

| Rank | Model | Mean | Inference path |
|------|-------|------|-------|
| #1 | **Qwen3-8B base** | **1.413** | OpenRouter, no `/no_think` |
| #2 | Ministral-8B-2512 | 1.351 | OpenRouter |
| #3 (tie) | Ember v0.1.5 iter-900 | 1.285 | local MLX, with `/no_think` |
| #3 (tie) | Llama-3.1-8B | 1.285 | OpenRouter |

**Round-2 external review flagged this leaderboard as confounded.** Ember ran through local MLX with the slowlit `/no_think` system prefix; the OpenRouter models had no such prefix. Different inference setups, not just different weights.

### The matched-inference diagnostic (2026-05-10)

We re-ran Ember v0.1.5 iter-900 and base Qwen3-8B both via local MLX, both with `/no_think`, capped prompt cache, n=3 fresh-server-start trials per cell:

| Gap | Ember mean (n=3) | Qwen-local mean (n=3) | Δ E−Q | 95% CI (task-bootstrap)¹ |
|---|---:|---:|---:|---|
| `current` | 1.222 | 1.181 | **+0.042** | [−0.139, +0.222] |
| `neutral` | 1.319 | 1.333 | **−0.014** | [−0.139, +0.111] |

Both CIs cross zero. **Statistical tie on both gap modes.** Yesterday's "Ember regresses by 0.25, CI [−0.46, −0.06]" was inflated by inference-config asymmetry; about 5/6 of that gap was confound.

¹ Task-bootstrap CI conditional on the observed 3 restart trials. A hierarchical bootstrap over (task, trial) would be wider, not narrower. Sufficient to reject shipping; not for fine ranking.

### Round-4 reviewer's required wording

> Under matched local MLX inference, Ember v0.1.5 is statistically indistinguishable from base Qwen3-8B on LHC v0.2; it does not meet the bar for release.

Two earlier claims are explicitly **withdrawn**:
- "Ember demonstrably regresses against base." — was inference confound.
- "v0.1.5 collapses to confident-wrong terse style on `state_recall_v2_004`." — was a within-session caching artifact; across fresh server starts, Ember scores [1, 0, 2] on the same task.

### MLX replication observation

In our MLX-LM server setup on Apple Silicon, outputs were stable within a single server session but varied across fresh server starts. We have not isolated the source (could be MLX-LM server, Metal kernels, cache state, sampling defaults, warmup, or process init). The narrow, defensible claim: **benchmark replications of MLX-served models should restart the server between trials or explicitly state they are within-session repeats.** The original sweep's "byte-identical n=3 trials" was a within-session repeat, not three independent samples.

### Deterministic baseline reference

A 100-line Python parser (no LLM in the forward pass) scored **0.75 on resumption** alone. It scored 2/2 on `resumption_v2_004` (warehouse tracker) and `resumption_v2_008` (the inconsistency-detection task — Ember's archetype nemesis from v0.1's `resumption_004`). For those structured-state tasks specifically, *parsing beats every fine-tuned 8B model we tested*. See [`evals/results/published/lhc-v0.2/deterministic-baseline.json`](../evals/results/published/lhc-v0.2/deterministic-baseline.json).

Scorecards: [`evals/results/published/lhc-v0.2/sweep/`](../evals/results/published/lhc-v0.2/sweep/) (original) and [`evals/results/published/lhc-v0.2/diagnostic-ember-rerun/`](../evals/results/published/lhc-v0.2/diagnostic-ember-rerun/) + [`diagnostic-local-qwen/`](../evals/results/published/lhc-v0.2/diagnostic-local-qwen/) (matched-inference). Original 13-gate verdict (with the now-retracted CI on G4): [`evals/results/published/lhc-v0.2/verdict-original-confounded.json`](../evals/results/published/lhc-v0.2/verdict-original-confounded.json). Matched-inference verdict (corrected): [`evals/results/published/lhc-v0.2/verdict-matched-inference.json`](../evals/results/published/lhc-v0.2/verdict-matched-inference.json). Pre-registered methodology: [`evals/v0.2/DECISION.md`](../evals/v0.2/DECISION.md).

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
