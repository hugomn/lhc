# Changelog

All notable changes to Ember and LHC are documented here. Format: keep a record per release; pre-release work lives under `[Unreleased]`.

## [Unreleased]

### LHC v0.1 — benchmark complete (2026-05-08)

#### Added
- **12-task benchmark suite** — 3 categories × 4 difficulty tiers (seed, easy, medium, hard).
- **Binary 2D rubric** — correctness and meta-awareness, each `0/1`. Replaced the original 0–4 rubric after cross-judge agreement collapsed on middle scores.
- **Multi-provider runner** — Moonshot, Anthropic, DeepSeek, OpenAI, plus a `slowlit` provider slot for local Ember serving. OpenAI-compatible base URLs work out of the box.
- **Cross-judge validation** — every run can be graded by an independent judge (default cross-judge config: target=any, judge=Sonnet 4.6).
- **Verbose tracer** (`runners/trace.py`) — step-through inspection of one task end-to-end for debugging.
- **Deterministic gap generator** with trailing-user-message trimming to prevent referential ambiguity attacks (see findings F-01).
- **Public cross-model scorecard** — Kimi K2.6, Claude Sonnet 4.6, DeepSeek V4 Pro, all scored on 3 trials × 12 tasks. See [`docs/results.md`](results.md).

#### Documented
- [`docs/manifesto.md`](manifesto.md) — why this exists, refreshed for Slow Lit Labs branding.
- [`docs/eval-suite.md`](eval-suite.md) — methodology, rebuilt for the 12-task structure and binary 2D rubric.
- [`docs/benchmark-spec.md`](benchmark-spec.md) — formal task and rubric definition.
- [`docs/architecture.md`](architecture.md) — end-to-end harness flow.
- [`docs/results.md`](results.md) — current cross-model scorecard.
- [`docs/findings.md`](findings.md) — running log of design tradeoffs and bug history (F-01 to F-04).
- [`PLAN.md`](../PLAN.md) — Ember v0.1 execution plan.

### Planned for the next release — Ember v0.1

- ~2,000 LHC-shaped synthetic post-training examples, generated and filtered via Sonnet 4.6.
- LoRA fine-tune of Qwen2.5-7B-Instruct on Apple Silicon (MLX-LM).
- Released as `slowlitlabs/ember-v0.1` on Hugging Face.
- Servable locally via `mlx_lm.server` exposing OpenAI-compatible `/v1/chat/completions`.
- Target: meta-awareness ≥ 0.70, correctness ≥ 0.95 on LHC v0.1.

See [`PLAN.md`](../PLAN.md) for the full plan.

## How releases work

Ember follows a simple `vMAJOR.MINOR` scheme.

- **MINOR** releases improve LHC scores or add capability without breaking the API surface.
- **MAJOR** releases change the base model, the API, or the eval suite version.

Every release ships with: weights on Hugging Face, an LHC scorecard tied to a specific LHC version, release notes here, and a regenerated [`docs/results.md`](results.md).

## Renames

- 2026-05-08 — Cinder Labs renamed to **Slow Lit Labs**. GitHub org migrated from `cinderlabsai` to `slowlitlabs`. The Ember model name is unchanged. Brand thesis: *patient fire*.
