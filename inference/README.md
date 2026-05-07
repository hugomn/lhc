# Inference

vLLM-backed OpenAI-compatible API server.

## Why vLLM

- Production-grade throughput.
- OpenAI-compatible chat completions out of the box.
- Native LoRA adapter loading — we can serve the base model with the
  Ember adapter applied at request time, without merging weights.

## Run locally

```bash
# Serve Ember v0.1
vllm serve cinderlabs/ember-v0.1 \\
    --host 0.0.0.0 \\
    --port 8000 \\
    --max-model-len 65536

# Or serve the base + adapter
vllm serve moonshotai/Kimi-K2.6 \\
    --enable-lora \\
    --lora-modules ember-v0.1=cinderlabs/ember-v0.1-adapter \\
    --host 0.0.0.0 \\
    --port 8000
```

## Production deploy (Path 2 from the spec)

Single rented H100 from RunPod / Lambda / Vast.ai. The `serve.py` wrapper
adds auth, rate limiting, and request logging on top of vLLM.

```bash
# On the GPU host
python -m inference.serve \\
    --model cinderlabs/ember-v0.1 \\
    --port 8000

# Behind a reverse proxy (Caddy/nginx) terminating TLS at api.cinderlabs.ai
```

## API surface

OpenAI-compatible. Drop-in replacement for any agent framework that
accepts a `base_url` override.

```bash
curl https://api.cinderlabs.ai/v1/chat/completions \\
  -H "Authorization: Bearer $CINDER_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "ember-v0.1",
    "messages": [
      {"role": "user", "content": "Resume the deployment workflow."}
    ],
    "tools": [...],
    "max_tokens": 4096
  }'
```

This is the single highest-leverage product decision: do not invent a
new API shape. Every existing agent SDK works against Ember on day one.
