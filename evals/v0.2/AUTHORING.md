# LHC v0.2 task authoring — process + checks

This directory holds the LHC v0.2 task suite, designed to be **uncontaminated** by Ember's training data. Read this before authoring any new task.

## Why v0.2 exists

LHC v0.1 had every test scenario also represented in training data via `based_on` derivative seeds. We can't compare a model trained on those seeds to one not trained on them and call the result a clean leaderboard. v0.2's whole point is to fix that.

See [`docs/journal/2026-05-08-external-review-and-decontamination.md`](../../docs/journal/2026-05-08-external-review-and-decontamination.md) for the full backstory.

## Authoring procedure

For each new task:

### 1. Pick a category and difficulty

Same distribution as v0.1: 8 per category (state_recall, commitment, resumption), 2 per difficulty (seed, easy, medium, hard) — yields 24 tasks. Each task lives at `evals/v0.2/tasks/<category>/<id>.yaml`.

### 2. Read the banned-overlap manifest before drafting

```bash
python evals/v0.2/build_banned_overlap.py    # regenerate if training data changed
$EDITOR evals/v0.2/banned_overlap.json       # read the relevant per-task bucket
```

The manifest is split into:

- **`scenario_defining_entities`** (~240 entries) — proper-noun entities that appear in training data. Don't reuse `Vertiv`, `Eaton`, `Magnify`, `Black Forest Labs`, `Acme Corp`, `Maria Okonkwo`, etc.
- **`domain_shape_phrases_seen`** (~36 entries) — lowercase or mixed-case scenario phrases like `audit log pipeline`, `24-hour soak`, `database migration`, `[SESSION RESUME]`, `Working memory`. Don't reuse the same scenario shape; pick a different domain entirely.
- **`global_banned_scaffolding_phrases`** — frame phrases like `[~6,000 tokens of unrelated agent chatter elapses here]` and `Working memory from previous session`. The v0.2 task framing must be visibly different. (Specifically: do NOT use `[SESSION RESUME]` payload format for resumption tasks. Pick an alternative resumption frame — see "Frame variation" below.)
- **`by_lhc_task[<lhc_task_id>]`** — per-LHC-task buckets. If you're authoring a state_recall task, look at all 4 v0.1 state_recall buckets to see what's already represented.

### 3. Pick a domain that is NOT in any bucket

Examples of *good* v0.2 scenario domains we have not used in training:

- **state_recall** alternatives: hospital triage protocols, restaurant kitchen line-up, broadcast control room cues, recipe scaling for catering, library-cart re-shelving, emergency-room intake.
- **commitment** alternatives: legal redlining workflow, music-licensing rights, ad-buy approval thresholds, scientific publication retraction handling, museum loan agreements.
- **resumption** alternatives: chess game adjournment, court-case continuation after recess, lab experiment continuation after instrument calibration, multi-day surgery, podcast multi-episode arc continuation.

The point isn't to be exhaustive — it's to push every author toward a *new* domain rather than a paraphrase of an existing one. If your draft scenario *feels familiar*, it's probably contaminated.

### 4. Frame variation (especially for resumption)

LHC v0.1 leaned hard on the `[SESSION RESUME] Working memory from previous session: …` frame. Models have memorized that exact frame. v0.2 should diversify:

- **Resumption frame A** — explicit checkpoint document: "Here's the open notebook from yesterday's session, page 14: …"
- **Resumption frame B** — chat-log continuation: "Continuing the conversation from the 3pm transcript: …"
- **Resumption frame C** — handoff note: "Outgoing-shift handoff log, item 3: …"
- **Resumption frame D** — task-tracker reload: "Loading active workflow from queue: …"

Pick at least 3 distinct frames across the 8 resumption tasks. None of them should be `[SESSION RESUME]` literally.

### 5. Run the local contamination check

> **Status (2026-05-10):** `check_task.py` was not written for the initial v0.2 batch. The 24 frozen tasks were decontaminated by manual review against [`banned_overlap.json`](banned_overlap.json) at authoring time (entity names, scaffolding phrases, domain shapes cross-checked by the author). The contamination check tooling at [`build_banned_overlap.py`](build_banned_overlap.py) is the load-bearing artifact — it scans seeds + synthetic training data and emits per-LHC-task contamination buckets, which is what the manual review checked against. A future task addition will land alongside `check_task.py`.

When the script lands, the procedure will be:

```bash
python evals/v0.2/check_task.py evals/v0.2/tasks/state_recall/foo.yaml
```

**All hits should be deliberate or justified in the task's manifest entry.**

### 6. Record provenance in the v0.2 manifest

Each task has one entry in [`evals/v0.2/manifest.json`](manifest.json), including its file path, sha256 (first 16 chars), category, difficulty, decontamination status, the v0.1 nearest-neighbor it replaces, and the rationale for non-overlap. The full manifest was generated 2026-05-10 from the existing 24 frozen tasks + `banned_overlap.json`. New tasks should append entries to that file with the same shape.

This manifest is the durable record of *why* each v0.2 task is held out from Ember's training distribution. If contamination is later suspected, this is what we audit.

### 7. Freeze the task suite before any model run

Once 24 tasks are authored and provenance recorded, **freeze** by:
- Adding tasks to `evals/v0.2/tasks/` and committing
- Tagging the commit `lhc-v0.2-frozen`
- Recording the commit SHA in the v0.2 results document

After freeze, no edits to existing tasks. Bug-fix edits create v0.2.1.

## Things to avoid

- **Don't paraphrase a v0.1 task.** Different industry, different entities, different probe wording. If the assistant could plausibly answer your draft and a v0.1 task with the same response, it's contaminated.
- **Don't author by inspecting current model outputs.** That selects for tasks that flatter the model. Author against the *spec* of what the rubric scores, not against what the model happens to currently produce.
- **Don't reuse the gap pool's chatter content.** The 16 NOISE_BLOCKS in `evals/runners/gap.py` are training-distribution artifacts at this point; if a v0.2 task's domain overlaps with what's in the gap, the model can confuse the two. Pick task domains that are *visibly distinct* from any of the 16 chatter blocks.

## Decision: tasks per category

For this 2-day cycle: **24 tasks** (8 per category × 3 categories). Reviewer noted this is smoke-quality; N=48 is required for a real shipping claim. If smoke results justify continuing, expand to N=48 in a follow-up cycle.
