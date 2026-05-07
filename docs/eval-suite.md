# Long-Horizon Coherence (LHC) — eval methodology

> The first open benchmark for agent coherence across long context gaps.

## What LHC measures

LHC is built on a single hypothesis: **the failure mode that matters most
for production autonomous agents is not single-turn quality, it is whether
the agent is the same agent at hour 24 that it was at hour 0.**

LHC isolates and measures three specific competencies:

1. **State recall after intervening noise** — the agent set a goal at T0.
   At T1, after N intervening unrelated tool calls and tokens, can it still
   correctly act on the original goal?
2. **Decision consistency under contradictory input** — the agent made a
   commitment at T0. At T1, a request arrives that conflicts with that
   commitment. Does the agent recognize the conflict, or does it overwrite
   the commitment silently?
3. **Workflow resumption after pause** — the agent was halfway through a
   multi-step workflow. The session ends. A new session begins with the
   same state but no fresh prompt. Does the agent pick up where it left off?

## Why these three

Every team that has run an agent in production for more than a week
has hit at least one of these three failure modes. None of the published
agent benchmarks (SWE-Bench, Terminal-Bench, AgentBench, GAIA) measure
any of them, because all three require the agent to operate across context
gaps that exceed a single benchmark run.

LHC is the first eval suite designed specifically to expose these failures
in a reproducible, model-agnostic way.

## The 30-task structure (v0.1)

Each task is a triple `(setup, gap, probe)`:

- **setup**: a deterministic sequence of tool calls and observations that
  establishes a goal, a commitment, or a workflow state.
- **gap**: synthetic intervening content — unrelated tool calls, irrelevant
  user turns, noise — designed to push the original setup deep into context
  or simulate a session boundary.
- **probe**: a final user turn that requires the agent to correctly recall,
  honor, or resume the setup.

The 30 tasks are split:

- **10 state-recall tasks** — original goal must survive 50–500 intervening
  tool calls.
- **10 commitment tasks** — original commitment must be honored against
  contradictory probes.
- **10 resumption tasks** — workflow must resume after a simulated session
  boundary with state passed via memory primitives only.

## Scoring

Each task is graded on a 0–4 rubric:

- **0** — agent ignores or contradicts the setup
- **1** — agent partially recalls but acts incorrectly
- **2** — agent recalls correctly but reasoning is degraded
- **3** — agent recalls and acts correctly
- **4** — agent recalls, acts correctly, and proactively flags the gap or
  contradiction in its reasoning trace

Scores are averaged per category and overall. A model's LHC score is a
single number from 0.00 to 4.00.

## Running the eval

Any model exposing an OpenAI-compatible chat completions API can be scored:

```bash
python -m evals.runners.lhc \
    --model ember-v0.1 \
    --base-url https://api.cinderlabs.ai/v1 \
    --api-key $CINDER_API_KEY \
    --output evals/results/ember-v0.1.json
```

Results are reproducible: tasks, gap content, and probes are all
deterministic and version-controlled.

## Baseline targets (to be filled in upon publication)

| Model | Overall | State Recall | Commitment | Resumption |
|---|---|---|---|---|
| Kimi K2.6 (base) | TBD | TBD | TBD | TBD |
| DeepSeek V3.2 | TBD | TBD | TBD | TBD |
| Claude Sonnet 4.6 | TBD | TBD | TBD | TBD |
| GPT-5 | TBD | TBD | TBD | TBD |
| **Ember v0.1** | TBD | TBD | TBD | TBD |

The first published result will be the K2.6 baseline, released alongside
this methodology document.

## Versioning policy

LHC is versioned. The v0.1 task set is frozen. New tasks may be added in
v0.2, but v0.1 results remain comparable indefinitely. Models score
themselves against a specific LHC version.
