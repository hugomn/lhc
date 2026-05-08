# Ember v0.1 — Plan

## Goal

Ship a downloadable Ember v0.1 model that demonstrably improves long-horizon coherence (LHC) over its base model, runnable locally on an M5 Pro 68GB Mac, served via an OpenAI-compatible `/v1/chat/completions` endpoint.

**Success criteria for v0.1:**
- Ember v0.1 (7B) scores ≥0.70 meta-awareness on the LHC benchmark (vs ~0.45 for the base model and 0.42 for K2.6)
- Correctness stays ≥0.95 (training does not break task execution)
- Runs locally on M5 Pro at ≥30 tok/s
- Published as open weights on HuggingFace
- Total spend ≤$200 (well under the $1k budget)

## Status (start of plan)

- ✅ LHC benchmark v0.1 — 12 tasks, multi-provider runner, binary 2D rubric
- ✅ Cross-model baseline — K2.6, Sonnet 4.6, DeepSeek V4 Pro scored on LHC
- ✅ Cross-judge validation — Sonnet judge agrees with K2.6 self-judge within ±0.08
- ⏳ Ember model — not started
- 💰 Spent so far: ~$30-65 on API. Budget remaining: ~$935.

## Stages

### Stage 1 — Dataset design and validation (gating step, ~3-4 days)

The dataset is the project. If the dataset doesn't teach the right behavior, no amount of training compute saves it. Validate cheaply before scaling.

**1.1 — Hand-design 50 seed examples**
- Format: `(setup_messages, gap_messages, probe, ideal_response)`
- Each example demonstrates the executor → narrator transformation: same correctness, but with explicit metacognitive framing ("Per your earlier instruction…", "Picking up Thread B since A is blocked on it…", "I see an inconsistency in the working memory…")
- Cover all 3 LHC categories: state_recall, commitment, resumption
- Mix all 4 difficulty tiers
- Stored as JSONL in `evals/training_data/seeds.jsonl`

**1.2 — Few-shot validation**
- Take 5-10 of the seed examples
- Use them as few-shot prompts against K2.6 on the LHC benchmark
- Measure: does few-shot K2.6 beat zero-shot K2.6 on meta-awareness?
- **Decision gate:** if few-shot doesn't lift meta-awareness from 0.42 → ≥0.65, the dataset concept is wrong. Stop and redesign before generating more.

**1.3 — Synthetic generation at scale**
- If 1.2 passes: use the 50 seeds as in-context examples to generate ~2,000 synthetic examples via Sonnet 4.6
- Generation prompt: "Given this LHC-shaped scenario template, produce a response that (a) executes the task correctly AND (b) explicitly surfaces the metacognitive context."
- Cost: ~$50-80 in Sonnet API
- Filter: drop any generated example where Sonnet's response doesn't include explicit metacognitive language (regex pre-filter + LLM-judge filter)

**1.4 — Held-out eval split**
- Reserve ~200 examples for held-out evaluation (never seen during training)
- Training set: ~1,800 examples

**Deliverable:** `evals/training_data/ember_v0.1_train.jsonl` and `ember_v0.1_eval.jsonl`

### Stage 2 — Local training infrastructure (~1-2 days)

**2.1 — MLX-LM setup**
- `pip install mlx-lm`
- Download base model: `mlx_lm.convert --hf-path Qwen/Qwen2.5-7B-Instruct --mlx-path ./models/qwen-7b`
- Verify base model serves: `mlx_lm.server --model ./models/qwen-7b --port 8080`
- Smoke test: curl the local endpoint with a simple prompt

**2.2 — Baseline eval**
- Add `slowlit` provider to the LHC runner pointing at `localhost:8080`
- Run the 12-task LHC suite against base Qwen2.5-7B
- Record baseline scorecard (will likely score ~0.85 correctness, ~0.45 meta-awareness)
- This is the floor Ember v0.1 must beat

**2.3 — LoRA training script**
- Configure MLX-LM LoRA training: rank 32, alpha 64, learning rate 1e-4
- Format training data as MLX-LM expects (chat template applied)
- Dry-run on 50 examples to confirm the pipeline runs end-to-end

**Deliverable:** working local serving + training pipeline + baseline scorecard.

### Stage 3 — Train Ember v0.1 (~2-3 days, mostly waiting)

**3.1 — First training run**
- Train Qwen2.5-7B with LoRA on the 1,800-example dataset
- 1-2 epochs, batch size 4, gradient accumulation as needed
- Expected duration on M5 Pro: 4-8 hours
- Save checkpoints every 500 steps

**3.2 — Eval each checkpoint**
- Run LHC against checkpoints at 500, 1000, 1500, final
- Pick the best-scoring checkpoint (avoid overfitting)

