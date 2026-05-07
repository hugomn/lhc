# Data

The training corpus for Ember v0.1.

## Sources

1. **Synthetic** (`data/synthetic/`) — long-horizon coherence examples
   generated via rejection sampling against the base model. The base
   model is asked to produce paired (success, failure) trajectories on
   coherence-stressing prompts; we keep the successes.

2. **Real Clayer traces** (`data/traces/`) — anonymized agent run
   traces from production Clayer deployments. **Gitignored.**
   Customer data never enters this repository directly.

## Pipeline

```bash
# 1. Generate synthetic examples (10k–50k target)
python -m data.prepare synthetic \
    --base-model kimi-k2-6 \
    --target-count 20000 \
    --output data/synthetic/v0.1.jsonl

# 2. Anonymize and convert real traces
python -m data.prepare traces \
    --input data/traces/raw/ \
    --output data/traces/anonymized.jsonl

# 3. Merge, dedupe, split into train/eval
python -m data.prepare merge \
    --synthetic data/synthetic/v0.1.jsonl \
    --traces data/traces/anonymized.jsonl \
    --output data/sft/v0.1/
```

## Format

Every example is a JSONL row in OpenAI chat-completions format:

```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    ...
  ],
  "metadata": {
    "source": "synthetic|trace",
    "category": "state_recall|commitment|resumption",
    "gap_tokens": 8000
  }
}
```

The `metadata.category` field lets us stratify training and eval splits
by the same taxonomy LHC uses.
