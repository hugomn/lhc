# Long-Horizon Coherence (LHC) — eval methodology

> The first open benchmark for agent coherence across long context gaps.

## What LHC measures

LHC is built on a single hypothesis: **the failure mode that matters most for production autonomous agents is not single-turn quality, it is whether the agent is the same agent at hour 24 that it was at hour 0.**

LHC isolates and measures three specific competencies:

1. **State recall after intervening noise** — the agent set a goal at T0. At T1, after thousands of tokens of intervening unrelated content, can it still correctly act on the original goal?
2. **Decision consistency under contradictory input** — the agent made a commitment at T0. At T1, a request arrives that conflicts with that commitment. Does the agent recognize the conflict, or does it overwrite the commitment silently?
3. **Workflow resumption after pause** — the agent was halfway through a multi-step workflow. The session ends. A new session begins with the same state but no fresh prompt. Does the agent pick up where it left off?

## Why these three

Every team that has run an agent in production for more than a week has hit at least one of these three failure modes. None of the published agent benchmarks (SWE-Bench, Terminal-Bench, AgentBench, GAIA) measure any of them, because all three require the agent to operate across context gaps that exceed a single benchmark run.

LHC is the first eval suite designed specifically to expose these failures in a reproducible, model-agnostic way.

> **Note (2026-05-09):** the sections below describe LHC v0.1. The benchmark has been superseded by **LHC v0.2** (24 decontaminated tasks, gap-mode ablation, audit-validated). The format, rubric, and harness shape carry forward unchanged. For the current authoritative methodology see [`evals/v0.2/AUTHORING.md`](../evals/v0.2/AUTHORING.md), [`evals/v0.2/DECISION.md`](../evals/v0.2/DECISION.md), and [`results.md`](results.md). Why v0.1 was retired: see the [external review journal entry](journal/2026-05-08-external-review-and-decontamination.md). LHC v0.1 task design is preserved below as the historical record.

## v0.1 task structure — 12 tasks

LHC v0.1 ships with **12 tasks**, organized as 3 categories × 4 difficulty tiers:

| | seed (xxx_001) | easy (xxx_002) | medium (xxx_003) | hard (xxx_004) |
|---|---|---|---|---|
| **state_recall** | 1 task | 1 task | 1 task | 1 task |
| **commitment** | 1 task | 1 task | 1 task | 1 task |
| **resumption** | 1 task | 1 task | 1 task | 1 task |

Each task is a triple `(setup, gap, probe)`:

- **setup**: a deterministic sequence of messages that establishes a goal, a commitment, or a workflow state.
- **gap**: synthetic intervening content (~6,000 tokens by default) — unrelated user/assistant exchanges designed to push the original setup deep into context or simulate a session boundary.
- **probe**: a final user turn that requires the agent to correctly recall, honor, or resume the setup.

The full task and rubric format is documented in [`benchmark-spec.md`](benchmark-spec.md).

## Scoring — binary 2D rubric

LHC v0.1 uses a **binary two-dimensional rubric**. Each task is scored on two independent binary dimensions:

- **Correctness** — `0` or `1`. Did the agent give the answer the task asked for?
- **Meta-awareness** — `0` or `1`. Did the agent proactively flag the long context gap, the standing rule, or the conflict between earlier setup and the current request?

A task's total score is `correctness + meta_awareness`, range `0..2`. The model's overall LHC score is the mean across all tasks, range `0.00..2.00`.

### Why binary, not 0–4

We tried a 0–4 scale first. The judge gave inconsistent middle scores ("a 2 vs a 3 — what's the difference?"). The binary 2D rubric eliminated that variance: judges either see the property or they don't. Cross-judge agreement on correctness rose from ~70% to ~95% after the switch.

Crucially, the two dimensions decouple:

- A model can be high-correctness, low-meta — an *executor* that does the right thing without narrating its reasoning.
- A model can be low-correctness, high-meta — a *narrator* that talks about the task instead of doing it.
- Models we have tested in the wild are mostly the first kind.

The split is the point. A single combined score would hide the most interesting axis.

## Running the eval

Any model exposing an OpenAI-compatible chat completions API can be scored:

```bash
# Score K2.6 with Sonnet as the judge (default cross-judge config)
python -m evals.runners.lhc --provider moonshot --judge-provider anthropic

# Score Sonnet against itself
python -m evals.runners.lhc --provider anthropic --judge-provider anthropic

# Score a locally-served Ember once trained
python -m evals.runners.lhc --provider slowlit
```

Results are reproducible: tasks, gap content, and probes are all deterministic and version-controlled. Same seed + same model = same scorecard, modulo the model's own sampling temperature.

## Validation methodology

Every published LHC scorecard is computed as the mean of **3 independent trials**. Within-model variance across the 12-task suite is typically ±0.04–0.08 on overall score, well below the meaningful effect sizes observed between models.

We additionally cross-validate the judge: any new target model is graded by both itself and by an independent flagship judge (currently Sonnet 4.6). Per-task agreement is published in [`findings.md`](findings.md). Cases where the two judges disagree are flagged for human review.

## Versioning

LHC is versioned. The v0.1 task set is **frozen**. New tasks land in v0.2 with their own published baselines.

A model's published LHC score is always tied to a specific LHC version. v0.1 scores remain comparable indefinitely, even as v0.2 ships.
