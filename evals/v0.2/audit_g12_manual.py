"""G12 — manual audit interactive script.

Per DECISION.md §5: sample 10% of task-trials uniformly across (model,
gap_mode), read the full prompt + response + judge reasoning, hand-rate.
If ≥ 5% of audited labels are *materially wrong* in a direction that would
flip a per-task score, the judge or rubric is too unreliable.

This script:
  1. Samples N task-trials (default 12, slightly above the 9 floor)
     uniformly across (model, gap_mode).
  2. For each: prints task probe + full agent response + judge's recorded
     scores + judge's recorded reasoning.
  3. Asks the human auditor: "Would you score this materially differently?"
     - "agree" → judge call stands
     - "flip" → record as material miss (would change per-task score)
     - "skip" → record as not audited (e.g. need more time, ambiguous)
     - "back" → re-show the previous sample
  4. After all samples: writes audit-g12.json with the miss-rate.

Output schema (analyze.py expects keys: manual_audit_miss_rate, audited_task_trials):
  {
    "manual_audit_miss_rate": float (0..1),
    "audited_task_trials": int,
    "n_disagreements": int,
    "samples": [{...}]
  }

Usage:
    python evals/v0.2/audit_g12_manual.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--scorecards-dir",
        default=str(REPO_ROOT / "evals" / "results" / "v0.2" / "sweep"),
    )
    p.add_argument("--n-samples", type=int, default=12)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--output",
        default=str(REPO_ROOT / "evals" / "results" / "v0.2" / "audit-g12.json"),
    )
    args = p.parse_args()

    sc_dir = Path(args.scorecards_dir)
    print(f"\n  Loading scorecards from {sc_dir}…")
    scorecards = []
    for path in sorted(sc_dir.glob("*.json")):
        stem = path.stem
        parts = stem.split("__")
        if len(parts) != 3:
            continue
        model, gap_mode, trial_part = parts
        trial = int(trial_part[len("trial"):])
        sc = json.loads(path.read_text())
        scorecards.append({
            "model": model,
            "gap_mode": gap_mode,
            "trial": trial,
            "scorecard": sc,
        })
    print(f"  ✓ Loaded {len(scorecards)} scorecards")

    # Build flat list of task-trials, sample uniformly
    candidates = []
    for sc in scorecards:
        for ts in sc["scorecard"]["task_scores"]:
            candidates.append({
                "model": sc["model"],
                "gap_mode": sc["gap_mode"],
                "trial": sc["trial"],
                "task_id": ts["task_id"],
                "category": ts["category"],
                "original_c": ts["correctness"],
                "original_m": ts["meta_awareness"],
                "original_score": ts["score"],
                "judge_reasoning": ts.get("judge_reasoning", ""),
                "response_full": ts.get("response_full") or ts.get("response_excerpt", ""),
                "prompt_messages": ts.get("prompt_messages", []),
                "gap_messages": ts.get("gap_messages", []),
                "gap_estimated_tokens": ts.get("gap_estimated_tokens", 0),
            })
    rng = random.Random(args.seed)
    samples = rng.sample(candidates, args.n_samples)

    # Load task expected_behavior so we can show the auditor what the judge
    # was checking against.
    import yaml
    task_lookup = {}
    for cat_dir in (REPO_ROOT / "evals" / "v0.2" / "tasks").iterdir():
        for tp in cat_dir.glob("*.yaml"):
            t = yaml.safe_load(tp.read_text())
            task_lookup[t["id"]] = t
    for s in samples:
        s["expected_behavior"] = task_lookup[s["task_id"]]["expected_behavior"]
        s["task_probe"] = "\n".join(
            m["content"] for m in task_lookup[s["task_id"]]["probe"]
        )

    # Interactive loop
    print(f"\n  {'='*70}")
    print(f"  G12 manual audit — {len(samples)} samples to review")
    print(f"  {'='*70}")
    print(f"\n  For each sample, you'll see: task probe, agent response, judge's score+reasoning.")
    print(f"  Decide whether you'd score it materially differently.")
    print(f"  Commands: agree / flip / skip / back / quit\n")

    decisions = [None] * len(samples)  # "agree" | "flip" | "skip" | None
    i = 0
    while i < len(samples):
        s = samples[i]
        print(f"\n{'#'*70}")
        print(f"# Sample {i+1}/{len(samples)}  "
              f"({s['model']} · {s['gap_mode']} · trial{s['trial']} · {s['task_id']})")
        print(f"{'#'*70}\n")
        print(f"--- Task probe (last user message) ---")
        print(s["task_probe"])
        print(f"\n--- Expected behavior (judge's rubric) ---")
        print(s["expected_behavior"])
        print(f"\n--- Agent's full response ---")
        print(s["response_full"])
        print(f"\n--- Judge's recorded scores ---")
        print(f"  correctness:    {s['original_c']}/1")
        print(f"  meta_awareness: {s['original_m']}/1")
        print(f"  total:          {s['original_score']}/2")
        print(f"\n--- Judge's reasoning (if any) ---")
        print(s["judge_reasoning"][:400] if s["judge_reasoning"] else "(none recorded)")
        print()

        while True:
            ans = input("  Your call [agree/flip/skip/back/quit]: ").strip().lower()
            if ans in ("a", "agree"):
                decisions[i] = "agree"
                i += 1
                break
            elif ans in ("f", "flip"):
                decisions[i] = "flip"
                i += 1
                break
            elif ans in ("s", "skip"):
                decisions[i] = "skip"
                i += 1
                break
            elif ans in ("b", "back"):
                if i == 0:
                    print("    (already at first sample)")
                else:
                    i -= 1
                    decisions[i] = None
                break
            elif ans in ("q", "quit"):
                print("\n  Quitting early — partial decisions will be saved.")
                i = len(samples)  # exit outer loop
                break
            else:
                print("    (commands: agree / flip / skip / back / quit)")

    # Compute miss rate
    completed = [(s, d) for s, d in zip(samples, decisions) if d is not None and d != "skip"]
    flips = [(s, d) for s, d in completed if d == "flip"]
    miss_rate = len(flips) / len(completed) if completed else 0.0

    out = {
        "manual_audit_miss_rate": miss_rate,
        "audited_task_trials": len(completed),
        "n_disagreements": len(flips),
        "n_skipped": sum(1 for d in decisions if d == "skip"),
        "n_not_reached": sum(1 for d in decisions if d is None),
        "samples": [
            {
                "model": s["model"],
                "gap_mode": s["gap_mode"],
                "trial": s["trial"],
                "task_id": s["task_id"],
                "original_score": s["original_score"],
                "decision": d,
            }
            for s, d in zip(samples, decisions)
        ],
    }
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))

    print(f"\n  {'='*70}")
    print(f"  G12 audit complete")
    print(f"  {'='*70}")
    print(f"  Audited:        {len(completed)} task-trials")
    print(f"  Disagreements:  {len(flips)}")
    print(f"  Skipped:        {out['n_skipped']}")
    print(f"  Not reached:    {out['n_not_reached']}")
    print(f"\n  Miss rate:  {miss_rate*100:.1f}%  (threshold 5.0%)")
    print(f"  G12 result: {'PASS' if miss_rate < 0.05 else 'FAIL'}")
    print(f"\n  Written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
