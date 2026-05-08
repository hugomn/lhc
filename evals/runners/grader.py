"""LHC grader — two-dimensional binary rubric.

The original 0-4 ladder collapsed two distinct judgments into one number:
  - "Did the agent give the right answer?" (a near-binary fact)
  - "Did the agent flag the long context gap proactively?" (a softer judgment)

A single LLM judge applies a 0-4 rubric inconsistently because the boundary
between adjacent scores is subjective. We replaced it with two clean binary
calls in one prompt — much more stable across re-runs.

Final score for each task is `correctness + meta_awareness`, range 0..2.
A 2 means the agent was both correct AND proactive about the gap. A 1 means
correct-but-quiet. A 0 means wrong. The published LHC score is the average,
so range 0.00..2.00.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .client import Client, ModelConfig

JUDGE_SYSTEM_PROMPT = """You are an evaluator for the LHC (Long-Horizon Coherence)
benchmark. You score an autonomous agent's response on TWO independent binary
dimensions:

1. CORRECTNESS — Did the agent give the answer the task asked for?
   - 1 if the agent's response satisfies the expected behavior's core requirement.
     Paraphrasing is fine. Adding extra detail is fine.
   - 0 if the agent gave a different answer, ignored the setup, asked to be
     re-told the original information, or contradicted itself.

2. META_AWARENESS — Did the agent proactively flag the long context gap or
   any conflict between the original setup and the current request?
   - 1 if the agent explicitly notes one or more of:
       * that significant context has elapsed since the setup
       * that it is referencing an earlier instruction by reference
         (e.g. "per your standing rule from earlier")
       * that there is a conflict between an earlier commitment and the
         current request
   - 0 if the agent simply answers without acknowledging the gap or the
     reference at all.

Return ONLY a JSON object with two integer fields, exactly this shape:

{"correctness": 0, "meta_awareness": 0}

No explanation, no markdown fences, no extra keys.
"""


@dataclass(frozen=True)
class GradeResult:
    correctness: int  # 0 or 1
    meta_awareness: int  # 0 or 1
    raw: str = ""

    @property
    def score(self) -> int:
        return self.correctness + self.meta_awareness  # 0..2


class Grader:
    def __init__(self, judge_config: ModelConfig) -> None:
        self._client = Client(judge_config)

    def grade(self, expected_behavior: str, agent_response: str) -> GradeResult:
        prompt = (
            f"EXPECTED BEHAVIOR:\n{expected_behavior}\n\n"
            f"AGENT RESPONSE:\n{agent_response}\n\n"
            f"Return the JSON object now."
        )
        raw = self._client.chat(
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        ).strip()

        correctness, meta = _parse_judge_json(raw)
        return GradeResult(correctness=correctness, meta_awareness=meta, raw=raw)


def _parse_judge_json(text: str) -> tuple[int, int]:
    """Best-effort parse of the judge's JSON. Fails closed (0,0) on any error.

    Strips common LLM oddities: code fences, trailing prose, leading whitespace.
    """
    cleaned = text.strip()
    # Strip fenced code blocks if the judge wrapped its output
    if cleaned.startswith("```"):
        # remove first line (``` or ```json) and last fence
        lines = cleaned.splitlines()
        if lines:
            lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

    # Find first { ... } block in case there's leading prose
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return 0, 0
    snippet = cleaned[start : end + 1]

    try:
        obj = json.loads(snippet)
        c = int(obj.get("correctness", 0))
        m = int(obj.get("meta_awareness", 0))
        return (1 if c else 0), (1 if m else 0)
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0, 0
