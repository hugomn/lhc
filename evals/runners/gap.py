"""Gap generator — produces synthetic intervening content for LHC tasks.

The gap is the whole point of LHC. Without it we are just measuring whether
a model can answer a question that comes immediately after its setup. With
it we are measuring whether the setup survives intervening noise.

For v0.1 we use a deterministic generator so results are reproducible:
seeded RNG, fixed templates, target token count via tiktoken estimation.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# Deterministic synthetic content. Each block is intentionally mundane —
# the noise should be plausibly part of an agent's working session, not
# obvious filler the model can pattern-match and ignore.
NOISE_BLOCKS: list[dict[str, str]] = [
    {
        "role": "user",
        "content": (
            "Quick aside: can you check if there are any open dependabot "
            "alerts on the infra repo? No need to act on them yet, just "
            "want to know how many."
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Checked: 7 open dependabot alerts on infra. 2 high (lodash, "
            "minimist transitive), 4 medium, 1 low. None on hot-path "
            "services. Want me to triage now or batch them?"
        ),
    },
    {
        "role": "user",
        "content": "Batch. Continue what you were doing.",
    },
    {
        "role": "assistant",
        "content": "Got it. Continuing.",
    },
    {
        "role": "user",
        "content": (
            "Different topic — the new hire onboarding doc mentions Notion "
            "but we moved to Linear last quarter. Open a PR fixing that."
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Opened PR #847 on the handbook repo. Replaced 'Notion' with "
            "'Linear' in 3 places, kept the screenshots flagged with a "
            "TODO since they need re-shooting. Awaiting review."
        ),
    },
    {
        "role": "user",
        "content": (
            "Another thing — what's our current AWS spend trajectory for "
            "the month? Just the headline number."
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Month-to-date: $14,820 across all accounts. On pace for "
            "$31,200 by month end, about 4% under last month. Bedrock "
            "and S3 are the biggest line items."
        ),
    },
    {
        "role": "user",
        "content": (
            "Run the linter on the auth package — I think we have some "
            "unused imports from the refactor last week."
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Linter found 11 issues in auth: 6 unused imports, 3 unused "
            "variables, 2 missing return type annotations. All trivially "
            "fixable. Should I open a cleanup PR or wait?"
        ),
    },
    {
        "role": "user",
        "content": "Open the PR. Small changes only, no behavior changes.",
    },
    {
        "role": "assistant",
        "content": "PR #312 opened on auth. 11 lint fixes, no behavior changes. CI green.",
    },
    {
        "role": "user",
        "content": (
            "The Slack integration for the daily digest — is it still "
            "posting at 9am or did the cron drift?"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Posting on time. Last 7 runs all between 09:00:02 and "
            "09:00:11 UTC. No drift detected."
        ),
    },
    {
        "role": "user",
        "content": (
            "Pull the open PR count from the eng org for me. Just the number."
        ),
    },
    {
        "role": "assistant",
        "content": (
            "23 open PRs across the eng org. 8 awaiting review, 11 "
            "awaiting changes, 4 in draft."
        ),
    },
]


@dataclass
class GapResult:
    messages: list[dict[str, str]]
    estimated_tokens: int


def generate_gap(target_tokens: int, seed: int = 42) -> GapResult:
    """Return a list of message dicts whose total estimated token count
    is close to `target_tokens`. Deterministic given the same seed.

    Uses a 4-chars-per-token approximation — plenty good for gap sizing,
    we are not optimizing context to the byte.
    """
    if target_tokens <= 0:
        return GapResult(messages=[], estimated_tokens=0)

    rng = random.Random(seed)
    out: list[dict[str, str]] = []
    chars_so_far = 0
    target_chars = target_tokens * 4

    # Cycle through the noise pool; randomize order per seed to keep things
    # plausible across multiple runs without breaking reproducibility.
    pool = NOISE_BLOCKS.copy()
    rng.shuffle(pool)
    i = 0

    while chars_so_far < target_chars:
        block = pool[i % len(pool)]
        out.append({"role": block["role"], "content": block["content"]})
        chars_so_far += len(block["content"])
        i += 1

    # Trim trailing user messages so the gap doesn't end on an open question
    # that an ambiguous probe could mistakenly attach to.
    while out and out[-1]["role"] == "user":
        chars_so_far -= len(out[-1]["content"])
        out.pop()

    return GapResult(messages=out, estimated_tokens=chars_so_far // 4)
