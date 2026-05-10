# LHC v0.2 — published scorecards (2026-05-09, diagnostic added 2026-05-10)

Canonical results from the LHC v0.2 sweep plus the round-3+4 apples-to-apples diagnostic. All files here are tracked in git and cited in the docs.

> **2026-05-10 update.** The original sweep below compared Ember (local MLX, with `/no_think`) against Qwen3-8B base (OpenRouter, no `/no_think`). External review flagged this as an inference-config confound. We re-ran both Ember and base Qwen3-8B locally under matched MLX inference at n=3 with fresh server starts per trial. The result: **Ember v0.1.5 is statistically indistinguishable from base Qwen3-8B under matched local inference; it does not meet the bar for release.** See `diagnostic-ember-rerun/` and `diagnostic-local-qwen/` for scorecards, and `docs/journal/2026-05-10-mlx-replication-and-diagnostic-closure.md` for the full reasoning.

## Contents

```
lhc-v0.2/
├── README.md                       # this file
├── sweep/                          # 4 models × 4 gap modes × 3 trials = 48 scorecards
│   ├── ember-v015-iter900__none__trial1.json
│   ├── ember-v015-iter900__none__trial2.json
│   ├── ember-v015-iter900__none__trial3.json
│   ├── ember-v015-iter900__placeholder__trial1.json
│   ├── … (45 more)
│   └── qwen3-8b__current__trial3.json
├── diagnostic-ember-rerun/         # Ember under matched local-MLX, capped cache, n=3 fresh-server trials
│   ├── ember-v015-iter900__current__trial1.json
│   ├── ember-v015-iter900__current__trial2.json
│   ├── ember-v015-iter900__current__trial3.json
│   ├── ember-v015-iter900__neutral__trial1.json
│   ├── ember-v015-iter900__neutral__trial2.json
│   └── ember-v015-iter900__neutral__trial3.json
├── diagnostic-local-qwen/          # base Qwen3-8B under same matched config, n=3 fresh-server trials
│   ├── qwen3-8b-local__current__trial1.json
│   ├── qwen3-8b-local__current__trial2.json
│   ├── qwen3-8b-local__current__trial3.json
│   ├── qwen3-8b-local__neutral__trial1.json
│   ├── qwen3-8b-local__neutral__trial2.json
│   └── qwen3-8b-local__neutral__trial3.json
├── audit-g9.json                   # judge stability rejudge: 120 samples, 1 flip (0.83%)
├── audit-g12.json                  # manual audit: 12 samples, 0 disagreements (after revision)
├── audit-combined.json             # G9 + G12 merged, fed into the analyzer
├── verdict-final.json              # final 13-gate analyzer output + decision matrix routing
└── deterministic-baseline.json     # 100-line Python parser baseline (resumption-only, 8 tasks)
```

## Naming convention

```
<model_slug>__<gap_mode>__trial<N>.json
```

Where:
- `model_slug` ∈ `{ember-v015-iter900, qwen3-8b, ministral-8b, llama-31-8b}`
- `gap_mode` ∈ `{none, placeholder, neutral, current}`
- `N` ∈ `{1, 2, 3}` (trial index, paired across models for the bootstrap CI)

This naming convention is the contract between the sweep driver (`training/sweep_v02.py`) and the analyzer (`evals/v0.2/analyze.py`). Don't rename files here without updating both.

## How these were generated

```bash
# 1. Sweep — 48 scorecards
python -m training.sweep_v02 --skip-existing

# 2. Audit
python evals/v0.2/audit_g9_judge_stability.py --per-model 30
python evals/v0.2/audit_g12_manual.py    # interactive, 12 samples

# 3. Verdict
python evals/v0.2/analyze.py \
    --scorecards-dir evals/results/v0.2/sweep \
    --audit-results evals/results/v0.2/audit-combined.json \
    --output evals/results/v0.2/verdict-final.json
```

The deterministic baseline is independent:

```bash
python evals/v0.2/deterministic_baseline.py \
    --output evals/results/v0.2/deterministic-baseline.json
```

The matched-inference diagnostic (Ember and base Qwen3-8B both via local MLX, capped prompt cache, fresh server start per trial):

