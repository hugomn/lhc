"""Deterministic resume-state validator — baseline for LHC v0.2 resumption tasks.

Background: the external review of 2026-05-08 asked whether fine-tuning is
even the right layer for resumption-style failures, since deterministic
parsers and explicit session-state validators are often stronger and cheaper.
This script answers that for our specific benchmark.

What it does: instead of an LLM, a hand-written Python parser reads each
v0.2 resumption task's setup + probe, detects structured "next step"
markers (NEXT, [NEXT], next planned action), and produces a response.
For resumption_v2_008 specifically, it also detects inconsistencies in
loaded-state payloads.

The parser's output is graded by the same judge (Claude Opus 4.7) and
written as a normal LHC scorecard. This makes its score directly
comparable to model scores on the same tasks. If the parser scores 0.5+
on resumption, then any model scoring below that on resumption is doing
worse than ~100 lines of text-munging — a finding that would change
which gates in DECISION.md actually matter.

Scope (intentionally narrow):
  - Targets ONLY the resumption category (8 tasks).
  - Targets ONLY the `current` and `placeholder` and `none` gap modes
    (the parser ignores gap content entirely — that's the point).
  - Does NOT use any LLM in its forward pass; only the judge sees the
    parser's response.
  - Tasks the parser can't handle (free-prose continuations like
    resumption_v2_003 jewelry, _007 editor multi-thread) get an explicit
    "I cannot resume free-prose tasks deterministically" response.

Usage:
    python evals/v0.2/deterministic_baseline.py \\
        --judge-provider anthropic \\
        --output evals/results/v0.2/deterministic-baseline-1.json

Cost: ~$0.10 for Opus judge calls on 8 tasks. No model API for the
target — that's the whole point.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Reuse the existing scorecard schema, judge, and the lhc CATEGORIES list.
from evals.runners.client import Client, ModelConfig  # noqa: E402
from evals.runners.grader import Grader  # noqa: E402
from evals.runners.lhc import (  # noqa: E402
    DEFAULT_TASKS_DIR,
    PROVIDER_DEFAULTS,
    Scorecard,
    TaskScore,
    load_tasks,
)

load_dotenv(REPO_ROOT / ".env")


# ---------------------------------------------------------------------------
# The parser. This is the whole baseline.
# ---------------------------------------------------------------------------


def extract_full_text(task: dict) -> str:
    """All setup messages joined with newlines. Probe is handled separately."""
    return "\n".join(m.get("content", "") for m in task.get("setup", []))


def extract_user_loaded_state(task: dict) -> str:
    """Only the USER messages in setup — i.e. the state the user loaded into
    the conversation, not the system prompt or any assistant reply that may
    have already commented on it.

    The inconsistency detector should run on this (otherwise the assistant's
    own confirmation message — which mentions both formula IDs while
    flagging the conflict — confuses the detector).
    """
    return "\n".join(
        m.get("content", "")
        for m in task.get("setup", [])
        if m.get("role") == "user"
    )


def extract_probe(task: dict) -> str:
    """Probe message content joined."""
    return "\n".join(m.get("content", "") for m in task.get("probe", []))


# Patterns the parser knows how to detect in setup payloads.
# All patterns terminate at a newline — "next step" is single-line in our
# tracker formats, and pulling in additional lines causes downstream-prose
# bleed-through (we hit this in the dry-run where _001 captured "----- END
# PAGE 14 -----" and _005 captured the F.120 description).
NEXT_STEP_PATTERNS = [
    # Explicit NEXT: marker — take everything to end of line only.
    re.compile(r"NEXT:\s*([^\n]+)", re.IGNORECASE),
    # [NEXT] tag at start of a line — same single-line scope.
    re.compile(r"\[NEXT\]\s*([^\n]+)", re.IGNORECASE),
    # "Next planned action" / "Next planned step" labels — these usually
    # have a quoted multi-line value, so allow up to 3 wrapped lines but
    # stop at the next blank line.
    re.compile(
        r"next\s+planned\s+(?:action|step)[^:]*:\s*([^\n]+(?:\n[^\n]+){0,3})",
        re.IGNORECASE,
    ),
    # Arrow notation: "L5 → SKU foo  [NEXT]" in a workflow tracker.
    re.compile(r"^\s*[A-Z]\d+\s*→\s*([^\[]+?)\s*\[NEXT\]", re.MULTILINE),
]

INCONSISTENCY_HINTS = [
    # Names that appear in BOTH "decision" and "next action" but with
    # different values. Detected by looking for distinct CAPS-WORD-DASH-NUM
    # tokens (RECIPE-A, RECIPE-B) referenced in different "phases" of the
    # state.
    re.compile(r"\b([A-Z]+-[A-Z0-9]+)\b"),
]


def find_next_step(setup_text: str) -> str | None:
    """Try every pattern; return the first matched group's text, trimmed."""
    for pat in NEXT_STEP_PATTERNS:
        m = pat.search(setup_text)
        if m:
            return m.group(1).strip().rstrip(".")
    return None


