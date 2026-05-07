# Contributing

Ember is an open research project. Contributions are welcome on the eval
suite and the training pipeline.

## Adding a new LHC task

LHC v0.1 is **frozen** — no changes to `evals/tasks/state_recall/`,
`evals/tasks/commitment/`, or `evals/tasks/resumption/` beyond bug fixes.

New tasks land in `evals/tasks/v0.2/` and ship as part of a new LHC
version with its own published baselines.

## Code style

- Python 3.11+, type hints on all public functions.
- Ruff for lint and format (`ruff check . && ruff format .`).
- Pytest for tests. No mocks for things that can be tested for real.

## Reproducibility

Every published run must include:
- The exact LHC version scored against.
- The base model and adapter checksums.
- The judge model used for grading.
- A pinned `pyproject.toml` lock or `requirements.txt`.

Reproducibility > speed. A 0.02 LHC delta that nobody can re-run is noise.
