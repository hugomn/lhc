# Plan — superseded

This file used to hold the execution plan for **Ember v0.1** (May 2026). That plan produced Ember v0.1 and v0.1.5, but external review on 2026-05-08 + the LHC v0.2 sweep on 2026-05-09 showed that v0.1.5 underperforms its base model on a clean benchmark. **The v0.1.5 line is retired and v0.1 will not ship as planned.**

The original plan is preserved in git history (commit before this rewrite). The current state of the project lives in:

- [`README.md`](README.md) — what Ember is now and where things stand
- [`docs/findings.md`](docs/findings.md) — what we know today (newest first; F-05 is the v0.2 leaderboard)
- [`docs/journal/`](docs/journal/) — chronological methodology arc, including how we got here
  - [2026-05-08 — external review and decontamination](docs/journal/2026-05-08-external-review-and-decontamination.md)
  - [2026-05-09 — v0.2 sweep verdict, v0.1.5 stops here](docs/journal/2026-05-09-v02-sweep-verdict-ember-v015-stops-here.md)
- [`evals/v0.2/DECISION.md`](evals/v0.2/DECISION.md) — the pre-registered decision gates that produced today's verdict

## What's next

A new plan for **Ember v0.2** is being designed and externally reviewed before any further training. Until that plan is reviewer-blessed, no MLX training runs.

When the v0.2 plan is locked, it will land here (or at `PLAN-v0.2.md`). Until then, this file is a tombstone.
