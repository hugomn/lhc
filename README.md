# Ember

> **Patient fire.** A research effort by [Slow Lit Labs](https://slowlitlabs.co) on long-horizon coherence in autonomous agent models.

This repo is the home of:

- **LHC v0.2** — a decontaminated, gap-mode-ablated benchmark for long-horizon coherence in 8B-class language models.
- **The Ember training pipeline** — LoRA / DoRA fine-tuning on Apple Silicon (MLX-LM), built around LHC.
- **A complete, public methodology arc** — including the version of the benchmark we got wrong, the external review that called it out, and the rebuild that produced honest numbers.

## Status (2026-05-09)

**Ember v0.1.5 did not ship.** A clean, decontaminated re-evaluation showed it underperforms its base model (Qwen3-8B) by 0.13 mean / 0.25 on the production-relevant gap mode, with statistical confidence (95% CI [-0.46, -0.06]). Per our pre-registered decision gates, the v0.1.5 line is retired.

What you can use today:

- **LHC v0.2 benchmark** — 24 hand-curated tasks, 4 gap-mode ablation, stable seeding, full prompt + response audit trail, judge-stability tested, manual-audit validated. We believe this is the most rigorously-validated long-horizon coherence benchmark publicly available at this scale.
- **The deterministic resume-state validator baseline** — a 100-line Python parser (no LLM in the forward pass) that beats every fine-tuned 8B model we tested on two specific resumption tasks. Sets a hard floor on what "fine-tuning is worth it" means for structured-state tasks.
- **The full methodology record** — every dead end, every revision, every gate result. See the [journal](docs/journal/) and [findings](docs/findings.md).

What we are working on next:

- An honest plan for Ember v0.2, currently being designed and reviewed externally before any new training. See `PLAN.md` after it lands; until then, see the [latest journal entry](docs/journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md) for context.

## Headline result (LHC v0.2)

| Rank | Model | Mean (max 2.00) |
|------|-------|----------------:|
| #1 | **Qwen3-8B base** | **1.413** |
| #2 | Ministral-8B-2512 | 1.351 |
| #3 (tie) | **Ember v0.1.5 iter-900** | 1.285 |
| #3 (tie) | Llama-3.1-8B | 1.285 |

3 trials × 24 tasks × 4 gap modes per cell. Judged by Claude Opus 4.7. All four benchmark-validity gates passed (judge stability, rank inversion, CI discrimination, variance attribution). See [`docs/results.md`](docs/results.md) for per-category and per-gap-mode tables.

A 100-line deterministic parser (no LLM) scored **0.75 on resumption** (8 tasks) — and beat all four LLMs on the two structured-state resumption tasks (warehouse tracker, inconsistency detection). Implication: fine-tuning is the wrong layer for those task structures.

## What's in this repo

| Path | What |
|---|---|
| **`evals/v0.2/`** | LHC v0.2 — tasks, decision gates, analyzer, audit scripts, deterministic baseline. The current canonical benchmark. |
| **`evals/runners/`** | The harness — multi-provider runner with stable seeding, full-message scorecards, fail-fast lifecycle, gap-mode ablation. |
| **`evals/results/published/lhc-v0.2/`** | All 48 sweep scorecards, audit results, verdict. Reproducible. |
| **`evals/tasks/`** | LHC v0.1 tasks (historical — superseded by v0.2 due to contamination). |
| **`docs/journal/`** | Append-only chronological log of work sessions. The methodology arc. |
| **`docs/findings.md`** | Living "what's true now" doc, newest-first. |
| **`docs/results.md`** | Current LHC v0.2 cross-model leaderboard. |
| **`data/`** | Synthetic dataset construction pipeline (used for v0.1.5; pending redesign for v0.2). |
| **`training/`** | LoRA / DoRA recipes via MLX-LM, sweep drivers, eval drivers. |

## Quick links

- [LHC v0.2 results](docs/results.md) — current leaderboard
- [Findings](docs/findings.md) — living what-we-know doc
- [Journal — 2026-05-08](docs/journal/2026-05-08-external-review-and-decontamination.md) — the external review that triggered the rebuild
- [Journal — 2026-05-09](docs/journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md) — the sweep that confirmed v0.1.5 underperforms base
- [LHC v0.2 decision gates](evals/v0.2/DECISION.md) — pre-registered methodology
- [LHC v0.2 authoring procedure](evals/v0.2/AUTHORING.md) — how the decontaminated tasks were built
- [Manifesto](docs/manifesto.md) — why long-horizon coherence matters
- [Architecture](docs/architecture.md) — how the harness assembles a run
- [Changelog](docs/changelog.md) — versioned release notes

## Run LHC v0.2

```bash
git clone https://github.com/slowlitlabs/ember.git
cd ember
uv venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env  # add your provider keys (OPENROUTER_API_KEY + ANTHROPIC_API_KEY for the published sweep)

# One model × one gap mode × one trial
python -m evals.runners.lhc \
    --provider openrouter \
    --model qwen/qwen3-8b \
    --judge-provider anthropic \
    --gap-mode current \
    --lhc-version 0.2 \
    --tasks-dir evals/v0.2/tasks

# Full sweep (4 models × 4 gap modes × 3 trials = 48 scorecards, ~3 hours, ~$5)
python -m training.sweep_v02 --skip-existing

# Audit + verdict
python evals/v0.2/audit_g9_judge_stability.py --per-model 30
python evals/v0.2/audit_g12_manual.py    # interactive, 12 samples
python evals/v0.2/analyze.py \
    --scorecards-dir evals/results/published/lhc-v0.2/sweep \
    --audit-results evals/results/published/lhc-v0.2/audit-combined.json
```

## What we learned that someone else can use

- **Benchmark contamination is easy to introduce and hard to detect.** Our LHC v0.1 derivative-seed contamination *masked an actual regression* — without the v0.2 rebuild, we would have shipped a model that was worse than its base. The contamination check tooling at [`evals/v0.2/build_banned_overlap.py`](evals/v0.2/build_banned_overlap.py) is reusable for any benchmark-vs-fine-tune comparison.

- **Pre-registering decision gates and refusing to move them is the methodology that produced an honest result.** [`evals/v0.2/DECISION.md`](evals/v0.2/DECISION.md) was locked before any model run. When the data showed Ember worse than base, we had no path to argue around it.

- **Pre-registered thresholds need a power check.** Our G9 threshold of 0.10 was below the noise floor at the originally-specified sample size — caught and corrected by increasing N. Documented in the [2026-05-09 journal entry](docs/journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md).

- **Deterministic parsers are a real baseline for structured-state tasks.** A 100-line script beat all four 8B-class LLMs on two specific resumption tasks. Anyone training agent models should test this before assuming fine-tuning is the right layer.

- **Storing full prompt + full gap + full response in scorecards costs nothing and enables independent re-judging by anyone, ever.** Excerpt-only storage made our v0.1 scorecards effectively un-auditable. Lesson learned the hard way.

## License

Apache 2.0 for code. See [`LICENSE`](LICENSE).

LHC v0.2 tasks and methodology are also Apache 2.0 — fork the benchmark, run your own model on it, send a PR with your scorecard.

## Citation

If you use LHC or build on this methodology, please cite via [`CITATION.cff`](CITATION.cff).

---

**Slow Lit Labs** — patient fire.
