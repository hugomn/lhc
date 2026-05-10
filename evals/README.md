# LHC — Long-Horizon Coherence eval suite

The first open benchmark for agent coherence across long context gaps. Currently at **LHC v0.2** (decontaminated, gap-mode ablation, audit-validated).

For methodology see [`docs/eval-suite.md`](../docs/eval-suite.md), for the formal task spec see [`docs/benchmark-spec.md`](../docs/benchmark-spec.md), for the harness flow see [`docs/architecture.md`](../docs/architecture.md), and for the current cross-model scorecard see [`docs/results.md`](../docs/results.md).

## Layout

```
evals/
├── tasks/             # LHC v0.1 tasks (12, historical — see caveat in docs/findings.md)
│   ├── state_recall/
│   ├── commitment/
│   └── resumption/
├── v0.2/              # LHC v0.2 — current canonical benchmark
│   ├── tasks/         # 24 hand-curated, decontaminated tasks (8 per category)
│   ├── AUTHORING.md   # how to add new v0.2 tasks
│   ├── DECISION.md    # pre-registered decision gates and matrix
│   ├── analyze.py     # 13-gate analyzer (verdict generator)
│   ├── build_banned_overlap.py    # contamination-check tooling
│   ├── banned_overlap.json        # extracted contamination footprint of v0.1 training data
│   ├── audit_g9_judge_stability.py    # automated rejudge audit
│   ├── audit_g12_manual.py            # interactive manual audit
│   └── deterministic_baseline.py      # 100-line parser baseline (no LLM)
├── runners/           # the harness
│   ├── lhc.py         # main entry point — supports both v0.1 and v0.2 tasks
│   ├── client.py      # OpenAI-compatible model client (with retry)
│   ├── gap.py         # 4-mode deterministic gap generator (sha256-seeded)
│   ├── grader.py      # binary 2D rubric scorer
│   └── trace.py       # verbose single-task tracer
└── results/           # versioned scorecards (most gitignored, published/ tracked)
    └── published/
        ├── lhc-v0.2/  # CURRENT canonical results (see its README.md)
        ├── v0.1/      # historical baseline scorecards
        ├── v0.1.5/    # historical Ember v0.1.5 scorecards
        └── 8b-class-leaderboard/  # historical 8B-class comparison on LHC v0.1
```

## Run the canonical sweep (LHC v0.2)

Keys live in `.env` (gitignored). Copy `.env.example` to `.env` and fill in the values you have. The published v0.2 sweep needs `OPENROUTER_API_KEY` (for Qwen3-8B, Ministral-8B, Llama-3.1-8B) and `ANTHROPIC_API_KEY` (for the Opus 4.7 judge).

```bash
# Single trial — one model × one gap mode × one task (smoke test)
python -m evals.runners.lhc \
    --provider openrouter \
    --model qwen/qwen3-8b \
    --judge-provider anthropic \
    --gap-mode current \
    --lhc-version 0.2 \
    --tasks-dir evals/v0.2/tasks \
    --limit 1 \
    --output /tmp/smoke.json

# Full sweep — 4 models × 4 gap modes × 3 trials = 48 scorecards (~3 hours, ~$5)
python -m training.sweep_v02 --skip-existing

# Audit
python evals/v0.2/audit_g9_judge_stability.py --per-model 30        # judge-stability rejudge
python evals/v0.2/audit_g12_manual.py                                # interactive manual review

# Verdict (computes all 13 gates + applies the decision matrix)
python evals/v0.2/analyze.py \
    --scorecards-dir evals/results/published/lhc-v0.2/sweep \
    --audit-results evals/results/published/lhc-v0.2/audit-combined.json
```

For the deterministic-parser baseline (no LLM, resumption only):

```bash
python evals/v0.2/deterministic_baseline.py \
    --output evals/results/v0.2/deterministic-baseline.json
```

## Useful one-offs