**3.3 — Iterate (3-5 runs)**
- Try variations: rank 16 vs 32 vs 64, learning rate 5e-5 vs 1e-4 vs 2e-4, 1 epoch vs 2 epochs
- Each run = 4-8 hours, so plan 2-3 days for 3-5 iterations
- Pick the winner

**3.4 — Merge LoRA into base**
- `mlx_lm.fuse --model ./models/qwen-7b --adapter-path ./checkpoints/best --save-path ./models/ember-v0.1`
- Result: a standalone Ember v0.1 model file (~14GB bf16, ~4GB if quantized to 4-bit)

**Deliverable:** `./models/ember-v0.1/` runnable via `mlx_lm.server`.

### Stage 4 — Final eval and packaging (~1 day)

**4.1 — Full LHC scorecard**
- Run 3 trials of LHC against Ember v0.1
- Compare against: Qwen2.5-7B base (the relevant baseline), K2.6, Sonnet 4.6, DeepSeek V4 Pro
- Verify success criteria: meta-awareness ≥0.70, correctness ≥0.95
- If criteria not met, return to Stage 3 with insights from the eval

**4.2 — Quantize for distribution**
- Produce 4-bit and 8-bit GGUF variants for broader hardware support
- 4-bit ~4GB, runnable on 16GB Macs

**4.3 — HuggingFace upload**
- Repo: `slowlitlabs/ember-v0.1`
- Upload bf16, 4-bit, and 8-bit variants
- README with: model card, LHC scorecard, usage instructions, citation

**4.4 — Local serving doc**
- One-command instructions to download and run Ember locally
- Add a "talk to Ember" page on slowlitlabs.co pointing at the local server setup

**Deliverable:** Ember v0.1 publicly downloadable, with reproducible eval results.

### Stage 5 — Publish (~1 day, after Stage 4 lands)

**5.1 — Blog post on slowlitlabs.co**
- Title candidate: "Ember v0.1: A 7B Model That Narrates Its Own Reasoning"
- Lede: K2.6 (1T params) scored 0.42 meta-awareness on LHC. Ember v0.1 (7B params) scores 0.72. Here's why and how.
- Sections: the executor-vs-narrator gap, the LHC benchmark, the dataset, the training, the scorecard
- Include the full 4-model comparison chart

**5.2 — arXiv preprint**
- Same content as the blog, formatted for arXiv (LaTeX or markdown→PDF)
- Title: "LHC: Long-Horizon Coherence as a Measurable Axis for Agent Models"
- Authors: Hugo Marques, Slow Lit Labs
- Cite the K2.6, Sonnet, DeepSeek baselines

**5.3 — Distribution**
- Hacker News post
- Twitter/X thread
- Email to anyone you want to recruit

**Deliverable:** public artifact + paper + downloads.

## Local serving — confirmed path

Once Stage 4 completes, the workflow is:

```bash
# Terminal 1 — start the local Ember server
mlx_lm.server --model ./models/ember-v0.1 --port 8080

# Terminal 2 — chat from any OpenAI-compatible client
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ember-v0.1",
    "messages": [{"role": "user", "content": "Hello, Ember."}]
  }'
```

The existing LHC runner picks up Ember by adding `slowlit` to `PROVIDER_DEFAULTS` with `base_url=http://localhost:8080/v1` and any non-empty `api_key`. No other changes needed.

## Budget tracking

| Stage | Item | Est. cost |
|---|---|---|
| 1 | Sonnet API for dataset generation | $50-80 |
| 2 | None (all local) | $0 |
| 3 | None (all local) | $0 |
| 4 | Sonnet judge for cross-model eval | $20-30 |
| 5 | None (publishing is free) | $0 |
| **Total** | | **$70-110** |

Leaves ~$890 of the $1k budget for: a second iteration cycle if v0.1 needs work, a Tier 2 14B variant, or rented GPU for a future v0.2.

## Risks and mitigations

- **Risk:** dataset doesn't teach the right behavior. **Mitigation:** the few-shot validation gate in 1.2.
- **Risk:** training breaks correctness while improving meta-awareness. **Mitigation:** eval every checkpoint, not just the final one; pick the best tradeoff.
- **Risk:** MLX-LM has bugs on M5 (newest hardware). **Mitigation:** fall back to PyTorch + MPS backend if needed; ~2x slower but works.
- **Risk:** scope creep. **Mitigation:** v0.1 is *narrow*. Better local model on one axis. Future versions handle more.

## Timeline (calendar)

Assuming part-time focused effort:
- Stage 1: 2026-05-08 → 2026-05-12 (4 days)
- Stage 2: 2026-05-13 → 2026-05-14 (2 days)
- Stage 3: 2026-05-15 → 2026-05-18 (4 days, mostly compute)
- Stage 4: 2026-05-19 → 2026-05-20 (2 days)
- Stage 5: 2026-05-21 → 2026-05-22 (2 days)

**Target ship date for Ember v0.1: 2026-05-22 (15 days).**
