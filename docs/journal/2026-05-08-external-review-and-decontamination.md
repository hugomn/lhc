# 2026-05-08 · External review invalidates v0.1.5 leaderboard claims; revised plan

**Status at end of session:** Path B (YaRN context extension) abandoned. New 2-day plan committed: Day 1 methodology fixes + LHC v0.2 build, Day 2 re-run for ground truth. Decision table to be written before Day 2 starts.

## Context — where we were

At session start we believed:
- Ember v0.1.5 iter-900 was the strongest 8B-class open model on LHC overall (mean 0.973), narrowly behind Mistral's Ministral-8B-2512 (mean 1.000).
- The 0.027 gap was driven primarily by `resumption_004`, where Ember scored 0/0/0 across 3 trials and Ministral scored 2/2/0.
- Ember's failure on `resumption_004` was a **structural attention limit** in Qwen3-8B's RoPE encoding across 6k-token gaps.
- The right next step was **Path B**: apply YaRN context extension to Qwen3-8B, retrain v0.1.5's recipe, time-box 2 days. If `resumption_004` cleared 1.0 mean and IFEval didn't regress, ship as Ember v0.2.

We had just published our v0.1.5 sweep + 8B-class leaderboard scorecards to `evals/results/published/` (commit `cc54d8a`).

## What we did

1. **Wrote a self-review brief** — `REVIEW_BRIEF.md` (gitignored) describing goals, methodology, hypotheses (H1-H7), timeline, results, and the proposed Path B plan. Hugo sent it to an external reviewer (different model lineage from our judge) along with explicit instructions to *find what we got wrong*.

2. **Received the review.** Reviewer flagged 6 methodology issues, challenged our diagnosis, and proposed a different next step.

3. **Verified each finding against the code and data.** All 6 confirmed:
   - **Finding 1 — benchmark contamination.** `data/seeds/v0.1.jsonl:38` and `data/seeds/v0.1.5.jsonl:15` contain the literal Vertiv/UPS/Eaton scenario from `resumption_004`. Counts of `based_on: resumption_004` across training data: 6 in v0.1 seeds, 4 in v0.1.5 seeds, 14-40 per generated synthetic shard. "Vertiv" appears 2× in `data/synthetic/v0.1.5/mlx_lora/train.jsonl`. Ember was trained on the exact scenario it's tested on.
   - **Finding 2 — hash-seeded gap is process-randomized.** `evals/runners/lhc.py:81` uses `hash(task["id"])`. Python string hash is process-salted unless `PYTHONHASHSEED` is fixed; `training/eval_one.py:108` launches each trial as a new process. Verified by running `python3 -c 'print(hash("resumption_004"))'` in 3 fresh subprocesses → 3 different values. Each trial tests a *different* version of each task.
   - **Finding 3 — gap pool is tiny and high-salience.** `evals/runners/gap.py:19` defines `NOISE_BLOCKS` as 16 fixed agent-task blocks. Ember's failure responses on `resumption_004` literally copy these blocks ("Got it. Continuing.", "Opened PR #847…", "Checked: 7 open dependabot alerts…"). The model is being task-hijacked by the gap.
   - **Finding 4 — train/eval gap mismatch.** Training data uses the literal placeholder string `[~6,000 tokens of unrelated agent chatter elapses here]` (see `data/generate.py:88`). Eval injects 16 real chatter blocks. The model has no training signal to ignore real chatter.
   - **Finding 5 — scorecards store only first 400 chars** (`evals/runners/lhc.py:270`). The judge sees the full response; we (and the reviewer) cannot independently audit any judge decision from published files.
   - **Finding 6 — `eval_one.py` ignores subprocess return codes** (`training/eval_one.py:117`). `rc` is printed but never checked. Combined with our prior knowledge that `sweep_v15.py` lost 6/9 trials, we have a pattern of silent eval failures.

