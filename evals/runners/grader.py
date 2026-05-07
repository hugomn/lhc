"""LHC grader — applies the 0–4 rubric to a single (task, response) pair.

The grader uses a strong reference model (Claude Sonnet by default) as a
judge, given the task's `expected_behavior` clause and the model's actual
response. Judge prompts are version-controlled to keep results reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass

from .client import Client, ModelConfig

# The judge prompt is intentionally verbose. Fidelity > brevity here —
# rubric drift is the single largest source of LHC score noise.
JUDGE_SYSTEM_PROMPT = """You are an evaluator scoring whether an autonomous agent
correctly handled a long-horizon coherence task.

You will receive:
  1. The task's expected behavior, written by a human author.
  2. The full response the agent produced.

Score on this rubric, returning ONLY the integer 0, 1, 2, 3, or 4:

  0 - The agent ignored or contradicted the original setup.
  1 - The agent partially recalled the setup but acted incorrectly.
  2 - The agent recalled the setup correctly but its reasoning was degraded.
  3 - The agent recalled and acted correctly.
  4 - The agent recalled and acted correctly AND proactively flagged the
      context gap or contradiction in its reasoning trace.

Return only the digit. No explanation, no whitespace, no markdown.
"""


@dataclass(frozen=True)
class GradeResult:
    score: int  # 0..4
    reasoning: str = ""


class Grader:
    def __init__(self, judge_config: ModelConfig) -> None:
        self._client = Client(judge_config)

    def grade(self, expected_behavior: str, agent_response: str) -> GradeResult:
        prompt = (
            f"EXPECTED BEHAVIOR:\n{expected_behavior}\n\n"
            f"AGENT RESPONSE:\n{agent_response}\n\n"
            f"SCORE:"
        )
        raw = self._client.chat(
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        ).strip()

        # Defensive: judges occasionally drift; clamp to valid range.
        try:
            score = int(raw[0])
            if score not in (0, 1, 2, 3, 4):
                raise ValueError
        except (ValueError, IndexError):
            score = 0  # fail closed — unparseable judge output is treated as failure

        return GradeResult(score=score, reasoning=raw)
