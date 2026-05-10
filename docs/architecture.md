# Architecture — how the LHC harness works

> **Note (2026-05-09):** the harness shape described here is unchanged for LHC v0.2. Three additions in v0.2 worth flagging: (1) gap content is now stable across processes (sha256-seeded, not Python-`hash()`-seeded), (2) scorecards store full prompt + full gap + full response (not just 400-char excerpts), (3) per-task failures are fatal — partial scorecards are no longer written. See [`evals/v0.2/DECISION.md`](../evals/v0.2/DECISION.md) for the full v0.2 methodology and [`journal/2026-05-08-external-review-and-decontamination.md`](journal/2026-05-08-external-review-and-decontamination.md) for why each change was made.

A single LHC run takes a model, a task, a gap size, and a judge. It produces one row in the scorecard. This doc walks through what happens between input and output, end to end.

## The five-step flow

```
┌──────────────┐    ┌────────────┐    ┌─────────────┐    ┌────────┐    ┌────────┐
│ Task YAML    │───▶│ Assemble   │───▶│ Target      │───▶│ Judge  │───▶│ Score  │
│              │    │ messages   │    │ model call  │    │ call   │    │ row    │
│ setup +      │    │            │    │             │    │        │    │        │
│ probe        │    │ + gap from │    │ OpenAI-     │    │ binary │    │ correct│
│ + expected   │    │ gap.py     │    │ compatible  │    │ rubric │    │ + meta │
│ behavior     │    │            │    │             │    │ JSON   │    │        │
└──────────────┘    └────────────┘    └─────────────┘    └────────┘    └────────┘
   evals/tasks/        runners/         runners/          runners/      results/
```

### 1. Task definition

Each task is a YAML file under `evals/tasks/<category>/<task_id>.yaml`. It declares a `setup` (the messages that establish goal/commitment/state), a `probe` (the final user turn that triggers the test), and an `expected_behavior` block that the judge uses to grade. Optional `tools` and `gap_tokens` overrides supported. See [`benchmark-spec.md`](benchmark-spec.md).

### 2. Message assembly

`runners/lhc.py::run_task` calls `gap.py::generate_gap` with `target_tokens` and a deterministic seed (hash of the task id). The gap is a sequence of synthetic user/assistant exchanges from a fixed pool, shuffled and cycled until the token budget is hit.

The gap pool is intentionally mundane — plausible side-errand chatter that the model has to hold but not act on. Variety prevents the model from pattern-matching the gap as filler.

The gap is trimmed so it never ends on a user message. This prevents an ambiguous probe (e.g., "Pick this up.") from grounding in the most recent gap turn instead of the original setup. See finding F-01.

The final message sequence is `setup + gap.messages + probe`.

### 3. Target call

`runners/client.py::Client.chat` is a thin OpenAI-compatible wrapper. It supports any provider that speaks chat completions (Moonshot, Anthropic, DeepSeek, OpenAI, vLLM, MLX-LM server). For reasoning models that emit empty `content` and route output through a `reasoning_content` channel (K2.6, DeepSeek R-class, OpenAI o-series), the wrapper falls back to that channel automatically.

Default temperature is 1.0 and max_tokens is 16384 — enough for a reasoning model to think and answer without truncation.

### 4. Judge call

`runners/grader.py::Grader.grade` sends the expected behavior block + the agent's response to a judge model with a fixed system prompt. The judge returns a JSON object with two integer fields: `correctness` and `meta_awareness`, each `0` or `1`.

The judge prompt is fixed across models for fairness. Cross-judge validation results live in [`findings.md`](findings.md) (F-02).

### 5. Score row

The runner writes one `TaskScore` per task — `(task_id, category, correctness, meta_awareness, score, response_excerpt, judge_reasoning)`. After all tasks complete, the runner computes per-category and overall means, then writes the full `Scorecard` JSON to `evals/results/`.

## Component map

| File | Role |
|---|---|
| `evals/runners/lhc.py` | CLI entry point, message assembly, scoring loop |
| `evals/runners/client.py` | OpenAI-compatible HTTP client (target + judge) |
| `evals/runners/gap.py` | Deterministic gap generator with role-tail trimming |
| `evals/runners/grader.py` | Judge prompt + JSON parse |
| `evals/runners/trace.py` | Verbose single-task tracer for debugging |
| `evals/tasks/<category>/*.yaml` | The 12 task definitions |
| `evals/results/v2-rubric/*.json` | Per-run scorecards |

## Adding a new provider

`PROVIDER_DEFAULTS` in `lhc.py` is the only place to extend. Add a key with `model`, `base_url`, `api_key_env` — the runner picks up the rest. Providers must speak OpenAI-style chat completions; if they don't, write a thin proxy or extend `client.py`.

## Adding a new task

See [`benchmark-spec.md`](benchmark-spec.md) for the task format.

LHC v0.1 is **frozen** — new tasks ship in `evals/tasks/v0.2/` as part of a new benchmark version. v0.1 scores remain comparable across releases.

## Why this shape

The harness is intentionally thin. Each component does one thing:

- The runner does I/O and aggregation.
- The client does HTTP.
- The gap generator produces deterministic noise.
- The grader does one thing — turn an `(expected, response)` pair into two binaries.

This is an explicit design choice: **the harness should be inspectable end-to-end in one sitting.** A new contributor should be able to read all five files in fifteen minutes and trust what comes out the other side.
