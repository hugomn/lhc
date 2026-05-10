# LHC v0.2 — 8B-class scorecard

> **Two evaluations, one verdict.** The original sweep (2026-05-09, 4 models × 4 gap modes × 3 trials × 24 tasks, judged by Claude Opus 4.7) compared Ember (local MLX, with `/no_think`) against three OpenRouter models (no `/no_think`). External review flagged the inference-config asymmetry. The matched-inference diagnostic (2026-05-10, n=3 fresh-server-restart trials per cell) re-ran Ember and base Qwen3-8B on the same local MLX path and found a statistical tie. Both evaluations are reported below; the matched-inference comparison is the load-bearing one for the Ember-vs-base verdict.
>
> Pre-registered methodology at [`evals/v0.2/DECISION.md`](../evals/v0.2/DECISION.md). Audit-validated: G9 judge stability passed (1 flip in 120 rejudges, max shift 0.033). G12 manual audit passed (0 disagreements in 12 samples).

## Headline (matched local-MLX inference, n=3 fresh-server trials)

This is the apples-to-apples Ember-vs-base comparison. Same local MLX server, same `/no_think` prefix, same harness, fresh server restart per trial.

| Gap | Ember mean | Qwen-local mean | Δ E−Q | 95% CI (task-bootstrap)¹ |
|---|---:|---:|---:|---|
| `current` | 1.222 | 1.181 | **+0.042** | [−0.139, +0.222] |
| `neutral` | 1.319 | 1.333 | **−0.014** | [−0.139, +0.111] |

**Both CIs cross zero: statistical tie on both gap modes.** Under matched local MLX inference, Ember v0.1.5 is statistically indistinguishable from base Qwen3-8B on LHC v0.2; it does not meet our bar for release ("significant improvement on at least one functionality compared to a same-class model"). Per the pre-registered DECISION.md gates, the v0.1.5 line is retired.

¹ Task-bootstrap CI conditional on the observed 3 restart trials. A hierarchical bootstrap over (task, trial) would be wider, not narrower. Sufficient to reject shipping; not for fine ranking.

## Original 4-model sweep (confounded by inference-config asymmetry)

The original sweep ranked 4 models with mixed inference paths:

| Rank | Model | Mean overall (out of 2.00) | Inference path |
|------|-------|---------------------------:|----------------|
| #1 | **Qwen3-8B base** | **1.413** | OpenRouter, no `/no_think` |
| #2 | Ministral-8B-2512 | 1.351 | OpenRouter |
| #3 (tie) | Ember v0.1.5 iter-900 | 1.285 | local MLX, with `/no_think` |
| #3 (tie) | Llama-3.1-8B | 1.285 | OpenRouter |

The original "Ember − Qwen" delta on `current` overall was −0.250 (95% CI [−0.46, −0.06]). **That CI is no longer credible** — it was inflated by the inference-config asymmetry. About 5/6 of the apparent gap was confound. The matched-inference comparison above is the corrected reading.

The 4-model leaderboard rankings between Ember, Ministral, and Llama are *not* directly comparable to each other either, since Ember's `/no_think` path differs from the OpenRouter models' default. To do those comparisons cleanly would require running the OpenRouter models through the same matched local-MLX path. We did not do that for this cycle (Ministral and Llama are not the load-bearing comparison for the v0.1.5 verdict).

## By gap mode (overall mean, max 2.00)

The four gap modes test increasing distractor pressure. `none` = no inter-task gap; `placeholder` = the literal placeholder string the training data uses; `neutral` = lorem-ipsum-style filler with no task content; `current` = real-looking agent chatter (production-relevant condition).

Original sweep (mixed inference paths — Ember at local MLX with `/no_think`; others at OpenRouter without):

| Model | none | placeholder | neutral | current |
|-------|-----:|------------:|--------:|--------:|
| Qwen3-8B base (OpenRouter) | 1.375 | 1.444 | 1.458 | **1.375** |
| Ministral-8B-2512 (OpenRouter) | 1.333 | 1.361 | 1.389 | 1.319 |
| Ember v0.1.5 iter-900 (MLX) | 1.347 | 1.375 | 1.292 | 1.125 |
| Llama-3.1-8B (OpenRouter) | 1.292 | 1.306 | 1.361 | 1.181 |

Matched-inference (Ember and Qwen-local both via local MLX with `/no_think`, n=3 fresh-server-restart trials per cell):

