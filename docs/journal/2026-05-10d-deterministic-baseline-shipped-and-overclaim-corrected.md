# 2026-05-10d · Deterministic baseline shipped + overclaim corrected

**Status at end of session:** Path E artifact #2 shipped. The deterministic resume-state parser is now a standalone Apache-2.0 repo at [hugomn/lhc-resume-state-parser](https://github.com/hugomn/lhc-resume-state-parser) with 9 passing tests, a CLI, an example task, and the published scorecard. While preparing it I caught a real factual overclaim that had been in the canonical LHC docs since 2026-05-09 and corrected it across 6 places (5 in the main repo + the HF dataset card). One Path E artifact left: the methodology writeup.

## What we did

1. **Extracted the parser into a standalone module.** `parser.py` is the same logic that lived inside `evals/v0.2/deterministic_baseline.py` lines 75–235, but with all harness imports stripped out. Pure stdlib + pyyaml. 220 lines including docs/comments; ~80 lines of load-bearing logic. Public API: `parse_task(task: dict) -> str`.

2. **Built a CLI** (`cli.py`) that takes a path to an LHC v0.2 task YAML and prints the parser's response. `--show-task` flag also prints the task setup + probe before the response. Smoke-tested against `resumption_v2_004` (the bundled example): output references SKU C-3308 from the warehouse tracker — correct.

3. **Wrote 9 unit tests** (`tests/test_parser.py`) covering:
   - `NEXT:` marker detection
   - `[NEXT]` bracket-tag detection
   - "Next planned action" label form
   - Decline path when no marker is present
   - Inconsistency detector positive case (`RECIPE-A` decision vs `RECIPE-B` next-action)
   - Inconsistency detector negative case (consistent state)
   - Inconsistency detector ignoring non-formula codes (`GCS-9`, `H-2204`)
   - End-to-end on the bundled `resumption_v2_004` example
   - End-to-end on the decline path with a synthetic task

   First inconsistency test failed because my fixture had inline section labels ("Decision today: ...") rather than the standalone-line section headers (`DECISION:` then content) the actual `resumption_v2_008` task uses. Fixed the fixture; all 9 pass now.

4. **Drafted the standalone README** with the "fine-tuning may be the wrong layer" framing.

5. **Caught a real factual overclaim while writing the comparative table.** Until now, the canonical LHC docs (README, results.md, findings.md, changelog.md, journal entry, HF dataset card) have all said variants of *"the parser beats every fine-tuned 8B model we tested"* on `resumption_v2_004` and `resumption_v2_008`. Verifying against the published scorecards:

   `resumption_v2_004` per-model means across 12 cells (4 gap modes × 3 trials):
   - **Parser: 2.00** (deterministic)
   - Llama-3.1-8B: 1.92
   - Ministral-8B-2512: 1.67
   - Qwen3-8B base: 1.50
   - Ember v0.1.5: 1.25

   `resumption_v2_008` per-model means:
   - **Parser: 2.00** (deterministic)
   - Ministral-8B-2512: 1.92
   - Qwen3-8B base: 1.50
   - Llama-3.1-8B: 1.17
   - Ember v0.1.5: 1.00

   The "beats every model" claim is wrong on means — Ministral and Llama have higher per-task means than the parser claimed to "beat." The defensible claim is *"the parser scores 2/2 deterministically; no LLM matches that mean (some cells hit 2/2, but with cross-trial variance)."* Subtle but real.

   This was missed by the round-5 reviewer's 8-blocker repo audit. Could have shipped to HF and been quoted in third-party comparisons before correction. Caught only because I was building the standalone repo's README and double-checked the table.

