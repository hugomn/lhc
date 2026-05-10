# 2026-05-10 · MLX replication, diagnostic closure — Ember v0.1.5 lands as a null result

**Status at end of session:** Two more rounds of external review (round 3 and round 4) completed in one day. Yesterday's "Ember regresses, stop the line" verdict is rebuilt as **"Ember v0.1.5 is statistically indistinguishable from base Qwen3-8B under matched local inference; it does not meet the bar for release."** The decision is unchanged (no v0.1.5 release, Path E ships) but the framing is honest. We also discovered an MLX replication issue worth a small section in the methodology writeup. Day ends ready to start the Path E artifacts.

## Context — where we were at start of day

Yesterday's verdict (commit `5f454e5`) said Ember was demonstrably worse than its base, 95% CI [−0.46, −0.06] on the `current` gap mode, with `state_recall_v2_004` as the most striking single signal: a byte-identical confident-wrong response across all 3 trials.

We sent the v0.2 plan + that verdict to the external reviewer in `REVIEW_BRIEF_V02_PLAN.md`. The reviewer (round 2) caught two methodology holes neither the plan nor the verdict acknowledged:

1. **Inference-config asymmetry.** Ember runs through local MLX with the slowlit provider's `/no_think` system prefix. The other three models (Qwen3-8B base, Ministral-8B-2512, Llama-3.1-8B) ran through OpenRouter with no such prefix. Different inference setups.
2. **Fake n=3 trial variance.** Ember's local MLX sampling appeared deterministic — all 3 trials per cell were byte-identical. The other 3 models had real trial-to-trial variance. The 95% CI was computed treating all 4 models as if they had real variance.

Reviewer's recommendation: **no-training diagnostic first.** Run base Qwen3-8B locally via MLX with the same `/no_think` prefix, then re-compare. Only after that should we commit to any of the 5 candidate paths (A diagnose / B different recipe / C different base / D hybrid / E ship benchmark + parser).

Hugo's framing for the day: ship Path E as the immediate move; longer arc still alive (willing to rent GPUs eventually for a Clayer-grade attempt). No rush.

## What we did

1. **Built the round-3 diagnostic.** `evals/v0.2/diagnostic_local_qwen.py` — base Qwen3-8B via local MLX, same `/no_think` prefix, capped prompt cache (lesson learned the hard way after a Metal GPU OOM at ~12 GB cache on the first attempt). `evals/v0.2/diagnostic_compare.py` — pre-written analysis with three pre-registered branches: VERDICT SURVIVES, VERDICT OVERTURNED, AMBIGUOUS.

2. **Ran the round-3 diagnostic at n=1.** Result: apples-to-apples Δ E−L on `current` overall = −0.04, vs yesterday's confounded reading of −0.25. The pre-registered branch routed to AMBIGUOUS: "Yesterday's strong claim was inflated by inference confound. Path E is still defensible, but the regression claim should be softened."

3. **Sent round-3 brief to reviewer.** `REVIEW_BRIEF_V02_DIAGNOSTIC.md` — narrow: "Did we read the diagnostic correctly? Is Path E still right?"

4. **Round-3 reviewer endorsed**, with two action items:
   - **Mandatory:** replace "Ember demonstrably regresses" with "Under matched local MLX inference, Ember v0.1.5 is not measurably better than base Qwen3-8B on LHC v0.2. The previous stronger regression estimate was inflated by inference-configuration asymmetry. A small set of confident-wrong structured-state failures remains."
   - **Optional but cheap:** rerun one Ember `current`/`neutral` pass under the same capped-cache config to close the symmetry nuisance — Ember scorecards in the diagnostic still came from the original sweep, while Qwen-local was newly run under capped cache. Reviewer said this would not change the decision; just makes the audit record clean.

