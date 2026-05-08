# Training

LoRA post-training of an open-weight base model on long-horizon coherence data.

## Approach for v0.1

- **Base**: Qwen2.5-7B-Instruct (Apache-2.0, well-supported in MLX-LM, fits in M5 Pro RAM with room for training).
- **Method**: LoRA via [MLX-LM](https://github.com/ml-explore/mlx-examples/tree/main/llms) on Apple Silicon. Local. No cloud compute for v0.1.
- **Dataset**: ~2,000 LHC-shaped examples from `data/synthetic/`. See [`PLAN.md`](../PLAN.md) Stage 1 for dataset construction.
- **Compute**: M5 Pro 68GB. Single training run is ~4–8 hours.

The full plan is documented in [`PLAN.md`](../PLAN.md). This README is the operational entry point once Stage 2 of that plan is complete.

## Run (placeholder — operational once Stage 3 lands)

```bash
# Convert base model to MLX format (one-time)
mlx_lm.convert --hf-path Qwen/Qwen2.5-7B-Instruct --mlx-path ./models/qwen-7b

# LoRA training
mlx_lm.lora \
    --model ./models/qwen-7b \
    --train \
    --data data/synthetic/v0.1 \
    --batch-size 4 \
    --iters 1000 \
    --adapter-path checkpoints/ember-v0.1

# Merge LoRA into base for distribution
mlx_lm.fuse \
    --model ./models/qwen-7b \
    --adapter-path checkpoints/ember-v0.1 \
    --save-path models/ember-v0.1
```

The `configs/` directory will hold the canonical hyperparameter YAML once we lock the recipe.

## Future paths

- **Tier 2 (14B base):** scaling to Qwen2.5-14B with the same recipe. Same M5 Pro can host it; training takes longer.
- **Cloud step:** if v0.1 hits the LHC target and a v0.2 needs more compute, rent an H100 from RunPod / Lambda / Crusoe. Out of scope for v0.1 — local first.

## Infra

`infra/accelerate_8xh100.yaml` is leftover scaffold for a future cloud path. Ignore it for v0.1; MLX-LM does not use Accelerate.