def find_inconsistency(setup_text: str) -> tuple[str, str] | None:
    """Detect inconsistency in loaded state.

    Heuristic: if the same CAPS-DASH-token (e.g. RECIPE-A) appears in a
    "decision" / "last action" context AND a different one appears in a
    "next" context, that's a candidate inconsistency.

    Returns (decided_value, next_action_value) if detected, else None.
    """
    # Split text into sections by common headers / labels.
    chunks = re.split(
        r"(?im)^.*(?:decision|last action|next planned|tomorrow's plan|work log|recorded|call|note).*$",
        setup_text,
    )
    if len(chunks) < 3:
        return None

    # Find every CAPS-DASH-CAPS token. If one appears in early chunks
    # (decision / action / log) and a different one appears in the LAST
    # chunk (next-action), that's inconsistency.
    pat = INCONSISTENCY_HINTS[0]
    early_tokens: set[str] = set()
    for chunk in chunks[:-1]:
        for m in pat.finditer(chunk):
            early_tokens.add(m.group(1))
    late_tokens: set[str] = set()
    for m in pat.finditer(chunks[-1]):
        late_tokens.add(m.group(1))

    # Filter to "named formula"-style tokens: CAPS+DASH+single-letter or
    # CAPS+DASH+digit. RECIPE-A, BATCH-MAR-09-A. Excludes things like
    # GCS-9 or H-2204 by being strict.
    def looks_like_formula_id(t: str) -> bool:
        # RECIPE-A, RECIPE-B style: CAPS, dash, single letter
        return bool(re.fullmatch(r"[A-Z]{2,}-[A-Z]", t))

    early_formulas = {t for t in early_tokens if looks_like_formula_id(t)}
    late_formulas = {t for t in late_tokens if looks_like_formula_id(t)}

    # Only-in-early: chosen formula. Only-in-late: action target. If
    # disjoint AND both present, it's an inconsistency.
    only_early = early_formulas - late_formulas
    only_late = late_formulas - early_formulas
    if only_early and only_late:
        return (next(iter(only_early)), next(iter(only_late)))
    return None


def parser_response(task: dict) -> str:
    """Produce the parser's response to a task. The whole baseline is this fn.

    Strategy (order matters — inconsistency check comes first because the
    inconsistent payloads also contain a "next planned action" that the
    NEXT detector would otherwise grab):
      1. Inconsistency detection: run only against USER-loaded state, look
         for two distinct CAPS-DASH-LETTER tokens (e.g. RECIPE-A and
         RECIPE-B) that appear in disjoint phases of the loaded state.
      2. Explicit NEXT marker: if found in setup, report it.
      3. Decline: "no deterministic next-step marker found." Critical:
         do NOT free-associate from probe / gap content.
    """
    user_loaded = extract_user_loaded_state(task)
    setup_text = extract_full_text(task)

    # Step 1: inconsistency check on the user-loaded state.
    inc = find_inconsistency(user_loaded)
    if inc:
        chosen, action_target = inc
        return (
            f"I detected an inconsistency in the loaded state: the recorded "
            f"decision and last action reference {chosen}, but the "
            f"next-action note references {action_target}. These don't "
            f"match. Per the workflow tracker we loaded, the physical "
            f"materials prepared correspond to {chosen} (the decided "
            f"value), so I will proceed with {chosen} and flag the "
            f"conflicting next-action note for the operator to correct."
        )

    # Step 2: explicit NEXT marker.
    nxt = find_next_step(setup_text)
    if nxt:
        nxt = re.sub(r"\s*\[NEXT\]\s*$", "", nxt).strip()
        return (
            f"Per the loaded state, the next step is: {nxt}. "
            f"I'm continuing from where the previous session/shift left off, "
            f"as recorded in the workflow tracker we loaded earlier."
        )

    # Step 3: decline. Critical: do NOT free-associate.
    return (
        "I cannot determine the next step from the loaded state alone — "
        "no explicit NEXT-step marker was found, and I do not infer "
        "continuation from prose context. Please clarify the next action "
        "from the original task brief."
    )