4. **Conceded the diagnosis.** Reviewer's alternative — "recent-task continuation under distractor pressure" — is more parsimonious and better fits the evidence. The model's failure mode is *exactly* what the reviewer described: it copies gap content verbatim instead of engaging with the probe. This is not an attention-distance failure (the gap is only ~6k tokens, well inside Qwen3-8B's 32k context). It's a distractor-hijack failure caused by train/eval mismatch + recency bias.

5. **Sent a follow-up to the reviewer** with the revised plan (methodology fixes + LHC v0.2 build) and asked for refinements + falsifiability gates + the question we forgot to ask.

6. **Received refinement.** Reviewer endorsed the plan with 10 specific changes (see "Decisions" below).

7. **Decided N=24 for this 2-day cycle.** Reviewer noted N=48 is the minimum for a shipping claim (16 per category, 4 per category/difficulty), but explicitly accepted N=24 as smoke-quality if quality-per-task would otherwise drop. We're not making a shipping claim from this cycle — we're deciding *whether to invest more days*. N=24 is fit-for-that-purpose. If smoke results justify continuing, we expand to N=48 in a follow-up cycle.

## What we learned

**Verified facts:**
- Our v0.1.5 leaderboard claims are **invalid as written**. The training data contains the exact scenarios in the LHC test set. Comparisons to Ministral, Llama, etc. (which were not trained on LHC-derived data) are not apples-to-apples. The contamination affects v0.1 too, not just v0.1.5 — meaning we may have been overstating Ember's improvement over base Qwen3 the entire time.
- The hash-seeded gap means our reported variance is partly an artifact of testing different gap content per trial, not just model nondeterminism.
- The gap content is so concrete that Ember's failures are best explained by **task-hijack from the gap**, not attention-distance. YaRN does not target this failure.
- Storing only 400-char excerpts means our published scorecards cannot be independently audited against judge decisions. Future scorecards must store full prompt + full response + full gap.
- Our eval lifecycle silently swallows failures. `sweep_v15.py` lost 6/9 trials; `eval_one.py` and `sweep_8b_class.py` would do the same on a real failure.

**Updated hypotheses (replaces H5/H6/H7 from the review brief):**
- The bottleneck on `resumption_004` is **distractor pressure × train/eval gap mismatch**, not structural attention. (was H5)
- YaRN does not address the actual failure. Path B is wrong. (replaces H6)
- "Beating Ministral on resumption" is not measurable until we have a decontaminated benchmark and stable gaps. (replaces H7)

**New unstated assumption surfaced by reviewer:**
- *We had not asked whether fine-tuning is the right layer at all.* For agent-memory failures, deterministic resume-state validation, retrieval, and explicit session state are often stronger and cheaper than weight changes. Reviewer (round 2) accepts measuring model capability first but suggests a deterministic-checker baseline in parallel as a 2-3 hour artifact, not a separate path.

## Decisions

### D-01 — Abandon Path B (YaRN context extension)
- **Why:** the diagnosis Path B targets is wrong. Failure is gap-style sensitivity at 6k tokens, not attention-distance limits. Extending Qwen3-8B context from 32k → 128k does not address recency-distractor hijack.
- **Falsifiability gate:** if LHC v0.2 results show Ember failing across *all* gap modes including `none` (no gap at all), then attention/long-context might be a real issue and Path B becomes worth reconsidering. Until then, no.

### D-02 — Adopt revised 2-day plan with reviewer's refinements
- **Day 1 — methodology fixes (no model training):**
  1. Replace `hash(task["id"])` with `hashlib.sha256(...)` so gaps are identical across processes/machines/Python versions.
  2. Store **full prompt/messages + full response + full gap content** in scorecards (not just 400-char excerpts). Keep excerpt field for backward compat.
  3. Make per-task failures **fatal** — current `try/except continue` in `lhc.py:263` produces partial scorecards silently. Abort the run instead.
  4. Make `eval_one.py` / `sweep_v15.py` / `sweep_8b_class.py` abort on nonzero subprocess `rc`, and verify each scorecard has exactly 12 (or 24) task scores before declaring trial success.
  5. Build **LHC v0.2 — 24 hand-curated tasks**. No `based_on` overlap with anything in `data/seeds/*` or `data/synthetic/*`. Same rubric, same difficulty distribution. **Authoring process:** build banned-overlap list (domains, entity names, exact task shapes) from current training data first; author against that exclusion list; do not inspect current model outputs while authoring; freeze tasks before any model run; keep a manifest (author, date, intended category, forbidden nearest neighbor, why non-overlapping).
  6. Add **gap-mode ablation** per task: `none` (no gap), `placeholder` (matches training-data style — the literal `[~6,000 tokens…]` string), `neutral` (lorem-ipsum-ish filler), `current` (real agent chatter, today's eval style). Drop `adversarial` for this cycle — `current` is hard enough once we know the failure.

- **Day 2 — re-establish ground truth:**
  7. Build a **deterministic resume-state validator baseline** (~2-3 hours, in parallel). One-file oracle/parser that solves resumption tasks via schema validation, no LLM. Tells us whether "fine-tune for LHC" is chasing something trivial.
  8. Re-run on LHC v0.2 with stable hashing. Targets: Ember v0.1.5 iter-900, Qwen3-8B base, Ministral-8B-2512, Llama-3.1-8B. Gap modes: all 4. Trials: 3 each. Judge: Claude Opus 4.7.
  9. **Scorecard math:** 4 models × 4 gap modes × 3 trials = **48 scorecards** (corrected from my earlier sloppy "144" figure).
  10. Apply the decision table (see D-04) to the results.

### D-03 — Pre-register the primary endpoint
- **Primary endpoint:** LHC v0.2, `current` gap, overall + resumption category.
- **Artifact check:** `neutral` gap. If model behavior diverges drastically between `current` and `neutral`, the failure is gap-style sensitivity, not capability.
- **No goalpost moving.** This commitment is recorded *before* running anything.

### D-04 — Write the decision table BEFORE Day 2 starts
*(Reviewer's most important observation: "without that table, you risk using v0.2 as another narrative generator instead of a decision instrument.")*

The table will use paired comparisons (same task, same gap mode, same trial index) and bootstrap CIs over tasks. Reviewer's gates, accepted in full:

**Ember genuinely better than base Qwen3-8B** — convincing if all are true:
- `current` gap overall: Ember ≥ Qwen + 0.20
- `current` gap resumption: Ember ≥ Qwen + 0.30
- `neutral` gap overall: Ember ≥ Qwen + 0.10
- Paired bootstrap 95% CI lower bound for `current` overall delta > 0.00
- *(If Ember only wins `placeholder`, ignore it.)*

**Ember genuinely worse than Ministral** — convincing if all are true:
- `current` gap overall: Ministral ≥ Ember + 0.20
- `neutral` gap overall: Ministral ≥ Ember + 0.15
- `current` resumption: Ministral ≥ Ember + 0.30
- No gap mode shows Ember ahead by ≥ 0.10
- *(If Ministral only wins `current`, call it gap-style sensitivity, not general inferiority.)*

**LHC v0.2 itself is insufficient** — declare so if any are true:
- Opus rejudge instability on a 10% audit sample changes any model's overall by ≥ 0.10
- Model rank changes across `neutral` vs `current` by more than 2 positions
- 95% CIs for Ember/base and Ember/Ministral both include deltas of ±0.15
- Manual audit finds ≥ 5% materially wrong judge labels
- Gap mode explains more variance than model identity

**Decision matrix (action per outcome):**
- Ember beats base AND matches Ministral → ship only after held-out *product* tasks agree (not just LHC v0.2)
- Ember beats base BUT loses to Ministral → switch base model OR train against distractors (re-decide which based on data)
- Ember loses to base → stop the v0.1.5 line entirely
- All models collapse on `current` → benchmark is measuring recency distractors; build deterministic checker baseline first, then re-decide
- LHC v0.2 declared insufficient → stop, build a different benchmark (LongBench / RULER / hand-built product tasks) before any further training

### D-05 — Update findings.md with methodology caveat
The published v0.1.5 leaderboard (in `docs/findings.md`, `docs/results.md`, scorecards in `evals/results/published/`) is not deleted — it remains the historical record of *what we believed before this review*. But a top-of-file caveat is added pointing readers at this journal entry.

## Open questions

- **OQ-01:** What's the right floor for held-out *product* tasks before any HuggingFace publication? Reviewer didn't specify. Likely 8-12 tasks drawn from real agent workflows, not synthetic.
- **OQ-02:** If Day 2 says LHC v0.2 itself is insufficient, what's the right replacement? LongBench and RULER are public; both have known issues. May need a hybrid.
- **OQ-03:** The deterministic-checker baseline (D-02 step 7) — should it cover all categories or just resumption? Resumption seems most amenable; commitment less so. Decide while building.
- **OQ-04:** v0.2 task authoring — is one author (Hugo + Claude) enough, or should we have a second pair of eyes for the banned-overlap check before freezing? Reviewer's "blind-ish process" implies yes; logistics may force no.

## Pointers

**Commits this session:**
- `3df52ec` — Stage 4: v0.1.5 dataset, sweep tooling, OpenRouter provider
- `cc54d8a` — Publish Stage 4 scorecards: v0.1.5 sweep + 8B-class leaderboard
- *(this commit)* — Journal entry + findings caveat

**Files implicated by reviewer:**
- `evals/runners/lhc.py:81` — hash-seeded gap (Finding 2)
- `evals/runners/lhc.py:263` — silent task-skip (Finding 6)
- `evals/runners/lhc.py:270` — 400-char excerpt only (Finding 5)
- `evals/runners/gap.py:19` — 16 fixed `NOISE_BLOCKS` (Finding 3)
- `data/generate.py:88` — placeholder-only training gap (Finding 4)
- `training/eval_one.py:117` — ignored `rc` (Finding 6)
- `training/sweep_v15.py:107` — same (Finding 6)
- `training/sweep_8b_class.py:42` — same (Finding 6)
- `data/seeds/v0.1.jsonl:38` — Vertiv/UPS contamination (Finding 1)
- `data/seeds/v0.1.5.jsonl:15` — Vertiv/UPS contamination (Finding 1)

**Scorecards to treat as historical, not authoritative:**
- `evals/results/published/v0.1.5/*` — contaminated, all variants
- `evals/results/published/8b-class-leaderboard/*` — fine for non-Ember models in isolation, but the rank-vs-Ember comparisons are invalid

**External artifact (gitignored, was sent to reviewer):**
- `REVIEW_BRIEF.md` — round-1 brief
- *(no file kept for round-2 follow-up; verbatim recorded in this entry)*
