# Ember

> **Patient fire.** A foundation model for agents that live.

Ember is [Slow Lit Labs](https://slowlitlabs.co)' open research effort to push autonomous agent models past the failure mode that matters most: not getting the next token right, but staying coherent across hours, days, and weeks of operation.

This repo is the home of the **Long-Horizon Coherence (LHC) benchmark** and the **Ember post-training pipeline**. We define the metric we want to be measured by, score the field on it, and then train a model to win on it.

## Why this exists

Every team that has run an autonomous agent in production for more than a week has hit the same three failure modes — agents forget goals after enough intervening noise, agents silently drop commitments under contradictory pressure, agents fail to resume cleanly after a session boundary.

No published benchmark measures any of them. Most leaderboards measure single-run capability and stop there. We think long-horizon coherence is where production agent value actually lives, and where a small lab can move the field.

Read the [manifesto](docs/manifesto.md) for the longer version.

## What's in this repo

| Path | What |
|---|---|
| **`evals/`** | LHC — the long-horizon coherence benchmark. 12 tasks across 3 categories × 4 difficulty tiers. Open and reproducible. |
| **`docs/`** | Manifesto, methodology, findings, architecture, results, plan. |
| **`data/`** | Dataset construction pipeline for Ember post-training. |
| **`training/`** | LoRA / SFT recipes (currently MLX-LM, local Apple Silicon). |
| **`inference/`** | Local OpenAI-compatible server for running Ember once trained. |
| **`PLAN.md`** | The current execution plan for Ember v0.1. |

## Status

**Pre-release.** The benchmark works and has been run against three flagship models. The Ember model itself does not yet exist — see [`PLAN.md`](PLAN.md) for the path to v0.1.

What is true today:

- LHC v0.1 benchmark — 12 tasks, multi-provider runner, binary 2D rubric, cross-judge validated.
- Public scorecard — Kimi K2.6, Claude Sonnet 4.6, DeepSeek V4 Pro, all scored on 3 trials × 12 tasks. See [`docs/results.md`](docs/results.md).
- One real finding so far — the **executor-vs-narrator gap**: K2.6 is the most reliably correct model on LHC (97% correctness) but the least metacognitive (42% meta-awareness). This is the gap Ember is being trained to close.

## Quick links

- [Manifesto](docs/manifesto.md) — why this exists
- [LHC methodology](docs/eval-suite.md) — how we measure
- [Findings](docs/findings.md) — what we have learned so far
- [Results](docs/results.md) — the current cross-model scorecard
- [Architecture](docs/architecture.md) — how the harness works end-to-end
- [Benchmark spec](docs/benchmark-spec.md) — the formal task and rubric definition
- [Plan](PLAN.md) — execution plan for Ember v0.1
- [Changelog](docs/changelog.md) — versioned release notes

## Run the benchmark

```bash
git clone https://github.com/slowlitlabs/ember.git
cd ember
uv venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env  # then fill in any provider keys you have
python -m evals.runners.lhc --provider moonshot --judge-provider anthropic
```

Supported providers: `moonshot`, `openai`, `anthropic`, `deepseek`, `slowlit`. Any OpenAI-compatible endpoint also works via `--model` / `--base-url` / `--api-key`.

See [`evals/README.md`](evals/README.md) for the full runner reference.

## License

Apache 2.0 for code. See [`LICENSE`](LICENSE).

Model weights, when released, ship under a permissive open-weight license matching the base model's terms.

## Citation

If you use LHC or Ember in research, please cite via [`CITATION.cff`](CITATION.cff).

---

**Slow Lit Labs** — patient fire.
