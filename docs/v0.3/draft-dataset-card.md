# DRAFT — `lhc-v0.3` dataset card

> **Week 0 draft, written before Phase 1 begins, as the "consumption surface first" discipline.** It describes the dataset as if it had already shipped successfully against all K-gates. If we cannot write a dataset card we'd be proud to publish here, the artifact isn't worth building.
>
> If/when v0.3 actually ships, this becomes the basis for the published HF dataset card.

---

```yaml
---
license: apache-2.0
language:
  - en
tags:
  - long-horizon-coherence
  - agent-evaluation
  - state-handoff
  - protocol-ablation
  - benchmark
size_categories:
  - n<1K
configs:
  - config_name: tasks
    data_files:
      - split: v02
        path: data/tasks_v02.parquet
      - split: held_out
        path: data/tasks_heldout.parquet
  - config_name: scorecards
    data_files:
      - split: phase1
        path: data/scorecards_phase1.parquet
      - split: phase2
        path: data/scorecards_phase2.parquet
  - config_name: protocols
    data_files:
      - split: definitions
        path: data/protocols.parquet
---
```

# LHC v0.3 — The Agent State Handoff Problem

A controlled protocol-ablation benchmark for long-horizon coherence in language-model agents. Extends [LHC v0.2](https://huggingface.co/datasets/hugonogueira/lhc-v0.2) with five harness conditions (H0–H4) and 12 fresh held-out tasks authored blind to results.

**This dataset is the result of a pre-registered evaluation protocol.** All gate definitions, the held-out authoring discipline, and the model panel were locked before any sweep ran. See [DECISION-v0.3.md](https://github.com/hugomn/lhc/blob/main/docs/v0.3/DECISION-v0.3.md) for the contract this dataset honors.

## What's in here

**Tasks (36 total):**
- 24 tasks carried forward from LHC v0.2 (`split: v02`).
- 12 fresh tasks authored after Week 1 of v0.3 cycle, **blind to any Phase 1 sweep results** (`split: held_out`). Authored by Hugo Nogueira, not by any model. Used for Phase 2 ship gates and held-out validation.

**Protocol definitions (7 conditions, 5 protocols + 2 length/recency controls):**
- **H0** Raw LHC prompt. No protocol scaffolding.
- **H1** Explicit state card extracted programmatically from prompt. No interpretation.
- **H1c** Length/recency control for H1: same token count and position as H1, but with semantically irrelevant filler (shuffled content from an unrelated task). Used to distinguish state-interface effect from raw position/recency effect.
- **H2** State card + provenance/evidence spans pointing into source transcript.
- **H2c** Length/recency control for H2: same token count and position as H2, with irrelevant filler.
- **H3** State card + conflict detector. Flags potential inconsistencies; does NOT name the correct answer or recommend an action.
- **H4** Oracle protocol. Resume artifact constructed using ground truth. **Upper bound only — excluded from any capability claim about non-oracle conditions.**

Each protocol is defined by a deterministic transformation applied to the raw LHC prompt. Code for each transformation is in the LHC repo; the input/output of each transformation per task is in the `protocols` config. The H1c/H2c controls are necessary to attribute observed effects: a state-interface effect must show H1 > H1c and H2 > H2c, otherwise the result is attributed to recency/position, not state interface.

**Scorecards and task-trials (Phase 1 + optional Phase 2):**

Following v0.2 convention: one **scorecard** = one JSON file containing scored task-trials for a single (model × harness × gap_mode × trial_index) cell across all tasks in scope. One **task-trial** = one (task × trial) row within a scorecard.

- **Phase 1: 252 scorecards / 9072 task-trials.** N models × 7 harness conditions (H0/H1/H1c/H2/H2c/H3/H4) × 4 gap modes × 3 trials = 252 scorecards (minimum, with N=3 models). Each scorecard covers 36 tasks → 9072 task-trials in total.
- **Phase 2 (conditional): 36 scorecards / 432 task-trials.** 3 systems (specialist, same-size base, deterministic parser) × 4 gap modes × 3 trials = 36 scorecards. Each covers 12 held-out tasks → 432 task-trials.

Each scorecard is fully self-identifying: model_slug, base_model, adapter (if any), inference_path, system_prompt_prefix, server_config, generator, judge_id, judge_session_id, harness_condition.

## Headline findings (PROVISIONAL — to be filled with actual Phase 1 + Phase 2 numbers)

> Filled at publish time. The shape of the table is locked here so the structure cannot be retrofitted to flatter the result.

**Phase 1: does protocol scaffolding move the needle?**

Primary table (state-interface conditions vs raw + controls + oracle):

| Model | H0 (raw) | H1 (state card) | H1c (length ctrl) | H2 (+ evidence) | H2c (length ctrl) | H3 (+ conflict) | H4 (oracle) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Frontier | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Open 8B | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Small 1-3B | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

(Mean LHC overall, `current` gap mode, paired bootstrap CIs in the per-task scorecards.)

State-interface deltas (the question that matters): H1 − H1c, H2 − H2c, H3 − H2. These rows isolate the state-interface contribution after subtracting the position/recency contribution. Filled at publish time with paired CIs.

**Phase 2 (if ran): can a small specialist replicate the harness effect by emitting the artifact directly?**

TBD. Filled if the Phase 2 ship gates (S1–S5) clear. Otherwise, this section reads "Phase 2 model did not ship — see writeup."

## How this dataset was authored

1. **24 v0.2 tasks** carried forward from [LHC v0.2 dataset](https://huggingface.co/datasets/hugonogueira/lhc-v0.2) without modification. Same provenance, same decontamination manifest.
2. **12 held-out tasks** authored by Hugo Nogueira during weeks 3–4 of the v0.3 cycle, **before any Phase 1 sweep results were visible**. Author followed the v0.2 [`AUTHORING.md`](https://github.com/hugomn/lhc/blob/main/evals/v0.2/AUTHORING.md) discipline: original scenarios (no transformation of v0.2 tasks), decontamination check via [`banned_overlap.json`](https://github.com/hugomn/lhc/blob/main/evals/v0.2/banned_overlap.json), per-task manifest entries, all four gap modes (`none`, `placeholder`, `neutral`, `current`).
3. **Protocol definitions (H0–H4)** locked at end of v0.3 Week 2, before any full sweep. Code in the LHC repo at `evals/v0.3/protocols/`. Each protocol applies a deterministic transformation to the raw LHC prompt; the transformations themselves are publishable artifacts.
4. **Sweep run** weeks 5–6. All scorecards saved with full provenance metadata, batched into Parquet for the dataset viewer and JSON for the canonical scorecard format.

## Decontamination

Same protocol as v0.2: [`banned_overlap.json`](https://github.com/hugomn/lhc/blob/main/evals/v0.2/banned_overlap.json) extended for the 12 held-out tasks; per-task `manifest.json` entries with task-shape declarations and overlap checks. The 12 held-out tasks were authored using the same decontamination discipline as the 24 v0.2 tasks.

## Limitations

This section is intentionally specific. A short limitations section is a yellow flag.

- **Scope.** LHC measures a controlled prompt-level proxy for state-handoff behavior, not multi-week runtime agent coherence. A model that does well on LHC may still fail at week-long agent loops; this dataset does not falsify or validate that.
- **Task count.** 36 tasks is small. Per-task variance is real. The held-out subset (12) is even smaller. Treat single-task scores with appropriate skepticism; the gate analyses use paired bootstrap over tasks to put bounds on this.
- **Languages.** English only.
- **Domain.** Agent-task scenarios drawn from a curated set of families (state recall, resumption, commitment, planning, multi-thread editing, ATC handoff, court interpretation, NICU titration, etc.). Not a general agent benchmark.
- **Judge dependency.** All evaluations use Claude Opus 4.7 as judge. Judge stability gate (K1) and manual audit gate (K4) are run; K1/K4 results published alongside scorecards. Judge bias is a known risk and is documented per cycle.
- **Harness ablation interpretation.** The H4/oracle condition is upper bound only. Claims about "harness improves capability" must use H1/H2/H3 deltas vs H0, not H4. This is enforced in our DECISION doc and we expect downstream users to honor it.
- **No multi-turn dialogue.** All tasks are single-shot resume-from-state. The handoff problem in production agents has multi-turn variants this dataset does not cover.

## Methodology integrity

LHC v0.3 is the second cycle of an explicit pre-registration discipline. The first (LHC v0.2) is documented in our [methodology writeup](https://hugo.im/posts/lhc-v02-long-horizon-coherence-benchmark/) and in the [v0.2 journal](https://github.com/hugomn/lhc/tree/main/docs/journal). The full chain of decisions, dead ends, and corrections is public.

If you find an evaluation issue, please open an issue on the LHC repo. We treat third-party finds as first-class signal — see the v0.2 cycle, where six rounds of external review caught issues that internal review didn't.

## Citation

```bibtex
@misc{lhc-v03-dataset-2026,
  author       = {Nogueira, Hugo},
  title        = {LHC v0.3: The Agent State Handoff Problem — A Controlled Protocol-Ablation Benchmark for Long-Horizon Coherence},
  year         = {2026},
  publisher    = {HuggingFace},
  url          = {https://huggingface.co/datasets/hugonogueira/lhc-v0.3}
}
```

## License

Apache 2.0.

---

## Week 0 review notes (delete before publishing)

Drafting this surfaced:

1. **The protocol definitions need to be artifacts in their own right.** Right now they live as code in the repo and a description in this card. If H0–H4 become the load-bearing contribution, they should be a separate publishable spec, not a sub-section here. Decide at end of Week 2.
2. **The "headline findings" table reserves space for a result we don't have yet.** This is intentional — the schema is committed before the data exists. Do not collapse rows or add columns once Phase 1 starts.
3. **The held-out task count (12) is the floor that justifies T4 and S1–S5.** If we author fewer than 12, the gate thresholds need revision (and that means a v0.4 doc, not editing this one).
4. **No comparison row in headline table for Ember v0.1.5 / Qwen-local-MLX.** Those are continuity columns; if included, they go in a sub-table labeled "v0.2 continuity" so they aren't read as primary findings.
5. **Limitations section length is right.** Six bullets, all specific. Matches the bar v0.2 set.
