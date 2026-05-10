# LHC v0.2 — 8B-class scorecard

> 4 models × 4 gap modes × 3 trials × 24 tasks, judged by Claude Opus 4.7.
> Generated 2026-05-09. Pre-registered methodology at [`evals/v0.2/DECISION.md`](../evals/v0.2/DECISION.md).
> Audit-validated: G9 judge stability passed (1 flip in 120 rejudges, max shift 0.033). G12 manual audit passed (0 disagreements in 12 samples).

## Headline

| Rank | Model | Mean overall (out of 2.00) | Notes |
|------|-------|---------------------------:|-------|
| #1 | **Qwen3-8B base** | **1.413** | The base model Ember was fine-tuned from. Won every category. |
| #2 | Ministral-8B-2512 | 1.351 | Mistral's December 2025 release. Best on resumption (1.281). |
| #3 (tie) | Ember v0.1.5 iter-900 | 1.285 | Our LoRA fine-tune. Worse than its own base by 0.128 mean. |
| #3 (tie) | Llama-3.1-8B | 1.285 | Meta's flagship 8B. |

**The headline is uncomfortable.** Ember v0.1.5 — the model we trained specifically to improve on Qwen3-8B's long-horizon coherence — is *worse* than its base on a clean, decontaminated benchmark. With statistical confidence: the 95% paired-bootstrap CI for the (Ember − Qwen) overall delta on the production-relevant `current` gap mode is **[−0.46, −0.06]** — the *upper bound is negative*.

This contradicts what we believed before today. On the LHC v0.1 benchmark, Ember v0.1.5 appeared to win. That apparent win was a **contamination artifact** — LHC v0.1 task scenarios overlapped exactly with `based_on` derivative seeds in Ember's training data. With the contamination removed, the underlying truth surfaces: the v0.1.5 fine-tune *damaged* base Qwen3-8B's general capability, with the worst hit on the category we tried to fix (commitment).

Per the pre-registered DECISION.md gates, Ember v0.1.5 will not ship.

## By gap mode (overall mean, max 2.00)

The four gap modes test increasing distractor pressure. `none` = no inter-task gap; `placeholder` = the literal placeholder string the training data uses; `neutral` = lorem-ipsum-style filler with no task content; `current` = real-looking agent chatter (production-relevant condition).

| Model | none | placeholder | neutral | current |
|-------|-----:|------------:|--------:|--------:|
| Qwen3-8B base | 1.375 | 1.444 | 1.458 | **1.375** |
| Ministral-8B-2512 | 1.333 | 1.361 | 1.389 | 1.319 |
| Ember v0.1.5 iter-900 | 1.347 | 1.375 | 1.292 | 1.125 |
| Llama-3.1-8B | 1.292 | 1.306 | 1.361 | 1.181 |

**Qwen3-8B is monotonically the most robust** across gap modes. Ember and Llama show the largest drop on `current` (the realistic distractor condition). The bootstrap CI for the (Ember − Qwen) `current`-overall delta is [−0.46, −0.06].

## By category (mean across all gap modes, max 2.00)

| Model | state_recall | commitment | resumption |
|-------|-------------:|-----------:|-----------:|
| Qwen3-8B base | **1.271** | **1.740** | 1.229 |
| Ministral-8B-2512 | 1.062 | 1.708 | **1.281** |
| Ember v0.1.5 iter-900 | 1.042 | 1.625 | 1.188 |
| Llama-3.1-8B | 1.177 | 1.531 | 1.146 |

The biggest Ember regression vs base is on **commitment** (Δ −0.115) — the category v0.1.5's hand-written act-then-narrate seeds were specifically designed to fix. The seeds did not fix it; they made it worse.

## Deterministic baseline (the floor)

A 100-line Python parser with **no LLM in the forward pass** scored **0.75 on resumption** (8 tasks). It detects structured-state markers (`NEXT:`, `[NEXT]`, "next planned action") and surfaces inconsistencies in payloads with conflicting CAPS-DASH-LETTER tokens (e.g. `RECIPE-A` vs `RECIPE-B` in the same loaded state).

The parser scored **2/2 on `resumption_v2_004`** (warehouse pick-pack tracker) and **2/2 on `resumption_v2_008`** (the inconsistency-detection task — v0.2's analog of v0.1's `resumption_004` Ember-killer). For both of those structured-state tasks, *parsing beats every fine-tuned 8B model we tested*, including Ember.

