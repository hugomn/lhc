# Changelog

All notable changes to Ember and LHC are documented here. Format: keep a record per release; pre-release work lives under `[Unreleased]`.

## [Unreleased]

### Ember v0.1.5 retired; LHC v0.2 published (2026-05-09, verdict updated 2026-05-10)

#### Decision
- **Ember v0.1.5 will not ship.** The initial decontaminated LHC v0.2 sweep (4 models × 4 gap modes × 3 trials, audit-validated, paired-bootstrap CIs) reported Ember as worse than its base Qwen3-8B (Δ −0.25 on `current` overall, CI [−0.46, −0.06]). External review subsequently flagged that Ember (local MLX, with `/no_think`) and base Qwen3-8B (OpenRouter, no `/no_think`) had been compared under different inference configurations. The matched-inference diagnostic (n=3 fresh-server-restart trials per cell, both via local MLX) showed a **statistical tie**: Δ E−Q on `current` = +0.042 (95% CI [−0.139, +0.222]); Δ on `neutral` = −0.014 (95% CI [−0.139, +0.111]). Both CIs cross zero. All benchmark-validity gates passed. Per the pre-registered decision matrix, the v0.1.5 line is retired — not because it underperforms, but because it is statistically indistinguishable from base and does not meet our bar for release ("significant improvement on at least one functionality"). See [`docs/findings.md`](findings.md) F-05, the journal entry [`journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md`](journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md) (initial verdict), and [`journal/2026-05-10-mlx-replication-and-diagnostic-closure.md`](journal/2026-05-10-mlx-replication-and-diagnostic-closure.md) (matched-inference correction).

#### Added (LHC v0.2)
- **24 hand-curated, decontaminated tasks** at [`evals/v0.2/tasks/`](../evals/v0.2/tasks/) (8 per category × 2 per difficulty). No `based_on` overlap with anything in `data/seeds/*` or `data/synthetic/*`. Resumption uses 4 distinct frames (notebook reload / chat-log / handoff log / task-tracker) — no `[SESSION RESUME]` payloads. Frozen at git tag `lhc-v0.2-frozen`.
- **Four-mode gap ablation** in [`evals/runners/gap.py`](../evals/runners/gap.py): `none`, `placeholder` (literal training-data string), `neutral` (lorem-ipsum filler), `current` (real agent chatter, the v0.1 default).
- **Stable sha256-based gap seeding** in [`evals/runners/lhc.py:stable_seed`](../evals/runners/lhc.py). Replaces process-randomized `hash()`. Same task ID → byte-identical gap across machines and processes.
- **Full-audit scorecards** — every task-trial now stores `prompt_messages`, `gap_messages`, `gap_mode`, `gap_estimated_tokens`, `response_full` (not just a 400-char excerpt). Scorecards now contain run-level `gap_mode`, `judge_model`, `expected_task_count`.
- **Fail-fast harness lifecycle** — per-task failures abort the trial; partial scorecards are no longer written. Sweep drivers abort on nonzero subprocess `rc` and verify scorecard task-count matches `expected_task_count`.
- **Pre-registered decision gates** at [`evals/v0.2/DECISION.md`](../evals/v0.2/DECISION.md) — 13 gates (G1–G13), decision matrix locked before any model run. Includes paired-bootstrap CI computation, rank-inversion check, variance attribution.
- **Banned-overlap manifest tooling** at [`evals/v0.2/build_banned_overlap.py`](../evals/v0.2/build_banned_overlap.py). Scans seeds + synthetic training data, emits per-LHC-task contamination buckets (named entities, scaffolding phrases, domain shapes). Reusable for any benchmark-vs-fine-tune comparison.
- **Audit scripts** — automated judge-stability rejudge ([`audit_g9_judge_stability.py`](../evals/v0.2/audit_g9_judge_stability.py)) and interactive manual audit ([`audit_g12_manual.py`](../evals/v0.2/audit_g12_manual.py)).
- **Deterministic resume-state validator baseline** at [`evals/v0.2/deterministic_baseline.py`](../evals/v0.2/deterministic_baseline.py). ~80-line Python parser, no LLM in forward pass. Scored 0.75 / 2.00 on resumption (8 tasks); on `resumption_v2_004` (warehouse tracker) and `resumption_v2_008` (inconsistency detection) it scores 2/2 deterministically while every fine-tuned 8B model we tested averaged below 2.0 across 12 cells per task.
- **OpenRouter provider** for the harness. Used to evaluate Llama-3.1-8B, Ministral-8B-2512, Qwen3-8B, Phi-4-mini, etc. via one OpenAI-compatible endpoint.
- **Sweep driver** at [`training/sweep_v02.py`](../training/sweep_v02.py) — hybrid local-MLX + OpenRouter, fail-fast, `--skip-existing` for clean restart.
- **Client-side retry** in [`evals/runners/client.py`](../evals/runners/client.py) — up to 3 attempts with backoff on malformed upstream responses (None choices, None message). Triggered once mid-sweep; saved the run.