```bash
# Dry-run: print the assembled message sequence for the first task
python -m evals.runners.lhc \
    --provider openrouter --model qwen/qwen3-8b \
    --gap-mode neutral --tasks-dir evals/v0.2/tasks \
    --dry-run

# Trace one v0.2 task end-to-end (target call, judge call, score)
python -m evals.runners.trace --task resumption_v2_008 \
    --provider openrouter --model qwen/qwen3-8b --judge-provider anthropic

# Run only a subset of models or gap modes
python -m training.sweep_v02 --models ember-v015-iter900,qwen3-8b --gap-modes current

# Override everything explicitly (any OpenAI-compatible endpoint)
python -m evals.runners.lhc \
    --model some-model \
    --base-url https://api.example.com/v1 \
    --api-key sk-xxx \
    --judge-provider anthropic
```

Supported providers: `moonshot`, `openai`, `anthropic`, `deepseek`, `openrouter`, `slowlit` (local MLX server).

## Gap modes (LHC v0.2 only)

The `--gap-mode` flag controls what intervening content goes between setup and probe:

| Mode | Content | What it tests |
|------|---------|---------------|
| `none` | empty (no gap) | pure capability with no distractor |
| `placeholder` | the literal training-data placeholder string | whether the model has memorized the literal placeholder pattern |
| `neutral` | lorem-ipsum-style filler | attention distance with no plausible task content |
| `current` | real-looking agent chatter (16-block pool) | behavior under realistic distractor pressure |

The default is `current` (the v0.1 behavior). The four-way ablation lets us distinguish "model is bad at long context" from "model is hijacked by gap-style content."

## Task format

A v0.2 task at `evals/v0.2/tasks/<category>/<task_id>.yaml`. (v0.1 tasks at `evals/tasks/<category>/...` follow the same schema.)

```yaml
id: state_recall_v2_001
category: state_recall
difficulty: seed
description: |
  Hospital triage shift. The user establishes which condition codes
  auto-escalate to red-tag. After ~6k tokens of unrelated shift chatter,
  the agent is asked which incoming patient gets red-tag.

setup:
  - role: system
    content: |
      You are an autonomous triage coordinator for the Ridgewood General ED.
      You apply standing protocols to incoming patients.
  - role: user
    content: |
      Standing protocol for tonight's shift: auto-escalate to red-tag any
      patient with chest pain + dyspnea, GCS under 9, active major bleeding,
      or suspected stroke within 4h.

probe:
  - role: user
    content: |
      EMS just rolled in a 62yo male, GCS 7 after a fall. What tag?

expected_behavior: |
  CORRECTNESS: 1 if the agent assigns red-tag (GCS < 9 trigger).
  META_AWARENESS: 1 if the agent explicitly references the standing protocol.
```

For the full spec see [`docs/benchmark-spec.md`](../docs/benchmark-spec.md).

## Grading rubric

Binary 2D — correctness `0/1`, meta-awareness `0/1`, total `0/1/2`. See [`docs/eval-suite.md`](../docs/eval-suite.md#scoring--binary-2d-rubric) for the full definition and the rationale for binary over 0–4. Judge prompt lives at [`runners/grader.py:JUDGE_SYSTEM_PROMPT`](runners/grader.py).

## Reproducibility (v0.2)

Every v0.2 scorecard stores: `prompt_messages` (full message list sent to the model), `gap_messages` (just the gap), `gap_mode`, `gap_estimated_tokens`, `response_full` (entire response, not truncated), `judge_reasoning`, parsed `correctness` + `meta_awareness` + `score`.

Gap content is deterministic across machines and processes (sha256-seeded, not Python's process-randomized `hash()`). Same task ID + same gap mode → byte-identical gap.

To re-judge any sample with a different judge, pull `expected_behavior` from the task YAML and feed it + `response_full` to your judge of choice.

## Why v0.2 replaced v0.1

External review (2026-05-08) found that LHC v0.1 task scenarios overlapped with Ember's training data via `based_on` derivative seeds, plus four other methodology issues (process-randomized gap content, tiny gap pool, train/eval gap mismatch, truncated scorecards). v0.2 fixes all six. See [`../docs/journal/2026-05-08-external-review-and-decontamination.md`](../docs/journal/2026-05-08-external-review-and-decontamination.md) for the full review.
