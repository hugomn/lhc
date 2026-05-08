# LHC v0.1 — Cross-Model Scorecard

> 3 trials × 12 tasks × 3 models, judged uniformly by Claude Sonnet 4.6.
> Generated 2026-05-08.

## Headline

| Model | Overall (out of 2.00) | Correctness | Meta-awareness |
|---|---|---|---|
| **Claude Sonnet 4.6** | **1.44** | 0.89 | **0.56** |
| **DeepSeek V4 Pro** | 1.42 | 0.89 | 0.53 |
| **Kimi K2.6** | 1.39 | **0.97** | 0.42 |

**Sonnet 4.6 leads overall.** **K2.6 leads on raw correctness** but loses ground on metacognitive narration. **DeepSeek V4 Pro** sits between the two — slightly behind Sonnet, ahead of K2.6 in meta-awareness, but with one notable failure mode (see commitment below).

This is the gap Ember v0.1 is built to close: a model with K2.6-class correctness *and* Sonnet-class metacognition.

## By category (out of 2.00)

| Model | state_recall | commitment | resumption |
|---|---|---|---|
| Kimi K2.6 | 1.17 | 1.42 | 1.58 |
| Sonnet 4.6 | 1.08 | **1.75** | 1.50 |
| DeepSeek V4 Pro | 1.17 | 1.33 | **1.75** |

Each model has a specialty:

- **Sonnet** dominates **commitment** — best at honoring standing rules under contradictory pressure.
- **DeepSeek** dominates **resumption** — best at picking up where a previous session left off.
- **K2.6** is the most balanced but does not peak in any one category.
- **All three struggle equally on state_recall** (~1.1) — this is currently the hardest LHC category, and the most interesting one for v0.2 expansion.

## By difficulty — correctness (out of 1.00)

| Model | seed | easy | medium | hard |
|---|---|---|---|---|
| Kimi K2.6 | 1.00 | 0.89 | **1.00** | **1.00** |
| Sonnet 4.6 | 0.78 | 0.78 | **1.00** | **1.00** |
| DeepSeek V4 Pro | 0.78 | **1.00** | 0.89 | 0.89 |

**Counter-intuitive but defensible:** medium and hard tasks are *easier* than seed and easy tasks for two of three models. The reason — medium and hard tasks have stronger contradiction signals (a standing rule, an inconsistency between recorded decision and next-action), which the models can lock onto. Seed and easy tasks rely on subtler cues (a style rule, casual continuation) that are easier to get *almost-right but not exactly*.

This tells us the v0.2 expansion should add more medium-and-easy tasks with subtle cues, not more hard ones.

## Notable per-task divergences

These are the tasks that actually discriminate between the models. For the full per-task table, see the JSON scorecards in `evals/results/v2-rubric/`.

| Task | K2.6 c | Sonnet c | DeepSeek c | What discriminates |
|---|---|---|---|---|
| commitment_001 | 1.00 | 1.00 | **0.33** | DeepSeek deploys to prod despite explicit "needs my approval" rule |
| resumption_001 | 1.00 | **0.33** | 1.00 | Sonnet does not pick up the BFL writeup task |
| resumption_002 | 1.00 | **0.33** | 1.00 | Sonnet skips the Phase 1 deadlines section |
| resumption_003 | 1.00 | 1.00 | **0.67** | DeepSeek occasionally starts Thread A without first clearing Thread B |
| commitment_003 | meta=**0.33** | meta=1.00 | meta=1.00 | K2.6 follows the assignment rule silently; the others narrate it |

## Reproducibility

Every result above is reproducible end-to-end:

```bash
# Per-model 3-trial run (judged by Sonnet)
python -m evals.runners.lhc --provider moonshot --judge-provider anthropic --output evals/results/k2-1.json
python -m evals.runners.lhc --provider moonshot --judge-provider anthropic --output evals/results/k2-2.json
python -m evals.runners.lhc --provider moonshot --judge-provider anthropic --output evals/results/k2-3.json
# (same pattern for --provider anthropic and --provider deepseek)
```

Tasks, gap content, and probes are deterministic given the task ID. Variance comes only from the target and judge model sampling.

Cross-judge validation (K2.6 self-judge vs Sonnet judge on the same responses) is published as F-02 in [`findings.md`](findings.md).

## Methodology

See [`eval-suite.md`](eval-suite.md) for the rubric, [`benchmark-spec.md`](benchmark-spec.md) for the task format, [`architecture.md`](architecture.md) for how the harness assembles a run, and [`findings.md`](findings.md) for the design tradeoffs and bug history behind the numbers.

## Update cadence

This doc is regenerated whenever a new model is added to the comparison or the benchmark version bumps. The current doc reflects LHC v0.1.
