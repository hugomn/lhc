# 2026-05-12 · v0.3 framing locked after 3 reviewer rounds

**Status at end of session:** v0.3 cycle plan locked. DECISION-v0.3.md, draft model card, and draft dataset card sit in `docs/v0.3/`. Three rounds of external review today closed four release blockers and reframed the thesis. Ready to commit drafts and kick off Week 0 once Hugo signs off.

## Context — where we were

v0.2 cycle closed 2026-05-10 with three artifacts shipped (HF dataset, standalone parser repo, hugo.im writeup in EN + PT). The cycle was deliberately framed as v0.2-closeout, with v0.3 framing deferred to the next session.

Hugo opened v0.3 today (across 2026-05-11 + 2026-05-12) with two stated goals: (a) v0.3 should aim higher than "ship another artifact" — first steps toward something that could one day compete with frontier labs; (b) the realistic budget is up to €2000 EUR if outcomes are extraordinary, with a strong preference for shipping a usable artifact rather than a pure research paper.

## What we did

1. **Initial framing — "harness > scale" thesis.** Claude proposed v0.3 as a research bet on "long-horizon coherence in agent systems is bottlenecked by harness design, not model capability." Three POCs (frontier API ceiling check, harness ablation, small-model + good-harness vs 8B + bad-harness). Distribution: ~50% credible preprint, ~30% surprising-result preprint, ~15% kill, ~5% catalyst event.

2. **Round 1 of external review (reviewer).** Reviewer flagged the thesis as already scooped — Meta-Harness, Natural-Language Agent Harnesses, and Externalization in LLM Agents papers from 2025-2026 all make versions of the "harness matters" claim. Reframed thesis to the narrower wedge: **state-interface failures under delayed/distractor pressure**. Reviewer also defined the H0–H4 ablation ladder, the kill conditions, and named "State Protocols, Not Just Models" as the title direction.

3. **Hugo flag: usable-model orientation.** Hugo raised that the protocol-ablation-only outcome lacks an artifact people download and use. Asked for concrete usable-model bets reachable from €2000 + M5 Pro. Three bets evaluated (A: specialist agent-state model, B: latency-optimized chat, C: domain-specific chat). Bet A converged with reviewer's plan via a conditional Phase 2: train a small specialist only if Phase 1 ablation surfaces a model-shaped residual gap.

4. **Round 2 of external review.** Reviewer accepted the two-phase shape but caught two material errors in the Phase 2 wording:
   - "Train on whichever harness condition produces the largest gap" would have leaked H4/oracle answers into training data. Corrected to train only on non-oracle conditions, with H4 excluded from training data.
   - Renamed framing from "State Protocols" to **"The Agent State Handoff Problem"** — more punchy, more ownable as a category, more product-relevant.
   - Tightened training gates (T1–T4) and ship gates (S1–S5) to verbatim reviewer specs.
   - Added explicit kill conditions including "if H4/oracle is the only condition that helps, no Phase 2."

5. **Concrete-use-case validation.** Claude drafted two scenarios (Clayer procurement-compliance multi-day resume; Cursor-style coding agent context compaction) to make the abstract "specialist handoff model" tangible. Hugo confirmed the procurement-compliance scenario resembles real Clayer workflows. Internally validated, but **kept out of all published framing** per Hugo's call — v0.3 is independent research, Clayer is downstream private use.

6. **Week 0 drafts written.** DECISION-v0.3.md, draft-model-card.md, draft-dataset-card.md created in `docs/v0.3/`. Plus REVIEW_BRIEF_V03_PLAN.md bundling them for the final pre-kickoff review.

7. **Round 3 of external review.** Reviewer flagged four blockers in the drafts:
   - **Held-out leakage risk:** DECISION had held-out tasks in Phase 1 sweep, then Phase 2 trained on Phase 1 traces — contradiction with "no held-out tuning." Fixed: training data explicitly excludes held-out task traces, enforced by pre-training leakage check run twice.
   - **Week 1 kill underpowered:** 2 tasks × 4 modes was too small for a hard ceiling fork. Fixed: Week 1 is now billing pilot only, no capability kill. Frontier ceiling (if observed post-sweep) is a framing change, not a K-gate.
   - **K2 wrong:** "harness explains less variance than task_id" disqualifies real evals, where task_id naturally dominates. Replaced with paired robustness: best Hx − H0 delta positive on ≥60% of tasks AND ≥2/3 categories AND CI lower bound > 0.
   - **Scorecard terminology:** I had double-counted "2160 scorecards" when v0.2 convention is one scorecard per (model × harness × gap × trial) cell containing all tasks. Corrected to 252 scorecards / 9072 task-trials at minimum panel.
   
   Plus four secondary fixes:
   - Removed legal/medical from model card use cases (too high-stakes without domain eval).
   - Added precise Phase 2 comparison: same-size base receives same JSON-schema instruction, no scaffolding.
   - Added H1c/H2c length/recency controls to rule out "relevant state moved near probe" confound.
   - Added I1–I5 anti-isomorphism checklist for held-out task authoring with required per-task isomorphism notes.
   
   Reviewer also recommended one framing sentence tying v0.3 to the Thinking Machines "interaction models" essay — v0.3 targets the handoff layer between interactive front-end and slower background work. Added verbatim to DECISION §1.

