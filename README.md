# LHC — long-horizon coherence

> A decontaminated, audit-validated benchmark for evaluating long-horizon coherence in 8B-class agent models.

[![HuggingFace Dataset](https://img.shields.io/badge/🤗%20Dataset-hugonogueira%2Flhc--v0.2-yellow)](https://huggingface.co/datasets/hugonogueira/lhc-v0.2)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)

This repo contains:

- **LHC v0.2** — 24 hand-curated tasks, 4 gap-mode ablation, full audit trail, four rounds of external review. Also published as the [`hugonogueira/lhc-v0.2`](https://huggingface.co/datasets/hugonogueira/lhc-v0.2) HuggingFace dataset.
- **Deterministic baseline** — 100-line Python parser that beats every fine-tuned 8B model we tested on two structured-state tasks.
- **The honest training record** — every dead end, including the fine-tuned model that didn't beat its base.

## What this is for

If you are training a model to maintain coherence across long-running conversations or autonomous agent loops — and you want to know whether your fine-tune is *actually* better than its base, or just better at the test set — LHC is built for you. It is a small, manually-curated benchmark with three properties most LHC-style benchmarks lack:

1. **Decontaminated.** No `based_on` overlap with the synthetic data Ember was trained on. Contamination check tooling is in the repo.
2. **Gap-mode ablated.** Each task is run under 4 different "long-horizon gap" conditions (none / placeholder / neutral / current). The gap mode is the lever that exposes coherence failures vs. surface memorization.
3. **Pre-registered decision gates.** [`evals/v0.2/DECISION.md`](evals/v0.2/DECISION.md) was locked *before* any model was scored. The reasoning for shipping or not-shipping is the same reasoning we'd apply to anyone else's results.

## Status (2026-05-10)

The Ember v0.1.5 fine-tune did not ship. **Under matched local MLX inference, Ember v0.1.5 is statistically indistinguishable from base Qwen3-8B on LHC v0.2; it does not meet our bar for release** ("significant improvement on at least one functionality compared to a same-class model").

Getting to that conclusion took four rounds of external review in 72 hours:

1. **Round 1 (2026-05-08)** — caught LHC v0.1 contamination, hash-seed bug, train/eval gap mismatch. Triggered the v0.2 rebuild.
2. **Round 2 (2026-05-09)** — caught that the v0.2 sweep compared Ember (local MLX, with `/no_think`) against the OpenRouter models (no `/no_think`). Inference-config asymmetry confounded the original "Ember regresses by 0.25" verdict.
3. **Round 3 (2026-05-10)** — blessed the matched-inference diagnostic with a wording change and asked us to close one symmetry nuisance.
4. **Round 4 (2026-05-10)** — closing that nuisance surfaced an MLX replication issue (within-session vs across-session). Final n=3 fresh-server-restart comparison is a statistical tie; both CIs cross zero.

Both reviewer rounds and the resulting verdicts are recorded in the [journal](docs/journal/). Nothing has been edited after the fact.

## Headline result (LHC v0.2)

The 4-model sweep (3 trials × 24 tasks × 4 gap modes per cell, judged by Claude Opus 4.7) produced this leaderboard. **Ember and Qwen3-8B base ran via different inference paths** — see the matched-inference comparison below for the apples-to-apples Ember-vs-base verdict.

| Rank | Model | Mean (max 2.00) | Inference path |
|------|-------|----------------:|----------------|
| #1 | **Qwen3-8B base** | **1.413** | OpenRouter, no `/no_think` |
| #2 | Ministral-8B-2512 | 1.351 | OpenRouter |
| #3 (tie) | **Ember v0.1.5 iter-900** | 1.285 | local MLX, with `/no_think` |
| #3 (tie) | Llama-3.1-8B | 1.285 | OpenRouter |

All four benchmark-validity gates passed (judge stability, rank inversion, CI discrimination, variance attribution).

**Ember vs base, matched local-MLX inference, n=3 fresh-server trials per cell:**

| Gap | Ember mean | Qwen-local mean | Δ E−Q | 95% CI (task-bootstrap)¹ |
|---|---:|---:|---:|---|
| `current` | 1.222 | 1.181 | **+0.042** | [−0.139, +0.222] |
| `neutral` | 1.319 | 1.333 | **−0.014** | [−0.139, +0.111] |

Both CIs cross zero: **statistical tie on both gap modes.** Ember is not measurably better than base under matched inference; it is also not measurably worse.

¹ Task-bootstrap CI conditional on the observed 3 restart trials. A hierarchical bootstrap over (task, trial) would be wider, not narrower. Sufficient to reject shipping; not for fine ranking.

A 100-line deterministic parser (no LLM) scored **0.75 on resumption** (8 tasks) — and beat all four LLMs on the two structured-state resumption tasks (warehouse tracker, inconsistency detection). Implication: fine-tuning is the wrong layer for those task structures.

See [`docs/results.md`](docs/results.md) for per-category and per-gap-mode tables, and [`docs/findings.md`](docs/findings.md) F-05 for the full record.

## What's in this repo

| Path | What |
|---|---|
| **`evals/v0.2/`** | LHC v0.2 — tasks, decision gates, analyzer, audit scripts, deterministic baseline, matched-inference diagnostics. The current canonical benchmark. |
| **`evals/runners/`** | The harness — multi-provider runner with stable seeding, full-message scorecards, fail-fast lifecycle, gap-mode ablation. |
| **`evals/results/published/lhc-v0.2/`** | All sweep + diagnostic scorecards, audit results, verdict. Reproducible. |
| **`evals/tasks/`** | LHC v0.1 tasks (historical — superseded by v0.2 due to contamination). |
| **`docs/journal/`** | Append-only chronological log of work sessions. The methodology arc. |
| **`docs/findings.md`** | Living "what's true now" doc, newest-first. |
| **`docs/results.md`** | Current LHC v0.2 cross-model leaderboard. |
| **`data/`** | Synthetic dataset construction pipeline (used for v0.1.5; pending redesign for v0.2). |
| **`training/`** | LoRA / DoRA recipes via MLX-LM, sweep drivers, eval drivers. |

## Quick links

- [LHC v0.2 results](docs/results.md) — current leaderboard
- [Findings](docs/findings.md) — living what-we-know doc
- [Journal — 2026-05-08](docs/journal/2026-05-08-external-review-and-decontamination.md) — round 1: contamination, hash-seed bug, train/eval gap mismatch
- [Journal — 2026-05-09](docs/journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md) — the sweep verdict (later rebuilt under matched inference)
- [Journal — 2026-05-10](docs/journal/2026-05-10-mlx-replication-and-diagnostic-closure.md) — rounds 2–4: matched-inference diagnostic + MLX replication observation + final null-result framing
- [LHC v0.2 decision gates](evals/v0.2/DECISION.md) — pre-registered methodology
- [LHC v0.2 authoring procedure](evals/v0.2/AUTHORING.md) — how the decontaminated tasks were built
- [Manifesto](docs/manifesto.md) — why long-horizon coherence matters
- [Architecture](docs/architecture.md) — how the harness assembles a run
- [Changelog](docs/changelog.md) — versioned release notes

## Run LHC v0.2

### Evaluate any OpenAI-compatible model

```bash
git clone https://github.com/hugomn/lhc.git
cd lhc
uv venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env  # add provider keys (OPENROUTER_API_KEY + ANTHROPIC_API_KEY work for the published sweep models)

# One model × one gap mode × one trial
python -m evals.runners.lhc \
    --provider openrouter \
    --model qwen/qwen3-8b \
    --judge-provider anthropic \
    --gap-mode current \
    --lhc-version 0.2 \
    --tasks-dir evals/v0.2/tasks
```

To evaluate a model you serve yourself (vLLM, MLX-LM server, etc.), set `SLOWLIT_BASE_URL` to your endpoint and use `--provider slowlit`. **Important**: the slowlit provider injects `/no_think` as a system-prompt prefix by default (Qwen3-family thinking-mode opt-out). If you're benchmarking a model that doesn't support `/no_think` mode, override the prefix in the `slowlit` provider config or use `--provider openrouter` with an OpenRouter-mirrored deployment instead — see `evals/runners/lhc.py` for the prefix-injection logic. **Whichever inference path you pick, document it alongside your scorecard** — the original 2026-05-09 sweep was confounded by exactly this asymmetry, see [findings.md F-05](docs/findings.md).

### Multi-trial protocol for MLX-served models

In our setup on Apple Silicon, MLX-LM server outputs were stable within a single server session but varied across fresh server starts (~0.07–0.13 stdev on overall mean across 3 restart trials, with 6/24 tasks score-flipping per side). If your fine-tune is served via MLX-LM and you want to compare it against another model's score:

- **Restart the MLX server between trials** (or accept that your "n=3" is one sample with within-session caching).
- The diagnostic scripts in `evals/v0.2/diagnostic_*_replicate.py` show the protocol: launch a fresh `mlx_lm.server` process per trial.
- Aim for ≥3 fresh-server-restart trials on both sides of any comparison; report mean + stdev + a paired bootstrap CI (see `evals/v0.2/diagnostic_compare.py`).

We have not isolated the source of the cross-restart variance (could be MLX-LM server, Metal kernels, cache state, sampling defaults, warmup, or process init). If your stack is different, your variance characteristics may be different — measure first.

### Reproduce our results

```bash
# Original 4-model sweep — 4 models × 4 gap modes × 3 trials = 48 scorecards, ~3 hours, ~$5
# Note: this is OUR sweep config (model list and output paths are hardcoded); not a researcher-facing matrix runner
python -m training.sweep_v02 --skip-existing

# Audit + original verdict (with the now-retracted G4 CI; see findings.md F-05)
python evals/v0.2/audit_g9_judge_stability.py --per-model 30
python evals/v0.2/audit_g12_manual.py    # interactive, 12 samples
python evals/v0.2/analyze.py \
    --scorecards-dir evals/results/published/lhc-v0.2/sweep \
    --audit-results evals/results/published/lhc-v0.2/audit-combined.json

# Matched-inference diagnostic (Ember and base Qwen3-8B both via local MLX,
# n=3 fresh-server-restart trials per cell)
python evals/v0.2/diagnostic_local_qwen.py        # Qwen-local trial 1
python evals/v0.2/diagnostic_qwen_replicate.py    # Qwen-local trials 2 + 3
python evals/v0.2/diagnostic_ember_rerun.py       # Ember trial 1
python evals/v0.2/diagnostic_ember_replicate.py   # Ember trials 2 + 3
python evals/v0.2/diagnostic_compare.py           # paired bootstrap CI; defaults to published scorecards
```

## What we learned that someone else can use

- **Benchmark contamination is easy to introduce and hard to detect.** LHC v0.1's derivative-seed contamination *masked non-improvement* — without the v0.2 rebuild, we would have shipped a model whose apparent improvement on the contaminated benchmark was an artifact and which, on a clean matched-inference comparison, does not measurably beat its base. The contamination check tooling at [`evals/v0.2/build_banned_overlap.py`](evals/v0.2/build_banned_overlap.py) is reusable for any benchmark-vs-fine-tune comparison.

- **Pre-registering decision gates and refusing to move them is the methodology that produced an honest result.** [`evals/v0.2/DECISION.md`](evals/v0.2/DECISION.md) was locked before any model run. When the data showed Ember worse than base, we had no path to argue around it.

- **Pre-registered thresholds need a power check.** Our G9 threshold of 0.10 was below the noise floor at the originally-specified sample size — caught and corrected by increasing N. Documented in the [2026-05-09 journal entry](docs/journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md).

- **Deterministic parsers are a real baseline for structured-state tasks.** A 100-line script beat all four 8B-class LLMs on two specific resumption tasks. Anyone training agent models should test this before assuming fine-tuning is the right layer.

- **Storing full prompt + full gap + full response in scorecards costs nothing and enables independent re-judging by anyone, ever.** Excerpt-only storage made the v0.1 scorecards effectively un-auditable. Lesson learned the hard way.

- **Inference-config asymmetry can dominate a benchmark verdict.** The original v0.2 sweep ranked Ember vs OpenRouter-served Qwen3-8B and reported "Ember regresses by 0.25, CI [−0.46, −0.06]." Re-running both via the same local MLX server with the same `/no_think` prefix shrank that delta to +0.04 (a tie). About 5/6 of the apparent regression was inference confound. Anyone benchmarking a fine-tune against its base should run them on the same inference path.

- **MLX-LM server replication: restart between trials.** In our setup on Apple Silicon, MLX outputs were stable within a single server session but varied across fresh server starts. Per-cell stdev across 3 restart trials was 0.02–0.13 on overall mean, with 6 of 24 tasks score-flipping per side. The original sweep's "byte-identical n=3 trials" was a within-session repeat, not three independent samples. We have not isolated the source. Benchmark replications of MLX-served models should restart the server between trials or explicitly state they are within-session.

## Publishing your own scorecard

If you run LHC against a model and want to share scorecards:

1. **Self-identify your scorecards.** Add `model_slug`, `base_model`, `adapter` (or `null`), `inference_path`, `inference_provider`, `system_prompt_prefix`, and `server_config` fields at the top of each scorecard JSON. The published diagnostic scorecards under `evals/results/published/lhc-v0.2/diagnostic-*` show the shape. Filenames disambiguate; JSON content also should.
2. **Document the inference path in any comparison.** "Model X scored Y on LHC v0.2 `current`" is missing the inference path. "Model X (vLLM, no system prefix, n=3 fresh-process trials) scored Y±σ on LHC v0.2 `current`" is comparable to ours.
3. **If you publish artifacts to HuggingFace from a working directory, do not upload ignored files.** This repo's `.gitignore` covers `.env`, `models/`, `checkpoints/`, `evals/results/v0.2/` (working scorecards) and other local-only state. Use a clean `git ls-files` + `huggingface-cli upload` rather than `huggingface-cli upload .`.

## License

Apache 2.0 for code. See [`LICENSE`](LICENSE).

LHC v0.2 tasks and methodology are also Apache 2.0 — fork the benchmark, run your own model on it, send a PR with your scorecard.

## Citation

If you use LHC or build on this methodology, please cite via [`CITATION.cff`](CITATION.cff).

## About

Solo research effort by [Hugo Nogueira](https://github.com/hugomn). The methodology is the contribution; the model that didn't ship is the load-bearing example.

This is the seed for an eventual research lab focused on long-horizon agent reliability — but for now, it lives here under my personal name.