5. **Did the optional Ember rerun** (`evals/v0.2/diagnostic_ember_rerun.py`). Expected near-identical scores to the original sweep trial1 (deterministic MLX, same model, same prefix). **Got materially different scores.** Ember `current` overall went from 1.125 → 1.292. `state_recall_v2_004` went from 0/2 byte-identical → 1/2 with completely different response text. `resumption_v2_008` went from 0 → 2.

6. **Investigated the discrepancy.** Compared response text directly — entirely different generations. Three possibilities: (a) MLX is not actually deterministic across server restarts, (b) the capped prompt cache changed generation, (c) judge non-determinism on boundary cases. Picked option (a) as most likely given the magnitude of text differences.

7. **Replicated both models at proper n=3 with fresh server starts per trial.** Built `evals/v0.2/diagnostic_ember_replicate.py` and `evals/v0.2/diagnostic_qwen_replicate.py`. Both restart the MLX server between trials with identical capped-cache flags. (Hit one transient hang on the qwen-trial-3 server — broken-pipe loop after a client disconnect; killed and restarted, the script's skip-existing logic let trial 3 alone re-complete.)

8. **Recomputed the comparison** with the rewritten `diagnostic_compare.py` — task-bootstrap CI conditional on the observed 3 restart trials, paired across tasks, 10k iterations.

   | Gap | Ember mean (n=3) | Qwen-local mean (n=3) | Δ E−Q | 95% CI (task-bootstrap)¹ |
   |---|---:|---:|---:|---|
   | `current` | 1.222 | 1.181 | **+0.042** | [−0.139, +0.222] |
   | `neutral` | 1.319 | 1.333 | **−0.014** | [−0.139, +0.111] |

   Both CIs cross zero. **Statistical tie on both gap modes.**

   ¹ Hierarchical bootstrap over (task, trial) would be wider, not narrower. Sufficient to reject shipping; not for fine ranking.

9. **Sent round-4 brief** (`REVIEW_BRIEF_V02_NONDET.md`) — three narrow questions: is the n=3 paired bootstrap sound, is the MLX replication finding worth publishing, does the revised verdict change Path E timing.

10. **Round-4 reviewer endorsed.** Final wording for public framing:
    > "Ember v0.1.5 is statistically indistinguishable from base Qwen3-8B under matched local inference; it does not meet the bar for release."
    
    Drop both stronger claims: "Ember regresses" and "stable confident-wrong style collapse." Phrase the MLX finding narrowly as a replication-protocol observation, not a global non-determinism claim.

11. **Promoted diagnostic scorecards** to `evals/results/published/lhc-v0.2/diagnostic-ember-rerun/` and `diagnostic-local-qwen/`. Updated `evals/results/published/lhc-v0.2/README.md` to reflect the diagnostic's reframing.

## What we learned

**About v0.1.5 (the model):**

- **Verified:** Ember v0.1.5 is statistically indistinguishable from base Qwen3-8B on LHC v0.2 under matched local-MLX inference. Hugo's bar ("significant improvement on at least one functionality") is not met. v0.1.5 does not ship.

- **Withdrawn:** "Ember regresses against base, 95% CI [−0.46, −0.06]." That CI was inflated by inference-config asymmetry (`/no_think` for Ember, no prefix for OpenRouter Qwen) — about 5/6 of the gap was confound.

- **Withdrawn:** "Ember exhibits a stable confident-wrong style collapse on `state_recall_v2_004`." That was anchored on within-session byte-identical responses; across fresh server starts, Ember scores [1, 0, 2] on the same task — high-variance, not a stable failure mode.

- **What's left:** the `state_recall_v2_004` finding goes from "smoking-gun stable regression" to "interesting per-task variance worth noting." The narrower `state_recall_v2_005` and `commitment_v2_008` patterns also disappear under proper n=3.

**About MLX replication (the methodology side-finding):**

- **In our MLX-LM server setup on Apple Silicon, outputs were stable within a single server session but varied across fresh server starts.** Per-cell stdev across 3 restart trials: 0.02–0.13 on overall mean. 6 of 24 tasks score-flip per side.

- **We have not isolated the source.** Could be MLX-LM server, Metal kernels, cache state, sampling defaults, warmup, or process init. Round-4 reviewer cautioned against the broader claim "MLX is non-deterministic" and we are taking that caution. The narrow, defensible claim is: **benchmark replications of MLX-served models should restart the server between trials or explicitly state they are within-session repeats.**

- **The original sweep's "byte-identical n=3 trials" was a within-session repeat**, not three independent samples. Anyone running similar benchmarks needs to know this.

**About the methodology-review-loop itself:**

- **Four rounds of external review in roughly 72 hours.** Each round caught a real issue. Rounds 1 + 2 caught structural problems (contamination, hash bug, inference confound). Rounds 3 + 4 emerged from us *trying to address* the round-2 fix and discovering the next layer.

- **The cost of being wrong in public is much higher than the cost of one more round of review.** Each round changed our public framing materially: round 2 from "Ember beats base after retraining" → "Ember worse than base, ship parser instead"; round 3 from "Ember worse" → "Ember not measurably better"; round 4 from "Ember not measurably better with style-collapse coda" → "Ember statistically indistinguishable, no style-collapse claim, MLX replication caveat."

- **The pre-registered branches saved us.** At each round, having a written-down "what would make us conclude X vs Y" let us route on data instead of vibes. Round 3 routed to AMBIGUOUS, round 4 routed to TIE, both per the pre-registration rather than retrofitted.

- **One mistake to learn from:** in the round-3 brief we wrote "the byte-identical wrong response is a real finding about the v0.1.5 weights" before we had verified it was a fresh-session property. A reader who only saw round-3 would have walked away with a false claim. Round 4 caught it because we did the optional rerun — but we should have done that rerun *before* sending round 3, not after.

## Decisions

- **D-10.** Verdict for v0.1.5 is "statistically indistinguishable from base under matched local inference; does not meet the bar for release." This wording is the public stance. v0.1.5 weights stay on disk; not published. (Round-4 reviewer's required phrasing.)

- **D-11.** Ship Path E (LHC v0.2 → HuggingFace, deterministic baseline parser, methodology writeup). The methodology writeup includes the MLX replication-protocol observation, phrased narrowly per round-4 reviewer Q2.

- **D-12.** No more training in this cycle. Hugo's "no rush, willing to rent GPUs eventually for a Clayer-grade attempt" framing holds. v0.2 cycle closes after Path E artifacts ship.

- **D-13.** Diagnostic scripts (`diagnostic_local_qwen.py`, `diagnostic_ember_rerun.py`, `diagnostic_*_replicate.py`, `diagnostic_compare.py`) are part of the methodology contribution and stay in the repo. Scorecards are promoted to `evals/results/published/lhc-v0.2/diagnostic-*`.

- **D-14.** The methodology writeup adds, at minimum:
  - The 4-round review loop and what each round caught
  - The matched-inference diagnostic and why it was needed
  - The MLX session-vs-restart replication observation (narrowly phrased)
  - A pointer to the pre-registered decision branches as the load-bearing process discipline

## What's next (Path E proper)

1. Push the LHC v0.2 task suite to HuggingFace as `slowlitlabs/lhc-v0.2`. Include scorecards, audits, decision matrix, and the diagnostic.
2. Polish the deterministic-baseline parser to a publishable standalone repo or HF Space (resumption-only, ~100 lines, beats all four LLMs on 2 of 8 resumption tasks).
3. Methodology writeup. 1–2k word piece. The story is: "we spent 90 days fine-tuning to beat a benchmark, the benchmark turned out to be confounded, and the methodology to catch that is the actual contribution."
4. Update `docs/findings.md` F-05 with the round-4 wording and the MLX caveat (this commit).
5. Update README v0.2 section with the cleaner null-result framing (this commit).

This is a soft landing for a hard arc. Hugo wanted to ship a usable model; what we have is a benchmark, a tiny baseline, and a methodology that survived four rounds of public adversarial review. That's not nothing, even if it's not what we set out to make.
