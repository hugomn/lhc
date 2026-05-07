# Training

LoRA fine-tuning of the strongest available open-weight agent base model.

## Approach for v0.1

- **Base**: chosen at training time — leading candidate is Kimi K2.6
  (open-weight, Modified MIT, frontier-tier on agent benchmarks).
- **Method**: LoRA via [Axolotl](https://github.com/axolotl-ai-cloud/axolotl).
  No full fine-tune for v0.1; LoRA gives us a >10× cost win and is
  sufficient for narrowly scoped capability gains.
- **Dataset**: ~50k examples from `data/sft/v0.1/`.
- **Compute**: single 8×H100 node, ~$15–25k expected for the production run.

## Run

```bash
# Single-node LoRA on 8× H100
accelerate launch \\
    --config_file training/infra/accelerate_8xh100.yaml \\
    -m axolotl.cli.train \\
    training/configs/ember-v0.1-lora.yaml
```

The Axolotl config in `configs/` is the source of truth for hyperparameters,
LoRA rank, learning rate, and dataset paths.

## Infra

Production runs on rented H100s — RunPod, Lambda, or Crusoe depending on
availability. See `infra/` for cluster setup scripts.

Dev iterations on a single A100 (Lambda 1-Click clusters) for fast feedback
on small dataset slices.