6. **Corrected the wording in 6 places:**
   - `README.md` (main LHC repo, two locations: header bullet list and headline result section)
   - `docs/results.md` (deterministic baseline section)
   - `docs/findings.md` F-05 (deterministic baseline reference)
   - `docs/changelog.md` (the v0.2 release entry that originally introduced the claim)
   - The new standalone repo's README at [hugomn/lhc-resume-state-parser](https://github.com/hugomn/lhc-resume-state-parser) (correct framing from initial commit, not a backfill)
   - The HF dataset card at [hugonogueira/lhc-v0.2](https://huggingface.co/datasets/hugonogueira/lhc-v0.2) (commit `8e05f30` re-uploaded the corrected README)

   The 2026-05-09 journal entry's H7 hypothesis says *"a deterministic parser beats every 8B model we tested"* and per the append-only convention I left it unedited. Anyone reading entries chronologically lands on this entry's correction; the H7 statement stays as the period-accurate hypothesis-as-it-was-written.

7. **Created the standalone GitHub repo** with `gh repo create hugomn/lhc-resume-state-parser --public`. Initial commit `86efd78`. Live at https://github.com/hugomn/lhc-resume-state-parser.

8. **Decided NOT to create a HF model entry.** HF "model" type implies the artifact IS a model; a regex parser shoehorned into `pipeline_tag: text-generation` would contradict the README's explicit "this is NOT a model" framing. Discoverability is via the LHC v0.2 HF dataset card link, which is the right entry point anyway.

9. **Cross-linked from the main LHC repo's README** to point at the standalone parser. (`hugomn/lhc/README.md` line 11 in the contents list.)

## What we learned

- **Round-5 audit didn't catch the mean overclaim.** That reviewer caught 8 release blockers and 4 usability items before the HF publish, all real. Missing this one isn't on them — they were auditing the docs against their internal model of correctness, not against the published scorecards. The check that caught it was *building a comparative table from raw data for a separate consumer*. Lesson: structured comparisons against a different audience surface different errors than holistic-correctness review.

- **The original scorecard was correct; the framing around it was sloppy.** The parser scores 2/2 on `_004` and `_008`; that's a real result. Calling it "beats every fine-tuned model" because *some cells* of those models scored less than 2/2 is the kind of phrasing slip that's easy to write and hard to catch by re-reading the same docs. Cross-verifying against the raw scorecard table (`per-model × per-task means`) is the only safe check.

- **The standalone repo is more honest than the bundled version was.** Forcing the parser into a format meant for outside consumers (with a comparison table standing on its own) made the overclaim visible. The same data was sitting in `deterministic-baseline.json` since 2026-05-09 and nobody had drawn the per-model mean comparison before today.

- **Determinism as a benchmark property is itself an interesting finding.** The corrected framing — *parser hits 2/2 deterministically; LLMs hit 2/2 sometimes* — is arguably more useful than the original. For production systems where reliability matters, "I get 2/2 every run" beats "I get 2/2 most runs" even if the mean comparison is ambiguous. This connects to the round-4 MLX replication finding (within-session vs across-session determinism) — both reinforce the broader point that benchmarking LLM-based systems requires variance reporting that benchmarking deterministic systems doesn't.

## Decisions

- **D-22.** The deterministic resume-state parser ships as a standalone Apache-2.0 repo at `hugomn/lhc-resume-state-parser`. Does not get a HF model entry. Discoverable via the LHC v0.2 HF dataset card link.

- **D-23.** Public framing for the parser is *"deterministic floor on what fine-tuning is worth"* — not *"beats every LLM."* The parser's value is its determinism + zero inference cost on structured state, not raw outperformance.

- **D-24.** Apply the corrected wording across all canonical docs in the same commit. Left the 2026-05-09 journal entry's H7 hypothesis unedited per append-only convention; this entry serves as the chronological correction.

## What's next

Path E artifact #3: **methodology writeup**, 1-2k words. The story now has an additional thread thanks to today's correction:

- Round 1 caught contamination
- Round 2 caught the inference-config asymmetry
- Round 3 caught the symmetry nuisance that surfaced MLX session/restart non-determinism
- Round 4 set the final wording
- Round 5 caught 8 blockers in repo audit
- And then: the standalone-repo extraction surfaced an overclaim sitting in canonical docs that 5 review rounds had not flagged

Each layer of methodology rigor catches different things. The writeup is the load-bearing piece for whatever credibility this body of work has externally.

## Pointers

- Standalone repo: https://github.com/hugomn/lhc-resume-state-parser
- Initial commit: `86efd78`
- HF dataset card correction: commit `8e05f30` on `hugonogueira/lhc-v0.2`
- Main LHC repo correction: pending in this session's commit
