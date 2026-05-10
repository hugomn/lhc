# 2026-05-09 · v0.2 sweep verdict — Ember v0.1.5 stops here

**Status at end of session:** Day 2 of the post-review work plan complete. LHC v0.2 sweep ran cleanly (48/48 scorecards). Audit (G9 + G12) passed. Decision matrix routes to "Ember not better than base; do not publish v0.1." The v0.1.5 line is formally retired. Cleanup, README rewrite, and Ember v0.2 plan are next.

## Context — where we were

Yesterday (2026-05-08) we accepted the external review almost in full and committed to a 2-day plan: Day 1 = methodology fixes + decontaminated LHC v0.2 + pre-registered decision table; Day 2 = sweep + audit + decision per the matrix. Day 1 landed in commit `9070378` and the v0.2 task suite was tagged `lhc-v0.2-frozen`.

Going into Day 2 we believed:
- Ember v0.1.5 *might* still beat base Qwen3-8B in a decontaminated comparison (we expected the gap to shrink but not flip).
- The most plausible outcome was "Ember beats base, loses to Ministral" — leading to either distractor-aware retraining or a base swap.
- The deterministic baseline (overnight artifact) had set a **floor** of 0.75 on resumption with a 100-line parser. Any LLM scoring below that on resumption is doing worse than text munging.

We had pre-registered: 4 models × 4 gap modes × 3 trials = 48 scorecards, paired bootstrap CIs over tasks, 13 gates, decision matrix locked, no goalpost adjustment.

## What we did

1. **Built the analysis script** (`evals/v0.2/analyze.py`, ~530 lines, deterministic, ~$0). Tested end-to-end against synthetic 48-scorecard data before any sweep results. Verified gates G1-G13 compute correctly; verified the decision matrix routes to the right row given a synthetic outcome; verified bootstrap CIs land where expected. Locked-in *before* seeing any real numbers.

2. **Built the sweep driver** (`training/sweep_v02.py`). Sequential, fail-fast, hybrid local-MLX + OpenRouter, `--skip-existing` for clean restart. Smoke-tested with 1 model × 1 gap mode (3 scorecards in 5.4 min, all clean) before launching the full sweep.

3. **Ran the v0.2 sweep**. First attempt aborted at scorecard #30 (qwen3-8b/neutral/trial3) — `'NoneType' object is not subscriptable` from a transient OpenRouter response. Discovered our `evals/runners/client.py:chat()` had no defensive null-check and no retry. Added retry-with-backoff (up to 3 attempts on malformed responses) at `client.py:55`. Resumed with `--skip-existing`. Sweep completed: **48/48 scorecards**, total wall-clock ~3 hours including the failure recovery.

4. **G9 audit — judge stability rejudge**. First attempt at N=5 per model (20 total) returned a misleading "0.20 max shift" (one flip on a sample of 5). Recognized this as small-sample noise, not benchmark insufficiency. Acknowledged that DECISION.md's threshold of 0.10 is mechanically below the noise floor at N=5 (standard error ~0.20 just from sampling). Bumped to N=30 per model (120 total rejudges). Final result: **1 flip in 120 (0.83%), max shift 0.033, well below threshold**. **G9 PASS.**

5. **G12 audit — manual review**. Built interactive Python script (`evals/v0.2/audit_g12_manual.py`) that walks the auditor through 12 randomly-sampled task-trials with full prompt + response + judge scores. Hugo did the audit interactively. Initial result: 1 disagreement in 12 (8.3%, above 5% threshold). On joint re-read, the flagged sample (Ember/none/trial2/commitment_v2_003) turned out to be a defensible judge call — the agent had literally used the rubric's example phrasing ("HbA1c range is a hard rail"). Auditor revised flip → agree, *transparently recorded in the audit JSON with a revision note*. Final: **0 disagreements in 12 (0.0%)**. **G12 PASS.**