Implication: for production agent workflows where the inter-session state is structured, fine-tuning is the wrong layer. A schema validator + parser does the job better and at zero inference cost. See [`evals/v0.2/deterministic_baseline.py`](../evals/v0.2/deterministic_baseline.py) for the parser, and [`evals/results/published/lhc-v0.2/deterministic-baseline.json`](../evals/results/published/lhc-v0.2/deterministic-baseline.json) for the scorecard.

## All 13 gates (per DECISION.md)

| Gate | Description | Result |
|------|-------------|--------|
| G1 | current overall: Ember ≥ Qwen + 0.20 | ✗ FAIL (Δ −0.250) |
| G2 | current resumption: Ember ≥ Qwen + 0.30 | ✗ FAIL (Δ −0.083) |
| G3 | neutral overall: Ember ≥ Qwen + 0.10 | ✗ FAIL (Δ −0.167) |
| G4 | paired-bootstrap CI lower bound > 0 | ✗ FAIL (CI [−0.46, −0.06]) |
| G5 | current overall: Ministral ≥ Ember + 0.20 | ✗ FAIL (Δ +0.194) |
| G6 | neutral overall: Ministral ≥ Ember + 0.15 | ✗ FAIL (Δ +0.097) |
| G7 | current resumption: Ministral ≥ Ember + 0.30 | ✗ FAIL (Δ +0.083) |
| G8 | No mode shows Ember > Ministral by ≥ 0.10 | ✓ PASS (max +0.014) |
| G9 | Judge stability (rejudge shift < 0.10) | ✓ PASS (max 0.033) |
| G10 | No rank inversions > 2 positions | ✓ PASS (max swap 0) |
| G11 | CIs do not both span ±0.15 | ✓ PASS |
| G12 | Manual audit miss-rate < 5% | ✓ PASS (0%) |
| G13 | SS(model) > SS(gap) | ✓ PASS |

**Decision matrix** routes to: *Ember not better than base. STOP the v0.1.5 line.*

## Methodology

- **Tasks:** 24 hand-curated, decontaminated. No `based_on` overlap with anything in `data/seeds/*` or `data/synthetic/*`. Resumption uses 4 distinct frames (notebook reload / chat-log / handoff log / task-tracker) — no `[SESSION RESUME]` payloads. Frozen at git tag `lhc-v0.2-frozen`. See [`evals/v0.2/AUTHORING.md`](../evals/v0.2/AUTHORING.md).
- **Gap modes:** four-way ablation. Stable sha256-based gap seeding. See [`evals/runners/gap.py`](../evals/runners/gap.py).
- **Trials:** 3 per (model, gap_mode) cell. Paired by (task_id, trial_index) for the bootstrap CIs.
- **Judge:** Claude Opus 4.7. Re-judged 120 random samples in a fresh API session for the G9 audit.
- **Rubric:** binary 2D (correctness ∈ {0,1}, meta_awareness ∈ {0,1}, score = sum). See [`evals/runners/grader.py`](../evals/runners/grader.py).
- **Decision gates:** pre-registered before any model run, in [`evals/v0.2/DECISION.md`](../evals/v0.2/DECISION.md). No goalposts moved after seeing the data.

## Reproducibility

Every result is reproducible end-to-end:

```bash
# 1. Run the sweep (4 models × 4 gap modes × 3 trials = 48 scorecards)
python -m training.sweep_v02 --skip-existing

# 2. Audit (judge stability + manual review)
python evals/v0.2/audit_g9_judge_stability.py --per-model 30
python evals/v0.2/audit_g12_manual.py    # interactive, 12 samples

# 3. Verdict (gates + decision matrix)
python evals/v0.2/analyze.py \
    --scorecards-dir evals/results/published/lhc-v0.2/sweep \
    --audit-results evals/results/published/lhc-v0.2/audit-combined.json
```

All 48 scorecards (with full prompt + full gap + full response stored, not truncated) live at [`evals/results/published/lhc-v0.2/`](../evals/results/published/lhc-v0.2/).

## Why this doc replaced the previous one

The previous version of this doc (kept in git history, last commit before this rewrite) showed an 8B-class leaderboard from LHC v0.1 where Ember v0.1.5 *appeared* to outperform Llama-3.1-8B and approach Ministral-8B-2512. Those numbers are now known to be contamination artifacts — Ember had been trained on derivative seeds of the exact LHC v0.1 test scenarios. See [`docs/findings.md`](findings.md) F-05 and the journal entries at [`docs/journal/`](journal/) for the methodology arc that surfaced the contamination and the rebuild that produced this doc.

## Update cadence

Regenerated whenever the LHC version bumps or new models are added to the comparison. The current doc reflects LHC v0.2 (frozen at git tag `lhc-v0.2-frozen`, commit SHA in the file's git log).
