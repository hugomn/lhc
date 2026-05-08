# Contributing

Ember is an open research project. Contributions are welcome on the LHC eval suite, the harness, the post-training pipeline, and the docs.

## What to read first

- [`docs/manifesto.md`](docs/manifesto.md) — the *why*
- [`docs/eval-suite.md`](docs/eval-suite.md) — the LHC methodology
- [`docs/architecture.md`](docs/architecture.md) — how the harness is wired
- [`docs/findings.md`](docs/findings.md) — design tradeoffs and bug history (read this before second-guessing a design choice)

## Adding a new LHC task

LHC v0.1 is **frozen** — no changes to existing tasks under `evals/tasks/<category>/` beyond bug fixes.

New tasks land in `evals/tasks/v0.2/` and ship as part of LHC v0.2 with its own published baselines.

Format and acceptance criteria are documented in [`docs/benchmark-spec.md`](docs/benchmark-spec.md). At minimum a new task must:

1. Discriminate between at least two reference models (i.e. produce different scores).
2. Have its variance below the discrimination signal across 3 trials.
3. Include a `description` that is honest about what the task tests and why it is interesting.

## Adding a new model provider

`PROVIDER_DEFAULTS` in `evals/runners/lhc.py` is the only place to extend. Add an entry with `model`, `base_url`, `api_key_env`. The runner picks up the rest. The provider must speak OpenAI-style chat completions.

If you add a provider, add it to `.env.example` and to the supported-providers line in `evals/README.md`.

## Code style

- Python 3.11+, type hints on all public functions.
- Ruff for lint and format (`ruff check . && ruff format .`).
- Pytest for tests. No mocks for things that can be tested for real.
- Default to writing no comments. Only add one when the *why* is non-obvious.

## Reproducibility

Every published run must include:

- The exact LHC version scored against.
- The base model and adapter checksums (for trained models).
- The judge model used for grading.
- A pinned `pyproject.toml` lock or `uv.lock`.

Reproducibility > speed. A 0.02 LHC delta that nobody can re-run is noise.

## Filing a finding

When you learn something non-obvious — a bug fix, a design tradeoff that took a debate, an unexpected scorecard result — add an entry to [`docs/findings.md`](docs/findings.md). Use the format documented at the bottom of that file. Findings are the institutional memory of the project.

## License

By contributing, you agree your contributions are licensed under Apache 2.0, the same as the rest of the code.
