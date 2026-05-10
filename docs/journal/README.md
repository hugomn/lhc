# Journal

Append-only chronological log of Ember work sessions. Each entry captures one session's worth of context — what we tried, what we learned, what we decided next — with enough detail that someone (including future-you) can reconstruct the path months later without re-deriving it.

## How to read

- Entries are filenames `YYYY-MM-DD-short-slug.md` and listed below newest-first.
- Each entry is **self-contained**: you should be able to grep for a topic, read one entry, and understand what happened in that session without reading the others.
- Entries are **never edited after the day**. If a later session changes our understanding, write a new entry that links back, don't rewrite the old one. The dead ends are part of the record.

## Where to look for what

- **What's true right now?** → [`../findings.md`](../findings.md) (living doc, edited in place).
- **What were the numbers in release N?** → [`../changelog.md`](../changelog.md) and [`../results.md`](../results.md).
- **How did we end up at the current understanding?** → this directory.
- **One-shot artifacts for external consumers** (e.g. review briefs, scratchpad plans) → kept at repo root with `REVIEW_*.md` naming and gitignored.

## Entry template

```markdown
# YYYY-MM-DD · short title

**Status at end of session:** one-liner.

## Context — where we were
What we believed when the session started.

## What we did
Chronological. Be specific (commands, file paths, outputs).

## What we learned
Bullets. Distinguish "verified fact" from "current hypothesis."

## Decisions
What changes as a result. Each decision: rationale + falsifiability gate.

## Open questions
Stuff still unresolved. Carry into the next session.

## Pointers
Commits, scorecards, files referenced.
```

## Index

- [`2026-05-10b-repo-rebrand-to-personal-namespace.md`](2026-05-10b-repo-rebrand-to-personal-namespace.md) — Repo transferred from `slowlitlabs/ember` to `hugomn/lhc` on GitHub. Front-of-house docs re-attributed to Hugo Nogueira; HF target paths shifted to `hugonogueira/*`. Journal history preserved verbatim per append-only convention.
- [`2026-05-10-mlx-replication-and-diagnostic-closure.md`](2026-05-10-mlx-replication-and-diagnostic-closure.md) — Two more rounds of external review. Yesterday's "Ember regresses" verdict rebuilt as "statistically indistinguishable from base under matched local inference; does not meet bar for release." Discovered MLX session-vs-restart replication issue. Path E green-lit.
- [`2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md`](2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md) — LHC v0.2 sweep ran (48 scorecards). Audit (G9 + G12) passed. Decision: Ember v0.1.5 underperforms base Qwen3-8B on a clean benchmark. v0.1.5 line formally retired. Engaging external reviewer for v0.2 plan.
- [`2026-05-08-external-review-and-decontamination.md`](2026-05-08-external-review-and-decontamination.md) — Path B (YaRN) abandoned after external review found benchmark contamination, hash-seed bug, train/eval gap mismatch. New plan: methodology fixes + LHC v0.2.
