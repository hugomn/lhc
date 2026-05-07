# Ember

> A foundation model for agents that live.

Ember is [Cinder Labs](https://cinderlabs.ai)' open research effort to push
autonomous agent models past the 12-hour wall — toward agents that survive
days, weeks, and months of continuous operation.

This repo contains:

- **`evals/`** — the Long-Horizon Coherence (LHC) benchmark, an open eval
  suite that measures how well an agent recovers state and intent after
  long context gaps. We define the metric we want to be measured by.
- **`data/`** — the data pipeline that turns agent traces into training data.
- **`training/`** — LoRA / SFT / RL recipes built on top of the strongest
  open-weight agent base model available at training time.
- **`inference/`** — a vLLM-backed OpenAI-compatible API server.
- **`docs/`** — manifesto, eval methodology, release notes.

## Status

**v0.1 — pre-release.** The eval harness is the first deliverable. The
trained model follows once the baseline numbers are public.

## Quick links

- [Manifesto](docs/manifesto.md) — why this exists
- [Eval methodology](docs/eval-suite.md) — how we measure long-horizon coherence
- [Changelog](docs/changelog.md) — versioned release notes

## License

Apache 2.0 for code. Model weights, when released, will use a permissive
open-weight license (decision pending — likely Apache 2.0 or a Modified MIT
matching the base model's terms).

---

**Cinder Labs** — Building agents that build.
