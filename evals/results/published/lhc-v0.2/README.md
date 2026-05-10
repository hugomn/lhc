# LHC v0.2 — published scorecards (2026-05-09)

Canonical results from the LHC v0.2 sweep. All files here are tracked in git and cited in the docs.

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

## Headline result

| Rank | Model | Mean (max 2.00) | Notes |
|------|-------|----------------:|-------|
| #1 | **Qwen3-8B base** | **1.413** | The base Ember was fine-tuned from. Won every category. |
| #2 | Ministral-8B-2512 | 1.351 | Best on resumption (1.281). |
| #3 (tie) | Ember v0.1.5 iter-900 | 1.285 | Worse than its own base by 0.128. |
| #3 (tie) | Llama-3.1-8B | 1.285 | Meta's flagship 8B. |

Plus deterministic parser (resumption only): 0.75. Beat all four LLMs on `resumption_v2_004` (warehouse tracker) and `resumption_v2_008` (inconsistency detection) — 2/2 on each.

Full per-category, per-gap-mode breakdown: see [`docs/results.md`](../../../docs/results.md) and [`docs/findings.md`](../../../docs/findings.md) F-05.

## Decision

Per the pre-registered decision table at [`evals/v0.2/DECISION.md`](../../../evals/v0.2/DECISION.md) §6, all G9-G13 (benchmark-validity gates) passed; G1-G4 (Ember-vs-base) failed decisively. The decision matrix routes to:

> **Ember not better than base. STOP the v0.1.5 line. Do not publish v0.1.**

For the full reasoning and what we plan to do next, see [`docs/journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md`](../../../docs/journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md).

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