| Model | neutral mean | neutral stdev | current mean | current stdev |
|-------|-------------:|--------------:|-------------:|--------------:|
| Qwen3-8B base (local MLX) | 1.333 | 0.125 | 1.181 | 0.024 |
| Ember v0.1.5 iter-900 (local MLX) | 1.319 | 0.064 | 1.222 | 0.087 |

Under matched inference, the cross-trial stdev (0.02–0.13 on overall mean) is comparable to the Ember-vs-base point delta. That is what "statistical tie" means in practice: the variance from running the same model on the same harness with a fresh MLX server start is the same scale as the difference between the two models.

## By category (mean across all gap modes, max 2.00 — original sweep, mixed inference)

| Model | state_recall | commitment | resumption |
|-------|-------------:|-----------:|-----------:|
| Qwen3-8B base | **1.271** | **1.740** | 1.229 |
| Ministral-8B-2512 | 1.062 | 1.708 | **1.281** |
| Ember v0.1.5 iter-900 | 1.042 | 1.625 | 1.188 |
| Llama-3.1-8B | 1.177 | 1.531 | 1.146 |

These per-category means are from the original sweep and are subject to the same inference-config caveat: the Ember-vs-base per-category gaps are inflated by `/no_think` asymmetry. The matched-inference per-category breakdown for `current` (n=3 trial means per task):

| Category | Ember | Qwen-local | Δ E−Q |
|---|---:|---:|---:|
| state_recall | 1.042 | 0.875 | +0.167 |
| commitment | 1.417 | 1.458 | −0.042 |
| resumption | 1.208 | 1.208 | 0.000 |

## Deterministic baseline (the floor)

A 100-line Python parser with **no LLM in the forward pass** scored **0.75 on resumption** (8 tasks). It detects structured-state markers (`NEXT:`, `[NEXT]`, "next planned action") and surfaces inconsistencies in payloads with conflicting CAPS-DASH-LETTER tokens (e.g. `RECIPE-A` vs `RECIPE-B` in the same loaded state).

The parser scored **2/2 deterministically on `resumption_v2_004`** (warehouse pick-pack tracker) and **2/2 deterministically on `resumption_v2_008`** (inconsistency-detection — v0.2's analog of v0.1's `resumption_004` Ember-killer). On both of those structured-state tasks, every fine-tuned 8B model we tested (Ember, Qwen3-8B base, Ministral-8B-2512, Llama-3.1-8B) averaged below 2.0 across 12 cells per task. Some LLM cells hit 2/2; none of the LLMs match the parser's deterministic *mean*.

Implication: for production agent workflows where the inter-session state is structured, fine-tuning is the wrong layer. A schema validator + parser does the job better and at zero inference cost. See [`evals/v0.2/deterministic_baseline.py`](../evals/v0.2/deterministic_baseline.py) for the parser, and [`evals/results/published/lhc-v0.2/deterministic-baseline.json`](../evals/results/published/lhc-v0.2/deterministic-baseline.json) for the scorecard.

## Original 13-gate verdict (per DECISION.md, confounded sweep)

The pre-registered gates were computed against the original sweep. The G1–G4 results below are based on the inference-confounded comparison and **the underlying CI is no longer credible**. They are kept here as the verdict that the pre-registered methodology produced; the matched-inference correction is above the gate table, not woven into it.

| Gate | Description | Result (original sweep, confounded) |
|------|-------------|--------|
| G1 | current overall: Ember ≥ Qwen + 0.20 | ✗ FAIL (Δ −0.250) |
| G2 | current resumption: Ember ≥ Qwen + 0.30 | ✗ FAIL (Δ −0.083) |
| G3 | neutral overall: Ember ≥ Qwen + 0.10 | ✗ FAIL (Δ −0.167) |
| G4 | paired-bootstrap CI lower bound > 0 | ✗ FAIL (CI [−0.46, −0.06] — retracted) |
| G5 | current overall: Ministral ≥ Ember + 0.20 | ✗ FAIL (Δ +0.194) |
| G6 | neutral overall: Ministral ≥ Ember + 0.15 | ✗ FAIL (Δ +0.097) |
| G7 | current resumption: Ministral ≥ Ember + 0.30 | ✗ FAIL (Δ +0.083) |
| G8 | No mode shows Ember > Ministral by ≥ 0.10 | ✓ PASS (max +0.014) |
| G9 | Judge stability (rejudge shift < 0.10) | ✓ PASS (max 0.033) |
| G10 | No rank inversions > 2 positions | ✓ PASS (max swap 0) |
| G11 | CIs do not both span ±0.15 | ✓ PASS |
| G12 | Manual audit miss-rate < 5% | ✓ PASS (0%) |
| G13 | SS(model) > SS(gap) | ✓ PASS |

