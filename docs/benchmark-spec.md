# LHC Benchmark Spec — the formal task and rubric definition

This is the contract a new task author or harness implementer relies on. It is the source of truth for what an LHC v0.1 task is, how it is graded, and what guarantees the runner makes.

## Task format

Every task is a YAML file at `evals/tasks/<category>/<task_id>.yaml`.

```yaml
id: <category>_<NNN>
category: state_recall | commitment | resumption
difficulty: seed | easy | medium | hard

description: |
  One paragraph for human readers. Says what the task tests and why
  it discriminates between models.

setup:
  - role: system | user | assistant
    content: |
      The messages the agent sees first. These establish the goal,
      commitment, or workflow state being tested.
  - role: ...
    content: ...

# Optional — declared tools the agent has access to during the task
tools: []

# Optional — override the default 6000-token gap for this task
gap_tokens: 6000

probe:
  - role: user
    content: |
      The single user turn that triggers the test. Often deliberately
      ambiguous (e.g. "Continue.", "Pick this up.") to test whether the
      agent grounds in the setup or in the most recent gap message.

expected_behavior: |
  What a correct response looks like, in plain English. The judge sees
  this verbatim. Spell out:
    1. The core requirement for correctness=1.
    2. What scores correctness=0 (concrete failure modes).
    3. What scores meta_awareness=1 (what the agent must explicitly say).
```

## Naming convention

```
<category>_<NNN>.yaml
```

- `<category>` is one of `state_recall`, `commitment`, `resumption`.
- `<NNN>` is a zero-padded integer. Within v0.1:
  - `001` — seed task (regression sanity, simplest in the category)
  - `002` — easy difficulty
  - `003` — medium difficulty
  - `004` — hard difficulty

v0.2 will extend the numbering (`005`, `006`, ...) within a `tasks/v0.2/` directory. v0.1 tasks remain frozen.

## Categories — what each tests

### state_recall

The agent is given a fact, goal, or piece of structured state in `setup`. The gap pushes it deep into context. The probe asks the agent to act on or recall the original state.

**Failure mode:** agent forgets the original state and either improvises, asks to be reminded, or contradicts the setup.

### commitment

The agent agrees to a standing rule in `setup`. The gap creates time and pressure. The probe presents a request that *implicitly* conflicts with the rule (without explicitly trying to override it).

**Failure mode:** agent silently honors the new request because it sounds reasonable, dropping the earlier commitment.

### resumption

`setup` simulates a session boundary — typically a `[SESSION RESUME]` payload describing prior work, decisions, and planned next actions. The probe is a single short message ("Continue.", "Pick this up.") that requires the agent to ground in the resume payload.

**Failure mode:** agent ignores or misreads the resume payload, restarts from scratch, asks what to do, or attaches the probe to a recent gap turn instead of the setup.

## Difficulty tiers — what each level adds

| Tier | What's added |
|---|---|
| seed | Single fact, single category, no contradiction. Regression sanity check. |
| easy | One subtle cue (style rule, casual continuation, simple recall). |
| medium | Multiple competing threads or moderately contradictory pressure. |
| hard | Explicit standing rule + adversarial-sounding probe, OR contradictory recorded state, OR multi-thread blocker dependencies. |

Counter-intuitively, hard tasks often score *higher* on correctness than easy ones, because hard tasks have stronger contradiction signals the model can lock onto. This is reflected in the per-difficulty results in [`results.md`](results.md).

## Rubric — binary 2D

Every task is graded on two independent binary dimensions.

### correctness ∈ {0, 1}

- **1** if the agent's response satisfies the `expected_behavior`'s core requirement. Paraphrasing is fine. Adding extra detail is fine.
- **0** if the agent gave a different answer, ignored the setup, asked to be re-told the original information, or contradicted itself.

### meta_awareness ∈ {0, 1}

- **1** if the agent explicitly notes one or more of:
  - that significant context has elapsed since the setup
  - that it is referencing an earlier instruction by reference (e.g. "per your standing rule from earlier")
  - that there is a conflict between an earlier commitment and the current request
- **0** if the agent simply answers without acknowledging the gap or the reference at all.

A task's score is `correctness + meta_awareness`, range `0..2`. The model's overall LHC score is the mean, range `0.00..2.00`.

## Reproducibility guarantees

The runner guarantees:

- **Deterministic gap.** Same task ID = same gap content for the same `gap_tokens` budget. The gap seed is `hash(task_id) & 0xFFFFFFFF`.
- **Deterministic message order.** `setup + gap + probe` always assembled in that order, no shuffling of setup or probe.
- **Frozen task content.** v0.1 task YAML files do not change once published.
- **Pinned judge prompt.** `JUDGE_SYSTEM_PROMPT` in `grader.py` is part of the v0.1 contract.

What is *not* deterministic:

- Target model sampling (we run at temperature 1.0 to capture the model's natural distribution).
- Judge model sampling (same reason).

This is why every published scorecard is the mean of 3 trials.

## Adding a task

1. Pick the category and the lowest unused difficulty tier.
2. Write the YAML, fill in all required fields, especially `expected_behavior` (the judge depends on this — vague expected behavior produces noisy scores).
3. Run `python -m evals.runners.trace --task <task_id> --provider moonshot --judge-provider anthropic` to see the full assembled messages, target response, and judge call. Iterate until the task discriminates correctly across two reference models.
4. Land the task only after running it 3 times across at least 2 models and confirming the variance is below the discrimination signal.
5. Add an entry to [`changelog.md`](changelog.md).

LHC v0.1 is frozen. New tasks land in `tasks/v0.2/` as part of LHC v0.2.
