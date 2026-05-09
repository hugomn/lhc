"""Gap generator — produces synthetic intervening content for LHC tasks.

The gap is the whole point of LHC. Without it we are just measuring whether
a model can answer a question that comes immediately after its setup. With
it we are measuring whether the setup survives intervening noise.

Four gap modes are supported (v0.2):
  - "none"        — no gap at all. Tests pure capability with no distractor.
  - "placeholder" — single message containing the literal training-data
                    placeholder string. Tests whether the model has learned
                    to ignore that exact token sequence.
  - "neutral"     — lorem-ipsum-style filler. Tests attention distance with
                    no plausible task content for the model to latch onto.
  - "current"     — the original v0.1 gap: real-looking agent chatter from a
                    16-block pool. Tests behavior under distractor pressure.

Determinism: all modes are seeded with a stable hash of the task id (sha256),
not Python's process-salted hash(). Results are byte-identical across machines.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

GapMode = Literal["none", "placeholder", "neutral", "current"]
DEFAULT_GAP_MODE: GapMode = "current"

# The exact string used in synthetic training data to mark the gap. Eval-time
# "placeholder" mode injects this verbatim so we can test whether the model
# has learned to recognize / skip the literal token sequence.
TRAINING_PLACEHOLDER = "[~6,000 tokens of unrelated agent chatter elapses here]"

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
    mode: GapMode = "current"


# Lorem-ipsum-ish neutral filler. Each block is a multi-paragraph chunk of
# decorative prose with no task-shaped content for the model to latch onto.
# Used by gap_mode="neutral" to test attention distance without distractor
# pressure.
NEUTRAL_BLOCKS: list[dict[str, str]] = [
    {
        "role": "user",
        "content": (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer "
            "nec odio. Praesent libero. Sed cursus ante dapibus diam. Sed nisi. "
            "Nulla quis sem at nibh elementum imperdiet. Duis sagittis ipsum. "
            "Praesent mauris. Fusce nec tellus sed augue semper porta. Mauris "
            "massa. Vestibulum lacinia arcu eget nulla. Class aptent taciti "
            "sociosqu ad litora torquent per conubia nostra, per inceptos "
            "himenaeos. Curabitur sodales ligula in libero."
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Sed dignissim lacinia nunc. Curabitur tortor. Pellentesque nibh. "
            "Aenean quam. In scelerisque sem at dolor. Maecenas mattis. Sed "
            "convallis tristique sem. Proin ut ligula vel nunc egestas porttitor. "
            "Morbi lectus risus, iaculis vel, suscipit quis, luctus non, massa. "
            "Fusce ac turpis quis ligula lacinia aliquet. Mauris ipsum. Nulla "
            "metus metus, ullamcorper vel, tincidunt sed, euismod in, nibh."
        ),
    },
    {
        "role": "user",
        "content": (
            "Quisque volutpat condimentum velit. Class aptent taciti sociosqu "
            "ad litora torquent per conubia nostra, per inceptos himenaeos. Nam "
            "nec ante. Sed lacinia, urna non tincidunt mattis, tortor neque "
            "adipiscing diam, a cursus ipsum ante quis turpis. Nulla facilisi. "
            "Ut fringilla. Suspendisse potenti. Nunc feugiat mi a tellus "
            "consequat imperdiet."
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Vestibulum sapien. Proin quam. Etiam ultrices. Suspendisse in "
            "justo eu magna luctus suscipit. Sed lectus. Integer euismod lacus "
            "luctus magna. Quisque cursus, metus vitae pharetra auctor, sem "
            "massa mattis sem, at interdum magna augue eget diam. Vestibulum "
            "ante ipsum primis in faucibus orci luctus et ultrices posuere "
            "cubilia Curae; Morbi lacinia molestie dui."
        ),
    },
]


def _fill_from_pool(pool: list[dict[str, str]], target_chars: int, seed: int) -> tuple[list[dict[str, str]], int]:
    """Cycle through `pool` (shuffled by `seed`) until we hit `target_chars`.
    Trims trailing user messages so the gap never ends on an open question.
    Returns (messages, chars_consumed).
    """
    rng = random.Random(seed)
    shuffled = pool.copy()
    rng.shuffle(shuffled)
    out: list[dict[str, str]] = []
    chars = 0
    i = 0
    while chars < target_chars:
        block = shuffled[i % len(shuffled)]
        out.append({"role": block["role"], "content": block["content"]})
        chars += len(block["content"])
        i += 1
    while out and out[-1]["role"] == "user":
        chars -= len(out[-1]["content"])
        out.pop()
    return out, chars


def generate_gap(
    target_tokens: int,
    seed: int = 42,
    mode: GapMode = DEFAULT_GAP_MODE,
) -> GapResult:
    """Return a list of message dicts forming the inter-task gap.

    Deterministic given the same `seed` AND `mode`. Uses a 4-chars-per-token
    approximation for sizing — plenty good for gap sizing.

    Modes:
      - "none":        empty gap. `target_tokens` ignored.
      - "placeholder": single user message containing the literal training-
                       data placeholder string. `target_tokens` ignored.
      - "neutral":     lorem-ipsum-style filler from NEUTRAL_BLOCKS.
      - "current":     v0.1 behavior — chatter from NOISE_BLOCKS.
    """
    if mode == "none" or target_tokens <= 0:
        return GapResult(messages=[], estimated_tokens=0, mode=mode)

    if mode == "placeholder":
        msgs = [{"role": "user", "content": TRAINING_PLACEHOLDER}]
        return GapResult(
            messages=msgs,
            estimated_tokens=len(TRAINING_PLACEHOLDER) // 4,
            mode=mode,
        )

    target_chars = target_tokens * 4
    if mode == "neutral":
        pool = NEUTRAL_BLOCKS
    elif mode == "current":
        pool = NOISE_BLOCKS
    else:
        raise ValueError(f"unknown gap mode: {mode!r}")

    out, chars = _fill_from_pool(pool, target_chars, seed)
    return GapResult(messages=out, estimated_tokens=chars // 4, mode=mode)