The original decision matrix routed to *"Ember not better than base. STOP the v0.1.5 line."* The matched-inference correction strengthens the "not better" half (now with proper CI behind it) and **withdraws the "stop because worse" framing** — the underlying claim is that v0.1.5 is statistically indistinguishable from base, not that it regresses.

## Methodology

- **Tasks:** 24 hand-curated, decontaminated. No `based_on` overlap with anything in `data/seeds/*` or `data/synthetic/*`. Resumption uses 4 distinct frames (notebook reload / chat-log / handoff log / task-tracker) — no `[SESSION RESUME]` payloads. Frozen at git tag `lhc-v0.2-frozen`. See [`evals/v0.2/AUTHORING.md`](../evals/v0.2/AUTHORING.md) and the decontamination manifest at [`evals/v0.2/manifest.json`](../evals/v0.2/manifest.json).
- **Gap modes:** four-way ablation. **Stable sha256-based gap seeding** (replaces process-randomized `hash()` from v0.1, which was identified as a bug in round 1 of external review). See [`evals/runners/gap.py`](../evals/runners/gap.py).
- **Trials:** 3 per (model, gap_mode) cell. Paired by (task_id, trial_index) for the bootstrap CIs.
- **Judge:** Claude Opus 4.7. Re-judged 120 random samples in a fresh API session for the G9 audit.
- **Rubric:** binary 2D (correctness ∈ {0,1}, meta_awareness ∈ {0,1}, score = sum). See [`evals/runners/grader.py`](../evals/runners/grader.py).
- **Decision gates:** pre-registered before any model run, in [`evals/v0.2/DECISION.md`](../evals/v0.2/DECISION.md). No goalposts moved after seeing the data.
- **Matched-inference diagnostic:** added 2026-05-10 in response to round-2 external review which flagged the inference-config asymmetry. Per round-4 reviewer wording: in our MLX-LM server setup on Apple Silicon, outputs were stable within a single server session but varied across fresh server starts. Replications restart the server between trials.

## Reproducibility

Every result is reproducible end-to-end:

```bash
# 1. Run the original sweep (4 models × 4 gap modes × 3 trials = 48 scorecards)
python -m training.sweep_v02 --skip-existing

# 2. Run the matched-inference diagnostic (Ember + Qwen3-8B both via local MLX,
#    n=3 fresh-server-restart trials per cell)
python evals/v0.2/diagnostic_local_qwen.py        # Qwen-local trial 1
python evals/v0.2/diagnostic_qwen_replicate.py    # Qwen-local trials 2 + 3
python evals/v0.2/diagnostic_ember_rerun.py       # Ember trial 1 (matched config)
python evals/v0.2/diagnostic_ember_replicate.py   # Ember trials 2 + 3

# 3. Audit (judge stability + manual review)
python evals/v0.2/audit_g9_judge_stability.py --per-model 30
python evals/v0.2/audit_g12_manual.py    # interactive, 12 samples

# 4. Verdicts
python evals/v0.2/analyze.py \
    --scorecards-dir evals/results/published/lhc-v0.2/sweep \
    --audit-results evals/results/published/lhc-v0.2/audit-combined.json
python evals/v0.2/diagnostic_compare.py
```

All scorecards (with full prompt + full gap + full response stored, not truncated) live at [`evals/results/published/lhc-v0.2/`](../evals/results/published/lhc-v0.2/) — original sweep under `sweep/`, matched-inference diagnostic under `diagnostic-ember-rerun/` and `diagnostic-local-qwen/`.

## Why this doc replaced the previous one

The previous version of this doc (kept in git history, last commit before this rewrite) showed an 8B-class leaderboard from LHC v0.1 where Ember v0.1.5 *appeared* to outperform Llama-3.1-8B and approach Ministral-8B-2512. Those numbers are now known to be contamination artifacts — Ember had been trained on derivative seeds of the exact LHC v0.1 test scenarios. See [`docs/findings.md`](findings.md) F-05 and the journal entries at [`docs/journal/`](journal/) for the methodology arc that surfaced the contamination, the rebuild that produced the LHC v0.2 numbers above, and the matched-inference diagnostic that corrected the v0.2 sweep verdict from "Ember regresses" to "Ember statistically indistinguishable from base."

## Update cadence

Regenerated whenever the LHC version bumps or new models are added to the comparison. The current doc reflects LHC v0.2 (frozen at git tag `lhc-v0.2-frozen`, commit SHA in the file's git log).