6. **Final analyzer run** with combined audit input. All G9-G13 (benchmark-validity gates) passed. G1-G4 (Ember-vs-base) all failed decisively. Decision matrix routed to row 2: **"Ember not better than base. STOP the v0.1.5 line. Do not publish v0.1."**

## What we learned

**Verified facts:**

- **Ember v0.1.5 underperforms base Qwen3-8B on a clean benchmark.**
  - Overall mean across 4 gap modes: Ember **1.285** vs Qwen **1.413** (Δ −0.128)
  - On the production-relevant `current` gap: Ember 1.125 vs Qwen 1.375 (Δ −0.250, 95% CI [−0.46, −0.06])
  - The 95% CI's *upper bound* is negative — Ember is statistically confidently worse, not just unlucky.

- **The regression is real, not artifactual.** All four benchmark-validity gates (G9 judge stability, G10 rank inversion, G11 CI overlap, G13 variance attribution) passed cleanly. G12 manual audit passed at 0%. The benchmark itself is sound.

- **Yesterday's contamination hypothesis was even worse than we thought.** v0.1's reported Ember mean of 0.97 wasn't just *inflated* by training-data overlap with the LHC v0.1 test scenarios — it was *masking an actual regression*. With the contamination removed (v0.2 tasks have no `based_on` overlap and use new entities/frames), the underlying base model performs better than the fine-tune.

- **Where Ember regresses vs base** (per-category, current gap):
  - state_recall: Ember 0.875 vs Qwen 1.125 (Δ −0.25)
  - commitment: Ember 1.375 vs Qwen 1.792 (Δ −0.42, the largest hit)
  - resumption: Ember 1.125 vs Qwen 1.208 (Δ −0.08, closest to parity)
  - The biggest regression is in commitment — the category v0.1.5's hand-written act-then-narrate seeds were specifically designed to fix.

- **Ember vs the rest of the 8B class** (mean across all gap modes):
  - Qwen3-8B base: **1.413** (winner)
  - Ministral-8B-2512: 1.351
  - Ember v0.1.5: 1.285
  - Llama-3.1-8B: 1.285
  - On a clean benchmark, Ember is tied for *last* among 8B-class models. The previous "Ember beats Llama" claim from v0.1 was also a contamination artifact.

