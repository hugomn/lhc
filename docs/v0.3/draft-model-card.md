# DRAFT — `lhc-state-handoff-1.5b` model card

> **This is a Week 0 draft written before Phase 1 begins, as the "consumption surface first" discipline.** It describes the model as if it had already shipped successfully against all S-gates. If we cannot write a model card we'd be proud to publish here, the artifact isn't worth building.
>
> If/when the model actually ships, this doc becomes the basis for the published HF model card.

---

```yaml
---
license: apache-2.0
language:
  - en
library_name: transformers
tags:
  - agent
  - long-horizon-coherence
  - state-handoff
  - structured-output
  - specialist
base_model: <TBD: Qwen3-1.7B or Llama-3.2-3B>
datasets:
  - hugonogueira/lhc-v0.3
pipeline_tag: text-generation
---
```

# `lhc-state-handoff-1.5b`

A small local model that handles the one job long-running agent loops keep failing at: **state handoff** — given prior context, current request, and (optionally) a protocol schema, emit a structured JSON artifact describing the active goal, the relevant prior state, any conflicts, and the next action.

This is not a chat model. It does not respond to users. It is an **inference-time helper** called by an agent harness around frontier LLM calls. Use it to make your frontier model's job tractable, not to replace it.

## What it does

Input: any combination of (prior transcript, prior state card, current user request, optional protocol schema).

Output: a JSON object matching this schema.

```json
{
  "active_goal": "string",
  "relevant_prior_state": "string",
  "conflicts": [
    {
      "type": "state_invalidation | decision_conflict | scope_change",
      "detail": "string",
      "evidence_spans": ["string"]
    }
  ],
  "next_action": "string",
  "evidence_spans": ["string"]
}
```

The model emits valid schema in **≥ 95%** of cases on the LHC v0.3 held-out set.

## When to use it

The model is built for situations where an agent loop must resume from prior state and the resume step is currently fragile. Specifically:

- **Multi-day or multi-session agent tasks** where context must be compacted between runs.
- **Coding agents** approaching context-window limits that need to summarize state before truncation.
- **Privacy-sensitive deployments** that cannot send agent state to frontier APIs.
- **Generic agent workflows that need an auditable state-handoff record** — the structured output + evidence_spans gives downstream systems something to log and inspect rather than free-form prose.

> **Out of scope.** This model has not been evaluated on legal, medical, financial, or other high-stakes specialty domains. Do not deploy it in those domains on the basis of LHC evaluation results alone. LHC measures a controlled prompt-level proxy for state handoff; production use in regulated domains requires domain-specific evaluation that this model has not undergone.

## When NOT to use it

