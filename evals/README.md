# LHC — Long-Horizon Coherence eval suite

The first open benchmark for agent coherence across long context gaps.

See [`docs/eval-suite.md`](../docs/eval-suite.md) for the full methodology.

## Layout

```
evals/
├── tasks/         # 30 task specifications (10 per category)
│   ├── state_recall/
│   ├── commitment/
│   └── resumption/
├── runners/       # the eval harness
│   ├── lhc.py     # main entry point
│   ├── client.py  # OpenAI-compatible model client
│   └── grader.py  # rubric-based scoring
└── results/       # versioned scorecards (large outputs gitignored)
    └── published/ # canonical baseline results
```

## Run

```bash
# Score any OpenAI-compatible endpoint
python -m evals.runners.lhc \
    --model kimi-k2-6 \
    --base-url https://api.moonshot.ai/v1 \
    --api-key $MOONSHOT_API_KEY

# Score Ember once it is hosted
python -m evals.runners.lhc \
    --model ember-v0.1 \
    --base-url https://api.cinderlabs.ai/v1 \
    --api-key $CINDER_API_KEY
```

## Task format

Each task is a YAML file:

```yaml
id: state_recall_001
category: state_recall
description: |
  Agent is told to track three competing priorities. After 200 unrelated
  tool calls, asked which is the highest priority.
gap_tokens: ~8000
setup:
  - role: user
    content: |
      I need you to keep track of three things in priority order:
      1. Ship the migration by Friday
      2. ...
gap: synthetic_noise_001.jsonl
probe:
  - role: user
    content: What is the highest priority right now?
expected_behavior: |
  Agent must correctly identify "ship the migration by Friday" as priority
  one, without being re-prompted or shown the original list.
```

## Grading rubric

See `docs/eval-suite.md` for the full 0–4 scoring rubric.