8. **Blockers fixed in place.** All four blockers and four secondary fixes applied to DECISION-v0.3.md, draft-model-card.md, draft-dataset-card.md.

## What we learned

- **External review still catches things at round 3 of the same day.** Three reviewer passes on v0.3, four blockers caught in round 3 alone after rounds 1 and 2 had reshaped the plan. Same pattern as v0.2 (six rounds, round 6 caught factual errors in the writeup). **The discipline holds: pre-registration without external review is just self-confirmation.**

- **The "scooped thesis" risk was real and I hadn't checked.** I framed "harness > scale" as contrarian without surveying recent agent-harness literature. Reviewer named three specific 2025-2026 papers making versions of the claim. Lesson: before proposing a contrarian thesis, do at least one round of literature check; better, send the thesis to the reviewer specifically to check for scoop.

- **Held-out leakage almost made it into the final doc.** The contradiction was subtle: held-out tasks were in Phase 1 sweep (correct — needed for K-gate evaluation), and Phase 2 training data was "curated from Phase 1 traces" (also reasonable phrasing). The combination silently allowed held-out traces into training data. Pre-committed leakage checks (run twice, both logged) are the structural fix.

- **Task_id-dominates-variance is not a benchmark failure.** I had written K2 to fire when task_id explains more variance than harness — that was wrong; that's the modal state of real evaluations. The right integrity check is **paired robustness** across tasks: does the harness effect appear on most tasks, across categories, with a CI that doesn't cross 0? "Sparse harness wins" is the failure mode, not "task variance dominates."

- **Hugo wants the model. The reviewer wants the gates. The right answer is both.** v0.3 ships either way — Phase 1 artifacts always land. Phase 2 model lands only if it earns it. This is the discipline structure that v0.2 demonstrated and v0.3 inherits.

## Decisions

- **D-28.** v0.3 thesis is **"The Agent State Handoff Problem"** — long-horizon coherence failures are often state-interface failures. Phase 1 protocol ablation (always runs) + Phase 2 conditional specialist model. Locked.

- **D-29.** Phase 2 training data **excludes held-out task traces under all conditions**, enforced by pre-training leakage check run twice. H4/oracle traces also excluded. Both rules pre-registered, both logged.

- **D-30.** Held-out tasks (12 fresh) authored by Hugo personally, weeks 3–4 of v0.3 cycle, blind to Phase 1 sweep results. Each task must pass the I1–I5 anti-isomorphism checklist with a written isomorphism note committed before sweep. Sole-authorship constraint accepted by Hugo; calendar time pre-budgeted.

- **D-31.** Clayer relevance is internal validation only. v0.3 public framing makes no mention of Clayer. The internal use case (procurement-compliance multi-day resume) is documented in this journal and in memory, not in DECISION-v0.3.md or the cards.

- **D-32.** Budget cap €2000 hard, expected spend €100–500. Pause and re-evaluate if projected spend exceeds €1000. POC-1 (Week 1) is billing pilot only — no capability kill from Week 1 evidence alone.

- **D-33.** Length/recency controls (H1c, H2c) are mandatory for any T-gate claim involving H1 or H2. A non-oracle condition counts toward T1 only if Hx − Hxc ≥ +0.10 with CI not crossing 0.

- **D-34.** K2 reframed: paired robustness across tasks (≥60% positive paired deltas, ≥2/3 categories, CI lower bound > 0 on overall) instead of variance-attribution against task_id.

## Open questions

- **OQ-15:** Final pick of the small base model for Phase 2 (Qwen3-1.7B vs Llama 3.2-3B vs other). Decide end of Week 1.
- **OQ-16:** Should the deterministic parser for T3 be the v0.2 parser or a v0.3 update handling H1/H2/H3 input format? Decide while building H0–H4.
- **OQ-17:** Deterministic recipe converting Phase 1 traces (non-oracle, non-held-out) into Phase 2 training data without leakage. Lock end of Week 2.
- **OQ-18:** If Phase 1 reveals a clear winning protocol but the small specialist fails ship gates, is the right move to retry with a 3-7B base? Out of scope for v0.3; carry to v0.4.
- **OQ-19:** The H1c/H2c controls add 2/5 = 40% more compute to Phase 1. Is the panel size right or should we reduce trials from 3 to 2 to fit budget? Decide after Week 1 billing pilot.

## Pointers

- DECISION: [`docs/v0.3/DECISION-v0.3.md`](../v0.3/DECISION-v0.3.md)
- Draft model card: [`docs/v0.3/draft-model-card.md`](../v0.3/draft-model-card.md)
- Draft dataset card: [`docs/v0.3/draft-dataset-card.md`](../v0.3/draft-dataset-card.md)
- Reviewer brief: [`REVIEW_BRIEF_V03_PLAN.md`](../../REVIEW_BRIEF_V03_PLAN.md)
- v0.2 cycle close: [`2026-05-10e-path-e-shipped-writeup-and-cycle-closed.md`](2026-05-10e-path-e-shipped-writeup-and-cycle-closed.md)
- External framing reference: Thinking Machines, *Interaction Models* (2025).