- As a chat model. It will respond, but quality is not validated for chat.
- For tasks where a deterministic parser would do. The companion repo [`lhc-resume-state-parser`](https://github.com/hugomn/lhc-resume-state-parser) handles cleanly-structured state without an LLM call. Use the parser first; use this model only for the residual cases the parser cannot resolve.
- For domains far outside the training distribution (LHC v0.3 task families: state recall, resumption, commitment, planning, multi-thread). The model has no domain knowledge beyond what its base provides.

## Performance (PROVISIONAL — to be filled with actual Phase 1 + Phase 2 numbers)

Evaluated on LHC v0.3 held-out subset (12 tasks, 4 gap modes, 3 trials each, paired comparison with same-size base).

| Metric | `lhc-state-handoff-1.5b` | Same-size base | Δ | 95% CI |
|---|---:|---:|---:|---|
| Overall mean | TBD | TBD | TBD | TBD |
| Resumption category mean | TBD | TBD | TBD | TBD |
| Schema validity rate | TBD | n/a | n/a | n/a |

| Comparison vs deterministic parser | Specialist | Parser | Winner |
|---|---:|---:|---|
| Structured tasks | TBD | TBD | TBD |
| Unstructured/free-prose tasks | TBD | TBD | TBD |

**Ship gates that this row clears (S1–S5):** TBD. All five must be green for this card to publish.

## How it was built

**Base model:** TBD (Qwen3-1.7B or Llama-3.2-3B; final pick at end of v0.3 Week 1).

**Training data:** Curated from LHC v0.3 Phase 1 sweep traces under non-oracle harness conditions (H1, H2, H3). The recipe is deterministic and pre-registered in [the v0.3 decision doc](DECISION-v0.3.md) before Phase 1 begins. **No oracle (H4) traces are used in training.** Verified by automated leakage check before training kickoff.

**Training method:** LoRA fine-tune on Apple Silicon M5 Pro 64GB via MLX-LM. Specifics (rank, layers, LR, iters) frozen at training start.

**Evaluation:** All evaluations on the 12 held-out tasks authored before Phase 1 sweep results were visible. No tuning against held-out tasks. Same Opus 4.7 judge used across v0.2 and v0.3.

**Sweep size:** Phase 2 produces 36 scorecards (3 systems × 4 gap modes × 3 trials), each covering all 12 held-out tasks — 432 task-trials total. ("Scorecard" follows v0.2 convention: one JSON file per (system × harness × gap × trial) cell, containing all tasks. "Task-trial" = one (task × trial) row within a scorecard.)

## Honest limitations

This section lists the things this model **does not do well or at all**. It will be filled with real findings from Phase 2 evaluation if Phase 2 runs.

- **Domain coverage:** trained and evaluated on LHC task families. Does not generalize beyond.
- **Free-form chat:** explicitly not validated. Smoke tested against degradation only (S5).
- **Long context:** inherits base model's context limit. State handoff is the use case; this model is not a long-context engine.
- **Languages:** English only.
- **Hallucination:** structured JSON output reduces but does not eliminate fabrication risk in the `relevant_prior_state` and `next_action` fields. Always validate evidence_spans against source.

## Methodology integrity

This model is the conditional Phase 2 artifact of a pre-registered decision protocol. It ships only if all five S-gates clear on held-out tasks. The full gate definitions, training data recipe, and audit results are in:

- [DECISION-v0.3.md](https://github.com/hugomn/lhc/blob/main/docs/v0.3/DECISION-v0.3.md)
- [LHC v0.3 dataset card](https://huggingface.co/datasets/hugonogueira/lhc-v0.3)
- [LHC repo](https://github.com/hugomn/lhc)

If you find an evaluation issue, please open an issue on the LHC repo. The full sweep scorecards are public.

## Citation

```bibtex
@misc{lhc-state-handoff-2026,
  author       = {Nogueira, Hugo},
  title        = {lhc-state-handoff-1.5b: A small specialist model for agent state handoff},
  year         = {2026},
  publisher    = {HuggingFace},
  url          = {https://huggingface.co/hugonogueira/lhc-state-handoff-1.5b}
}
```

## License

Apache 2.0. Same as base model and LHC v0.3 dataset.

---

## Week 0 review notes (delete before publishing)

Drafting this now surfaced the following issues to resolve before Phase 1 kickoff:

1. **Base model selection has cascading effects.** Schema validity (S4) and chat smoke (S5) both depend on base. Decide before Phase 1 starts so we know what we're aiming at, not after Phase 1 results bias the choice.
2. **The "When to use it" scenarios** are the load-bearing pitch for this artifact. Validate at least one of them resembles a real Clayer use case before committing to Phase 2 (privately — does not enter published framing per DECISION §9).
3. **The parser comparison row in the performance table** is the differentiator from "another fine-tune." If the model only beats the parser on cases the parser was never going to handle, that's not a finding worth shipping.
4. **No comparative claim against frontier models in this card.** A 1.5B specialist beating frontier models on LHC tasks would be extraordinary; we don't pre-commit to claiming it. If Phase 2 surfaces such a result, it goes in the writeup, not the model card.
5. **The "honest limitations" section is shorter than it should be in a real model card.** Expand once Phase 2 data exists. A short limitations section is a yellow flag for any reader.
