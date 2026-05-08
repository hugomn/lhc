# Inference

How to run Ember locally and (later) in production.

## Path 1 — local on Apple Silicon (MLX-LM)

The default path for development and demos. Runs Ember on an M-series Mac with an OpenAI-compatible HTTP server.

```bash
# After Stage 4 of PLAN.md produces ./models/ember-v0.1
mlx_lm.server \
    --model ./models/ember-v0.1 \
    --port 8080
```

This exposes:
- `POST http://localhost:8080/v1/chat/completions`
- `POST http://localhost:8080/v1/completions`

The existing LHC harness picks Ember up automatically via the `slowlit` provider:

```bash
python -m evals.runners.lhc --provider slowlit --judge-provider anthropic
```

`SLOWLIT_BASE_URL` defaults to `http://localhost:8080/v1` — no other config needed.

## Path 2 — production via vLLM (later)

When Ember graduates to a public API, the same merged weights serve under vLLM on a rented H100 (RunPod, Lambda, Vast.ai). Native LoRA adapter loading also works if we choose to ship the adapter separately.

```bash
# Direct vLLM
vllm serve slowlitlabs/ember-v0.1 \
    --host 0.0.0.0 \
    --port 8000 \
    --max-model-len 65536

# Or with adapter on top of base
vllm serve Qwen/Qwen2.5-7B-Instruct \
    --enable-lora \
    --lora-modules ember-v0.1=slowlitlabs/ember-v0.1-adapter \
    --port 8000
```

`serve.py` will eventually wrap vLLM with auth, rate limiting, and request logging. Currently a placeholder — the local path is the focus until v0.1 ships.

## API surface

OpenAI-compatible. Drop-in replacement for any agent framework that accepts a `base_url` override.

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ember-v0.1",
    "messages": [
      {"role": "user", "content": "Resume the deployment workflow."}
    ],
    "max_tokens": 4096
  }'
```

This is the single highest-leverage product decision: do not invent a new API shape. Every existing agent SDK works against Ember on day one.
