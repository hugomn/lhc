# 2026-05-10b · Repo rebrand to personal namespace

**Status at end of session:** Repo transferred from `slowlitlabs/ember` to `hugonogueira/lhc` on GitHub. Front-of-house docs (README, manifesto, citation, package metadata) re-attributed to Hugo Nogueira. HuggingFace target paths shifted from `slowlitlabs/*` to `hugonogueira/*`. Journal history is preserved verbatim per the append-only convention; this entry records the rebrand decision and what changed.

## Context — where we were

By end of [`2026-05-10`](2026-05-10-mlx-replication-and-diagnostic-closure.md), the v0.1.5 line was retired with a clean null-result framing endorsed by external review round 4. Path E (ship benchmark + parser + methodology writeup) was the immediate next move.

Before kicking off the HuggingFace dataset upload, two adjacent constraints surfaced that needed resolution:

1. **Slow Lit Labs is not yet incorporated.** Publishing under `slowlitlabs/*` on HuggingFace and citing a not-yet-real lab in `CITATION.cff` reads as either aspirational (mild credibility hit) or evasive (worse hit if a careful reader notices the org doesn't exist). The pre-registered methodology arc loses force when the entity attribution is ambiguous.
2. **Disclosure constraint with Complyance.** Author cannot publicly associate the Clayer name (or by extension a Slow Lit Labs effort that hosts Clayer) with personal work until certain disclosures land with Complyance investors. Personal-name attribution avoids creating a paper trail that complicates that conversation.

## What we did

1. **Decided to publish under personal namespace for now.** Specifically: `github.com/hugonogueira/lhc` (note: HF profile is `hugonogueira`; GitHub username is `hugomn`) and `huggingface.co/hugonogueira/*`. When Slow Lit Labs incorporates, both can transfer back via GitHub's built-in transfer flow + HuggingFace dataset/model transfer, which preserve history, redirects, and citations.

2. **Considered three repo-shape options:**
   - **(A)** Rename in place: `slowlitlabs/ember` → `hugonogueira/lhc`. One repo, one history, redirects from old URL.
   - **(B)** Split: keep `ember` (training pipeline) and extract `lhc` (benchmark only) as a separate repo.
   - **(C)** Fork. Rejected — forks signal "derivative of someone else's work," wrong shape since I own the source.

   **Picked (A).** The training-pipeline code is part of the contribution because *the story of the v0.1.5 fine-tune that didn't beat its base* is the load-bearing example for the methodology writeup. Removing the training side would weaken the story. Naming the repo `lhc` instead of `ember` puts the actual contribution in the URL.

3. **Considered whether to rewrite journal history** to erase Slow Lit Labs from earlier entries. **Decided against.** The journal's `README.md` opens with "Entries are never edited after the day. If a later session changes our understanding, write a new entry that links back, don't rewrite the old one. The dead ends are part of the record." That convention is the credibility signal. Editing the journal to retroactively scrub a name would break it for a marginal cosmetic gain — and `git log` would still show the original commits on `slowlitlabs/ember`. The clean read for newcomers is achieved by reframing Slow Lit Labs in *current-tense, user-facing* docs (README, manifesto, citation, package metadata) as "a working name for a future research effort." Earlier journal entries stand verbatim.

4. **Updated current-tense docs to personal attribution:**
   - **`README.md`** — rewritten with contribution-first framing. Header is now "LHC — long-horizon coherence" with a tagline about the benchmark. Removed the "patient fire / Slow Lit Labs" subhead. Added a short About section noting solo authorship and that the work is the seed for an eventual Slow Lit Labs effort.
   - **`docs/manifesto.md`** — reframed from "Slow Lit Labs is built for endurance" to a personal manifesto signed Hugo Nogueira, with a footer noting the future-lab destination.
   - **`CITATION.cff`** — author changed from "Hugo Marques, affiliation: Slow Lit Labs" to "Hugo Nogueira, hugomn@gmail.com" (no org affiliation). Title shifted from "Ember and the LHC Benchmark" to "LHC — Long-Horizon Coherence Benchmark" since the benchmark is the foreground contribution.
   - **`pyproject.toml`** — package renamed `ember` → `lhc`. Author re-attributed. URLs point at `github.com/hugonogueira/lhc`.
   - **`evals/v0.2/DECISION.md`** + **`evals/v0.2/analyze.py`** + **`inference/README.md`** — `slowlitlabs/ember-v0.1` HF paths updated to `hugonogueira/ember-v0.1`. These are forward-looking references to a model that didn't ship; harmless cleanup.
   - **`evals/tasks/state_recall/state_recall_004.yaml`** — internal-fictional email `enterprise-team@slowlit.internal` changed to `enterprise-team@example.internal`. Task is LHC v0.1 (historical) and the change doesn't affect the task's substance.
   - **`docs/changelog.md`** — added a 2026-05-10 rename entry under the Renames section, alongside the existing 2026-05-08 Cinder Labs → Slow Lit Labs entry.

5. **Updated git remote** locally: `origin` now points at `git@github.com:hugomn/lhc.git`.

6. **Did NOT touch:**
   - The two earlier journal entries (`2026-05-08` and `2026-05-09`) — append-only convention.
   - The 2026-05-10 entry — also append-only (and its forward-looking "ship to `slowlitlabs/lhc-v0.2`" reference is now historical context, accurate to the moment it was written).
   - The 2026-05-08 changelog rename entry (Cinder Labs → Slow Lit Labs) — historical record.
   - The published scorecards or any audit-trail data.

## What we learned

- **Append-only conventions earn their keep at moments like this.** The temptation to rewrite the journal to make the front impression cleaner was real. Resisting it preserves the credibility signal that took four review rounds to build. Anyone who reads through to the journal and sees a name change between entries gets a more honest picture than they would from a sanitized history.

- **Front-of-house vs. archive is the right split.** Newcomers see clean personal attribution in README, manifesto, citation, and package metadata. Anyone investigating the methodology arc reads the journal and sees the actual sequence of decisions including the entity-name change. Both audiences get what they need.

- **GitHub repo transfers are essentially free.** ~30 seconds in the UI, all commits/branches/issues/PRs preserved, redirects from old URLs work indefinitely. This means the rebrand decision is fully reversible — when Slow Lit Labs incorporates, the same transfer flow moves everything back in one click.

## Decisions

- **D-15.** Repo lives at `github.com/hugomn/lhc` until Slow Lit Labs incorporates and is in a position to be publicly associated with this work. HuggingFace artifacts go under `hugonogueira/*` for the same period.

- **D-16.** Journal append-only convention applies to the rebrand itself: this entry records the change; earlier entries are not retroactively edited. Anyone reading entry-by-entry sees the entity-name shift with this entry as its explanation.

- **D-17.** Future writing voice in the manifesto and README is first-person solo, with Slow Lit Labs framed as "a working name for an eventual research lab." Drops the "patient fire / Slow Lit Labs" branding from the front matter; preserves it as a footer note.

## What's next (Path E proper)

Unchanged from the [2026-05-10 entry](2026-05-10-mlx-replication-and-diagnostic-closure.md) — Path E artifacts:

1. Push the LHC v0.2 task suite to HuggingFace as `hugonogueira/lhc-v0.2`.
2. Polish the deterministic-baseline parser to a publishable standalone artifact.
3. Methodology writeup, 1–2k words.

The rebrand changes the destination URL, not the work to be done.