#### Documented
- [`docs/journal/2026-05-08-external-review-and-decontamination.md`](journal/2026-05-08-external-review-and-decontamination.md) — the external review that triggered the rebuild.
- [`docs/journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md`](journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md) — today's sweep verdict.
- [`docs/findings.md`](findings.md) — F-05 added (LHC v0.2 leaderboard); top-of-file status block updated to retire v0.1.5.
- [`docs/results.md`](results.md) — rewritten for the LHC v0.2 leaderboard.
- [`README.md`](../README.md) — rewritten for the v0.2 era; honest about v0.1.5.
- [`evals/v0.2/AUTHORING.md`](../evals/v0.2/AUTHORING.md) — 7-step procedure for new tasks.
- [`evals/v0.2/DECISION.md`](../evals/v0.2/DECISION.md) — pre-registered methodology.
- [`evals/results/published/lhc-v0.2/README.md`](../evals/results/published/lhc-v0.2/README.md) — what's in the published sweep + how to reproduce.

#### Changed
- [`evals/runners/lhc.py`](../evals/runners/lhc.py) — added `--gap-mode`, `--lhc-version`, `--tasks-dir` CLI args. Refactored `run_task()` to return prompt + gap + response for full-audit scorecards.
- [`evals/runners/grader.py`](../evals/runners/grader.py) — unchanged. Same binary 2D rubric as v0.1 (a v0.2 contract design).
- [`docs/eval-suite.md`](eval-suite.md), [`docs/benchmark-spec.md`](benchmark-spec.md), [`docs/architecture.md`](architecture.md) — top-of-file caveats added pointing readers at v0.2 specifics.
- [`PLAN.md`](../PLAN.md) — converted to a tombstone pointing at the journal entries; the original v0.1 plan is preserved in git history.

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

### Planned for the next release — Ember v0.1 (HISTORICAL — did not ship)

> The plan below was the intent as of 2026-05-08. It produced Ember v0.1.5, which the LHC v0.2 sweep on 2026-05-09 showed underperforms its base model. The v0.1.5 line is retired. See the 2026-05-09 entry above for what shipped instead.

- ~2,000 LHC-shaped synthetic post-training examples, generated and filtered via Sonnet 4.6.
- LoRA fine-tune of Qwen2.5-7B-Instruct on Apple Silicon (MLX-LM). *(Actually trained on Qwen3-8B, not Qwen2.5-7B-Instruct — base model selection corrected during Stage 2.)*
- Released as `hugonogueira/ember-v0.1` on Hugging Face. *(Not released — see retirement decision above.)*
- Servable locally via `mlx_lm.server` exposing OpenAI-compatible `/v1/chat/completions`. *(Built and tested locally; never published.)*
- Target: meta-awareness ≥ 0.70, correctness ≥ 0.95 on LHC v0.1. *(Hit on the contaminated LHC v0.1; missed on the clean LHC v0.2 — see F-05.)*

## How releases work

Ember follows a simple `vMAJOR.MINOR` scheme.

- **MINOR** releases improve LHC scores or add capability without breaking the API surface.
- **MAJOR** releases change the base model, the API, or the eval suite version.

Every release ships with: weights on Hugging Face, an LHC scorecard tied to a specific LHC version, release notes here, and a regenerated [`docs/results.md`](results.md).

## Renames

- 2026-05-10 — `slowlitlabs/ember` → **`hugonogueira/lhc`** on GitHub. The repo's substance shifted from "training pipeline that produced Ember" to "long-horizon coherence benchmark plus the honest training record" — the v0.2 sweep made clear that the benchmark + methodology + the model that didn't ship is the contribution, not a model release. Repo lives under the personal username for now; will move back to a Slow Lit Labs org once incorporated. The HuggingFace org for any model artifacts also moves from `slowlitlabs/*` to `hugonogueira/*`.
- 2026-05-08 — Cinder Labs renamed to **Slow Lit Labs**. GitHub org migrated from `cinderlabsai` to `slowlitlabs`. The Ember model name is unchanged. Brand thesis: *patient fire*.
