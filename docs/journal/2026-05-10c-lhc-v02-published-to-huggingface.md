# 2026-05-10c · LHC v0.2 published to HuggingFace

**Status at end of session:** Path E artifact #1 shipped. `hugonogueira/lhc-v0.2` is live on HuggingFace, public, Apache-2.0, with all 24 tasks + 60 scorecards + audit results + both verdict artifacts + decontamination provenance + dataset card. Initial commit `fd9aa7f`. The benchmark is now citeable and downloadable independent of the GitHub repo.

## What we did

1. **Installed the HuggingFace CLI** as a project dependency. Added `huggingface_hub>=0.26` to `pyproject.toml` (the `[cli]` extra was removed in HF Hub 1.x — the CLI is now bundled in the base package and invoked as `hf`, not `huggingface-cli`). Logged in as `hugonogueira` via `hf auth login` with a fine-grained write token.

2. **Built a clean staging directory** at `/tmp/lhc-v0.2-hf-staging/` per the README's own publish hygiene rule (don't upload from a working directory that may contain `.env`, `models/`, `checkpoints/`, working scorecards, or briefs). 97 files total, 63MB:
   - 24 task YAMLs under `tasks/{state_recall,commitment,resumption}/`
   - 48 sweep scorecards under `results/sweep/`
   - 6 Ember diagnostic + 6 Qwen-local diagnostic scorecards under `results/diagnostic-*/`
   - 3 audit JSONs (G9, G12, combined)
   - Both verdict artifacts (`verdict-original-confounded.json` and `verdict-matched-inference.json`)
   - `deterministic-baseline.json`
   - `manifest.json`, `banned_overlap.json`, `AUTHORING.md`, `DECISION.md`
   - `README.md` (the dataset card), `LICENSE`, `.gitattributes`

   Verified no leaked API keys or sensitive content via grep before upload.

3. **Drafted the HF dataset card** (`README.md` at the staging root) with YAML frontmatter for HF tags + dataset viewer config, the round-4 wording as the headline, the matched-inference comparison table, the original confounded sweep table with explicit caveat, the layout, the methodology highlights, the MLX replication observation, the deterministic-baseline result, the decontamination provenance, the 4-round-review story, the BibTeX citation block, the about line.

4. **Created the empty repo**: `hf repo create hugonogueira/lhc-v0.2 --repo-type dataset` (default visibility public).

5. **Uploaded the staging directory**: `hf upload hugonogueira/lhc-v0.2 /tmp/lhc-v0.2-hf-staging --repo-type dataset --commit-message "Initial publish: LHC v0.2 — benchmark + scorecards + diagnostic + provenance"`. The CLI warned about large-folder uploads; it succeeded anyway in one shot. Commit `fd9aa7f`.

6. **Verified the upload** via the `huggingface_hub` Python API: 97 files on HF, all expected paths present (README, manifest, both verdicts, 24 task YAMLs, 48 sweep scorecards, 6 diagnostic per side).

7. **Updated the GitHub repo** to point at the HF dataset:
   - `README.md` — added an HF dataset badge under the title and a callout in the `## What's in this repo` summary.
   - `CITATION.cff` — added HF URL as the primary `url`, added `identifiers` section pointing at both HF and GitHub.

## Decisions

- **D-18.** Dataset is public, Apache-2.0, named `hugonogueira/lhc-v0.2`. When Slow Lit Labs incorporates and is publicly associable, the HF dataset can transfer to a `slowlitlabs/*` namespace via HuggingFace's built-in transfer flow (citations and downstream references redirect automatically).

- **D-19.** Scope of the published dataset matches what the round-5 reviewer audited: benchmark + scorecards + diagnostic + provenance + verdicts + audit. Not just the tasks. The methodology arc is what the round-5 reviewer cleared us to ship; cutting it down to just the tasks would weaken what the reviewer endorsed.

- **D-20.** The dataset card explicitly retracts the "Ember regresses" claim and uses the round-4 reviewer's required wording verbatim ("statistically indistinguishable from base Qwen3-8B under matched local inference"). The original 4-model leaderboard is included with the inference-config caveat clearly marked, not as the headline.

- **D-21.** The dataset card states the dataset "is NOT a leaderboard" / "is NOT a model release" / "is NOT a substitute for held-out product evaluation." This is to head off the most likely misreadings.

## What's next

Path E artifact #2 — **deterministic-baseline parser polished as a publishable standalone artifact.** Either:
- A small dedicated repo (`hugomn/lhc-resume-state-parser`) with the 100-line parser + a small README + benchmark results against LHC, or
- An HF Space that runs the parser interactively against a user-pasted resume payload.

Path E artifact #3 — **methodology writeup**, 1-2k words. The story is the four-round review arc: how methodology rigor produced an honest null result, what each review round caught, why the MLX replication observation matters for anyone benchmarking on Apple Silicon. Format TBD (essay, blog post, or HF Space write-up).

Order: parser first (more concrete, lower stakes), writeup second (the load-bearing piece, takes more careful drafting).

## Pointers

- HuggingFace dataset: https://huggingface.co/datasets/hugonogueira/lhc-v0.2
- Initial publish commit: `fd9aa7f` on the HF dataset
- GitHub commit referencing the HF link: pending in this session