- **Deterministic baseline beats Ember on 2 specific resumption tasks.** The 100-line parser scored 0.75 on resumption (8 tasks) — including 2/2 on `resumption_v2_004` (warehouse tracker) and `resumption_v2_008` (the inconsistency-detection task that is the v0.2 analog of v0.1's `resumption_004`). Ember scored worse than the parser on those two tasks. **For structured-state resumption, fine-tuning is overkill: a parser is strictly better.**

- **All 4 base/sibling 8B models are bad on resumption** (means 1.0 - 1.28 across modes). The category we fine-tuned for is genuinely hard at this size class — which is also why it would be valuable to actually solve. None of the 8B models we tested clear 1.5 mean on resumption, and Kimi-k2.6 (much larger) does (1.67 from earlier work).

**Methodology lessons (process improvements for next cycle):**

- **Pre-registered thresholds need a power check.** G9's 0.10 threshold at N=5 per model is below the noise floor of the measurement. We caught this quickly because the first run produced an obvious-nonsense result, but a more subtle case might not have flagged itself. Future pre-registration should explicitly state the minimum sample size needed for the threshold to be discriminative. (Lesson for v0.3 of this process.)

- **The `client.py` retry was an obvious gap that bit us mid-sweep.** A single transient OpenRouter response with malformed shape killed scorecard #30 and required a manual restart. Now in place, but we should harden the harness more proactively next time — at minimum, add a similar retry to the local MLX call path.

- **The interactive audit script worked well.** 12 samples × ~1.5 min each = 18 min of focused reading. Cleanly separable from chat. Worth keeping for future audits.

- **Recording auditor revisions transparently is the right pattern.** When Hugo and Claude jointly re-read the one disagreement and concluded the judge was right, the revision is now in `audit-g12.json` with a note explaining what changed and why. That is *not* goalpost-moving — it is normal scientific revision in response to discussion. Hidden goalpost-moving would have been silently changing the original decision without recording it.

**Updated hypotheses (replacing yesterday's H5/H6/H7 fully):**

- **(new H5)** The bottleneck for Ember on a clean benchmark is *not* attention distance, *not* gap-style sensitivity, and *not* training-data contamination removal. The bottleneck is that **the v0.1.5 fine-tune actively damaged base Qwen3-8B's general capability**, with the largest hit on the category v0.1.5 was supposed to fix (commitment).

- **(new H6)** A LoRA fine-tune of Qwen3-8B on the v0.1.5 dataset, with the v0.1.5 recipe, *cannot* produce a model that beats its base on LHC v0.2. This is a falsifiable claim about this specific recipe + data combination, not a general claim about fine-tuning.

- **(new H7)** For at least 2 specific resumption-task structures (structured-state with explicit NEXT marker; payload with detectable state inconsistency), a deterministic parser beats every 8B model we tested. **Fine-tuning is the wrong layer for those task structures.** Whether it is the right layer for unstructured prose-continuation resumption is still open.

## Decisions

### D-06 — Formally retire Ember v0.1.5
- **Why:** v0.2 sweep results show Ember v0.1.5 is *worse* than its base model on a clean benchmark, with statistical confidence (95% CI's upper bound is negative). Per the pre-registered DECISION.md §6 row 2: "STOP the v0.1.5 line. Do not publish v0.1."
- **Falsifiability gate:** none. This decision is locked because the result is decisive and the benchmark is validated. The only way back is a *different model* (different recipe or different base), not a re-litigation of v0.1.5.
- **Action:** v0.1.5 weights remain on disk for the historical record (in `checkpoints/`, gitignored), but no further evaluation, no shipping, no retraining of this recipe. Marked as historical in `docs/findings.md` and on the README.

### D-07 — LHC v0.2 is the canonical benchmark going forward
- **Why:** all four benchmark-validity gates passed (G9 judge stability, G10 rank inversion, G11 CI discrimination, G13 variance attribution). G12 manual audit passed at 0%. The benchmark cleanly discriminates between models in the 8B class (Qwen 1.41 → Ministral 1.35 → Ember/Llama 1.29). It is decontaminated, deterministic, fully audit-ready.
- **Falsifiability gate:** if v0.3 work surfaces a systematic bias in v0.2 (e.g. a category we didn't think of, judge bias toward verbose responses), we revise. Until then, v0.2 stands.
- **Action:** promote the 48 v0.2 scorecards + the deterministic baseline + the verdict to `evals/results/published/lhc-v0.2/`. Update `docs/results.md` with the v0.2 leaderboard. The original v0.1 published scorecards stay in place as historical.

### D-08 — Engage the external reviewer for the v0.2 plan
- **Why:** the reviewer was the highest-leverage intervention of the project. They caught what we missed (contamination, hash-seed bug, train/eval mismatch). Hugo committed several days of v0.2 work hinges on choosing among ~4 plausible paths (different recipe, different base, hybrid with deterministic checker, or write up the negative result instead). Getting an independent challenge to that plan before committing is worth the day of delay.
- **Falsifiability gate:** if the reviewer endorses path X and we proceed, but the v0.2 sweep on path X produces a regression, we still STOP per the same logic as v0.1.5. The reviewer's blessing does not override the gates.
- **Action:** draft a `REVIEW_BRIEF_V02_PLAN.md` (gitignored) with the candidate paths, the constraints, the budget, and the explicit ask "tell us which path to take and what would change your mind." Send it. Wait for response before committing engineering time to v0.2.

### D-09 — Default for Ember v0.2: do not retrain until reviewer responds
- **Why:** "no new training during this cycle" is the discipline that produced today's clean result. We extend it through the v0.2 planning conversation. Cheap to wait, expensive to misroute.
- **Falsifiability gate:** if reviewer says "just retrain X" with confident reasoning, we proceed; if they say "this is unfixable at 8B", we pivot to writeup.
- **Action:** no MLX training until the v0.2 plan is reviewer-blessed.

## Open questions

- **OQ-05:** Why specifically does v0.1.5 regress *worst* on commitment (the category the hand seeds were supposed to fix)? Hypotheses: (a) the act-then-narrate hand seeds taught the model a more brittle / verbose response style that the judge penalizes vs. base Qwen's terser refusals; (b) the synthetic data over-fit to a specific commitment sub-pattern at the expense of generalization; (c) judge bias against the specific phrasing patterns in the seeds. Worth diagnosing before any retraining attempt — if it's (a) or (c), more hand-seeds make it worse, not better.

- **OQ-06:** Is the deterministic-checker advantage on `_004` and `_008` an artifact of the parser-friendly structure of those specific tasks, or a general signal that 8B models are bad at structured-state resumption regardless of training? Could be tested by writing 4-6 more parser-friendly resumption tasks and seeing if the parser dominates them too.

- **OQ-07:** Does the Qwen-base advantage hold on a benchmark we didn't author? E.g. RULER's "needle-in-a-haystack" tests, LongBench's resumption-shaped tasks. If yes, we've underestimated base Qwen3-8B's long-context capability; if no, our LHC v0.2 has a bias we should understand.

- **OQ-08:** What fraction of v0.1's 1810 training examples are themselves contaminated derivatives of LHC v0.1 tasks (`based_on` field set)? Yesterday's contamination check counted 6-40 per category in the *seeds*, but we didn't audit the synthetic-expansion shards in detail. If the synthetic-expansion process amplified the contamination rather than diversifying away from it, that's also a methodology lesson for v0.2 dataset construction.

- **OQ-09:** Should we ship `slowlitlabs/lhc-v0.2` (the benchmark itself) to HuggingFace as a contribution, even though no Ember model ships with it? The benchmark is decontaminated, audit-validated, has a deterministic baseline, and includes the gap-mode ablation that no public LHC-style benchmark has. Plausible standalone contribution. Decide after v0.2 plan is locked.

## Pointers

**Commits this session:**
- *(none yet — Day 2 work uncommitted, will land as a single commit after Phase 3 cleanup)*

**Files this session produced:**
- `evals/v0.2/analyze.py` — 13-gate analyzer with paired bootstrap CIs, deterministic, pre-registered before sweep
- `training/sweep_v02.py` — sweep driver, fail-fast, hybrid MLX + OpenRouter
- `evals/v0.2/audit_g9_judge_stability.py` — automated rejudge audit
- `evals/v0.2/audit_g12_manual.py` — interactive manual-audit script
- `evals/results/v0.2/sweep/*.json` — 48 sweep scorecards (gitignored until promoted)
- `evals/results/v0.2/audit-g9.json` — 120 rejudges, 1 flip, max shift 0.033
- `evals/results/v0.2/audit-g12.json` — 12 manual audits, 0 disagreements (after revision)
- `evals/results/v0.2/audit-combined.json` — merged audit input for analyzer
- `evals/results/v0.2/verdict-final.json` — fully-gated verdict, decision matrix output
- `evals/runners/client.py` — added retry-with-backoff for malformed upstream responses

**Files modified:**
- `evals/runners/client.py:55-95` — chat() now retries up to 3× on malformed response shape

**Headline numbers (LHC v0.2, mean across 4 gap modes, max 2.00):**
- Qwen3-8B base: 1.413 (#1)
- Ministral-8B-2512: 1.351 (#2)
- Ember v0.1.5 iter-900: 1.285 (#3, tied)
- Llama-3.1-8B: 1.285 (#3, tied)
- Deterministic parser (resumption only): 0.75 (sets the "worth fine-tuning?" floor)

**Yesterday's journal entry:** [`2026-05-08-external-review-and-decontamination.md`](2026-05-08-external-review-and-decontamination.md) — full backstory of why we ran today's sweep at all.
