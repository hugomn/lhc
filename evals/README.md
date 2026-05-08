# LHC — Long-Horizon Coherence eval suite

The first open benchmark for agent coherence across long context gaps.

See [`docs/eval-suite.md`](../docs/eval-suite.md) for the methodology, [`docs/benchmark-spec.md`](../docs/benchmark-spec.md) for the formal spec, and [`docs/architecture.md`](../docs/architecture.md) for how the harness works end-to-end.

## Layout

```
evals/
├── tasks/         # 12 task specifications (3 categories × 4 difficulty tiers)
│   ├── state_recall/
│   ├── commitment/
│   └── resumption/
├── runners/       # the eval harness
│   ├── lhc.py     # main entry point
│   ├── client.py  # OpenAI-compatible model client
│   ├── gap.py     # deterministic gap generator
│   ├── grader.py  # binary 2D rubric scorer
│   └── trace.py   # verbose single-task tracer
└── results/       # versioned scorecards (large outputs gitignored)
    └── published/ # canonical baseline results
```

## Run

Keys live in `.env` (gitignored). Copy `.env.example` to `.env` and fill in the values you have.

```bash
# Score Kimi K2.6 with Sonnet as the judge (recommended cross-judge config)
python -m evals.runners.lhc --provider moonshot --judge-provider anthropic

# Dry-run: print the assembled message sequence for the first task
python -m evals.runners.lhc --provider moonshot --dry-run

# Limit to N tasks (debugging)
python -m evals.runners.lhc --provider moonshot --limit 1

# Score Sonnet against itself
python -m evals.runners.lhc --provider anthropic --judge-provider anthropic

# Score a locally-served Ember once trained
python -m evals.runners.lhc --provider slowlit

# Trace one task end-to-end (target call, judge call, score) for debugging
python -m evals.runners.trace --task resumption_003 --provider moonshot --judge-provider anthropic

# Override anything explicitly
python -m evals.runners.lhc \
    --model kimi-k2.6 \
    --base-url https://api.moonshot.ai/v1 \
    --api-key sk-xxx
```

Supported providers: `moonshot`, `openai`, `anthropic`, `deepseek`, `slowlit`.

## Task format

Each task is a YAML file. See [`docs/benchmark-spec.md`](../docs/benchmark-spec.md) for the formal spec. Minimal example:

```yaml
id: state_recall_002
category: state_recall
difficulty: easy

description: |
  Agent is given a small piece of state in setup. After ~6000 tokens of
  unrelated chatter, asked to act on the state.

setup:
  - role: user
    content: |
      Heads up: we use the alias "Magnify" for the new competitor. Note it.

probe:
  - role: user
    content: What do we know about Magnify?

expected_behavior: |
  Correctness=1 if the agent recognizes "Magnify" as the alias from earlier
  and responds appropriately (either by surfacing what was said or asking
  for more info on the same alias).
  Correctness=0 if the agent treats "Magnify" as unfamiliar.

  Meta-awareness=1 if the agent explicitly references the earlier alias
  setup ("you mentioned earlier...", "the alias we set up...").
```

## Grading rubric

Binary 2D — correctness `0/1`, meta-awareness `0/1`. See [`docs/eval-suite.md`](../docs/eval-suite.md#scoring--binary-2d-rubric) for the full definition and the rationale for binary over 0–4.

## Reproducibility

Every published scorecard is the mean of 3 independent trials. The gap content, task ordering, and judge prompt are all deterministic — only the model sampling introduces variance.

Cross-judge validation results live in [`docs/findings.md`](../docs/findings.md) (F-02).