```bash
# Run the comparison side (already done — scorecards in published/)
python evals/v0.2/diagnostic_local_qwen.py        # Qwen-local trial 1
python evals/v0.2/diagnostic_qwen_replicate.py    # Qwen-local trials 2 + 3
python evals/v0.2/diagnostic_ember_rerun.py       # Ember trial 1 (matched config)
python evals/v0.2/diagnostic_ember_replicate.py   # Ember trials 2 + 3

# Then compute the n=3 paired comparison with bootstrap CI
python evals/v0.2/diagnostic_compare.py
```

## Headline result

The original sweep produced this leaderboard (all-cells mean, max 2.00):

| Rank | Model | Mean | Notes |
|------|-------|----------------:|-------|
| #1 | **Qwen3-8B base** | **1.413** | OpenRouter, no `/no_think` |
| #2 | Ministral-8B-2512 | 1.351 | OpenRouter |
| #3 (tie) | Ember v0.1.5 iter-900 | 1.285 | local MLX, with `/no_think` |
| #3 (tie) | Llama-3.1-8B | 1.285 | OpenRouter |

**This ranking is confounded by inference-config asymmetry between Ember and the OpenRouter models.** The 2026-05-10 diagnostic re-ran Ember and base Qwen3-8B locally under matched MLX inference at n=3 with fresh server starts:

| Gap | Ember mean (n=3) | Qwen-local mean (n=3) | Δ E−Q | 95% CI (task-bootstrap)¹ |
|---|---:|---:|---:|---|
| `current` | 1.222 | 1.181 | **+0.042** | [−0.139, +0.222] |
| `neutral` | 1.319 | 1.333 | **−0.014** | [−0.139, +0.111] |

Both CIs cross zero: **statistical tie** on both gap modes.

¹ Task-bootstrap, conditional on the observed 3 restart trials. A hierarchical bootstrap over (task, trial) would be wider, not narrower. Sufficient to reject shipping; not for fine ranking.

Plus deterministic parser (resumption only): 0.75. Beat all four LLMs on `resumption_v2_004` (warehouse tracker) and `resumption_v2_008` (inconsistency detection) — 2/2 on each.

Full per-category, per-gap-mode breakdown: see [`docs/results.md`](../../../docs/results.md) and [`docs/findings.md`](../../../docs/findings.md) F-05.

## Decision

Per the pre-registered decision table at [`evals/v0.2/DECISION.md`](../../../evals/v0.2/DECISION.md) §6, all G9-G13 (benchmark-validity gates) passed. The Ember-vs-base gates (G1-G4) initially failed using the confounded comparison; the matched-inference diagnostic shows the apparent regression was inflated by inference-config asymmetry. The honest decision under the round-4 reviewer's required wording:

> **Under matched local MLX inference, Ember v0.1.5 is statistically indistinguishable from base Qwen3-8B on LHC v0.2; it does not meet the bar for release.**

For the original verdict and how it was rebuilt across rounds 2-4 of external review, see:
- [`docs/journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md`](../../../docs/journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md)
- [`docs/journal/2026-05-10-mlx-replication-and-diagnostic-closure.md`](../../../docs/journal/2026-05-10-mlx-replication-and-diagnostic-closure.md)

## Reproducibility

All scorecards include:
- `prompt_messages` — the exact assistant-input messages (setup + gap + probe)
- `gap_messages` — just the gap messages (so you can verify gap content)
- `gap_mode`, `gap_estimated_tokens` — gap-mode metadata
- `response_full` — the model's complete response (not truncated)
- `judge_reasoning` — the raw JSON the judge returned
- `correctness`, `meta_awareness`, `score` — the parsed judge scores

To independently re-judge any sample, you can pull `expected_behavior` from the corresponding task YAML at `evals/v0.2/tasks/<category>/<task_id>.yaml` and feed it + `response_full` to any judge of your choice.

To recompute the bootstrap CIs and gates from scratch:

```bash
python evals/v0.2/analyze.py --scorecards-dir evals/results/published/lhc-v0.2/sweep
```
