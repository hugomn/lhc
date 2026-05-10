# Training (HISTORICAL — Ember v0.1.5 era)

> **Status: this directory is preserved for the methodology arc, not as researcher-facing tooling.** It contains the LoRA / DoRA fine-tuning code that produced Ember v0.1.5 — the model that did not measurably beat its base under matched local inference and was not released. The training-side story is part of the load-bearing example for the [methodology contribution](../README.md), but if you're here to evaluate your own fine-tune on LHC, you don't need anything in this directory. See the top-level [`README.md`](../README.md) `## Run LHC v0.2` section instead.

If you want to read this code as historical context:

- **[`sweep_v02.py`](sweep_v02.py)** — the 4-model × 4-gap-mode × 3-trial sweep driver that produced the original 2026-05-09 verdict. Hardcoded model list (Ember/Qwen3-8B/Ministral/Llama-3.1-8B), hardcoded output paths. Not a researcher-facing matrix runner.
- **`sweep_v15.py`**, **`sweep_8b_class.py`** — older sweep configs from before LHC v0.2.
- **Training recipes** — see git history for the LoRA/DoRA configs that produced `checkpoints/ember-v0.1.5/`.

For the actual decision arc behind this code:

- [`docs/journal/2026-05-08-external-review-and-decontamination.md`](../docs/journal/2026-05-08-external-review-and-decontamination.md) — round 1 review, methodology rebuild
- [`docs/journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md`](../docs/journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md) — sweep verdict (later corrected by matched-inference diagnostic)
- [`docs/journal/2026-05-10-mlx-replication-and-diagnostic-closure.md`](../docs/journal/2026-05-10-mlx-replication-and-diagnostic-closure.md) — matched-inference correction; v0.1.5 retired

For an "evaluate my own fine-tune on LHC" path: there is no canned matrix runner today. Use [`evals.runners.lhc`](../evals/runners/lhc.py) directly with `--provider <your-provider>` and `--model <your-model>`, and run multiple trials yourself with fresh server starts (see the [MLX replication observation](../docs/findings.md) F-05 about why fresh server starts matter on Apple Silicon).
