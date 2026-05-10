# Inference (HISTORICAL — Ember v0.1.5 era)

> **Status: this directory is preserved for the methodology arc, not as researcher-facing tooling.** It contains the inference-serving plan that was drafted for Ember v0.1.5 before that model was retired (it did not measurably beat its base under matched local inference; see [`docs/findings.md`](../docs/findings.md) F-05). No model has been published; the vLLM serve commands below reference a HuggingFace path that does not exist.

If you want to evaluate a model on LHC, you don't need anything in this directory. See the top-level [`README.md`](../README.md) `## Run LHC v0.2` section.

The original v0.1.5 plan (kept here for the record):

## Path 1 — local on Apple Silicon (MLX-LM)

The default path was development and demos. Runs a model on an M-series Mac with an OpenAI-compatible HTTP server.

```bash
# Once weights are merged into ./models/<your-model>
mlx_lm.server \
    --model ./models/<your-model> \
    --port 8080
```

This exposes:
- `POST http://localhost:8080/v1/chat/completions`
- `POST http://localhost:8080/v1/completions`

The LHC harness picks an MLX-served model up automatically via the `slowlit` provider:

```bash
python -m evals.runners.lhc --provider slowlit --judge-provider anthropic
```

`SLOWLIT_BASE_URL` defaults to `http://localhost:8080/v1`. The slowlit provider also injects `/no_think` as a system prompt prefix by default — important to know if you're benchmarking a Qwen3-family model that supports the `/no_think` mode, since it changes the inference path. See `evals/runners/lhc.py` for the prefix-injection logic.

## Path 2 — production via vLLM (NEVER SHIPPED)

When Ember was planned to graduate to a public API, the plan was to serve merged weights under vLLM on a rented H100. The model paths below reference HuggingFace destinations that **do not exist** because the model was never published.

```bash
# Direct vLLM (model path is hypothetical — never published)
vllm serve hugonogueira/ember-v0.1 \
    --host 0.0.0.0 \
    --port 8000 \
    --max-model-len 65536

# Or with adapter on top of base (also hypothetical)
vllm serve Qwen/Qwen2.5-7B-Instruct \
    --enable-lora \
    --lora-modules ember-v0.1=hugonogueira/ember-v0.1-adapter \
    --port 8000
```

`serve.py` was a planned wrapper for vLLM with auth, rate limiting, request logging. Currently a placeholder.

## API surface (would have been)

OpenAI-compatible. Drop-in replacement for any agent framework that accepts a `base_url` override.

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<your-model>",
    "messages": [
      {"role": "user", "content": "Resume the deployment workflow."}
    ],
    "max_tokens": 4096
  }'
```

The single highest-leverage product decision in the original plan: do not invent a new API shape. Every existing agent SDK works against an OpenAI-compatible endpoint on day one.