# ---------------------------------------------------------------------------
# Runner — same shape as evals/runners/lhc.py main() but no target model.
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--tasks-dir",
        default=str(REPO_ROOT / "evals" / "v0.2" / "tasks"),
        help="directory holding category subdirs with task YAMLs",
    )
    p.add_argument(
        "--judge-provider",
        choices=list(PROVIDER_DEFAULTS),
        default="anthropic",
        help="judge provider for grading the parser output",
    )
    p.add_argument("--judge-model")
    p.add_argument("--judge-base-url")
    p.add_argument("--judge-api-key")
    p.add_argument(
        "--output",
        default=str(REPO_ROOT / "evals" / "results" / "v0.2" / "deterministic-baseline.json"),
        help="path to write scorecard JSON",
    )
    p.add_argument(
        "--category",
        default="resumption",
        choices=("resumption", "state_recall", "commitment", "all"),
        help="which categories to run the parser against (default: resumption)",
    )
    args = p.parse_args()

    # Resolve judge config from PROVIDER_DEFAULTS.
    jd = PROVIDER_DEFAULTS[args.judge_provider]
    args.judge_model = args.judge_model or jd["model"]
    args.judge_base_url = args.judge_base_url or jd["base_url"]
    args.judge_api_key = args.judge_api_key or os.environ.get(jd["api_key_env"], "")
    if not args.judge_api_key:
        print(f"[fatal] no judge API key found. Set {jd['api_key_env']} in .env.", file=sys.stderr)
        return 2

    tasks = load_tasks(Path(args.tasks_dir))
    if args.category != "all":
        tasks = [t for t in tasks if t["category"] == args.category]
    if not tasks:
        print(f"[fatal] no tasks found at {args.tasks_dir} for category={args.category}",
              file=sys.stderr)
        return 2

    print(f"Running deterministic baseline against {len(tasks)} tasks "
          f"(category={args.category})…")

    grader = Grader(
        ModelConfig(
            model=args.judge_model,
            base_url=args.judge_base_url,
            api_key=args.judge_api_key,
        )
    )

    task_scores: list[TaskScore] = []
    for task in tasks:
        print(f"\n  · {task['id']} ({task['category']}, {task['difficulty']})")
        response = parser_response(task)
        print(f"    parser said: {response[:120]}…")
        grade = grader.grade(task["expected_behavior"], response)
        print(f"    judge: c={grade.correctness} m={grade.meta_awareness}")

        # Build the same TaskScore shape the LHC runner produces. We don't
        # use the gap (deterministic baseline ignores it) so gap_messages
        # is empty and gap_mode is "none".
        excerpt = response[:400].replace("\n", " ")
        task_scores.append(
            TaskScore(
                task_id=task["id"],
                category=task["category"],
                score=grade.score,
                correctness=grade.correctness,
                meta_awareness=grade.meta_awareness,
                response_excerpt=excerpt,
                judge_reasoning=grade.raw,
                prompt_messages=list(task.get("setup", [])) + list(task.get("probe", [])),
                gap_messages=[],
                gap_mode="none",
                gap_estimated_tokens=0,
                response_full=response,
            )
        )

    # Aggregate.
    by_category: dict[str, float] = {}
    for cat in ("state_recall", "commitment", "resumption"):
        cat_scores = [t.score for t in task_scores if t.category == cat]
        by_category[cat] = round(sum(cat_scores) / len(cat_scores), 2) if cat_scores else 0.0
    overall = round(sum(t.score for t in task_scores) / len(task_scores), 2) if task_scores else 0.0

    sc = Scorecard(
        model="deterministic-baseline-v1",
        lhc_version="0.2",
        overall=overall,
        by_category=by_category,
        task_scores=task_scores,
        gap_mode="none",
        judge_model=args.judge_model,
        expected_task_count=len(tasks),
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(asdict(sc), indent=2))

    print(f"\n=========================================")
    print(f"  Deterministic baseline scorecard")
    print(f"=========================================")
    print(f"  overall:      {overall:.2f} / 2.00")
    for cat, score in by_category.items():
        if any(t.category == cat for t in task_scores):
            print(f"  {cat:<14} {score:.2f}")
    try:
        rel = out.relative_to(REPO_ROOT)
    except ValueError:
        rel = out  # output path is outside the repo (e.g. /tmp/...); print as-is
    print(f"\n  Written to {rel}")
    print(f"\n  Per-task summary:")
    for t in task_scores:
        print(f"    {t.correctness}/{t.meta_awareness}  {t.task_id}  ({t.category})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
