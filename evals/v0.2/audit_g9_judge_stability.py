"""G9 — judge stability audit for the v0.2 sweep.

Per DECISION.md §5: rejudge a 10% audit sample (≥3 task-trials per model)
with the same Opus 4.7 judge in a fresh API session. If any model's
overall mean shifts by ≥ 0.10 under rejudge, the judge is too noisy at
this granularity.

What this script does:
  1. Sample N task-trials per model uniformly at random across all 4 gap
     modes (default N=5, so 20 rejudge calls total — well above the 3 floor).
  2. For each sample: load the stored expected_behavior + full response
     from the scorecard, send to a fresh Grader instance.
  3. Compute the per-model overall-mean shift if the rejudged scores
     replaced the originals.
  4. Emit JSON with `judge_stability_max_shift` so analyze.py can read it.

Output schema (matches what analyze.py expects):
  {
    "judge_stability_max_shift": float,
    "samples": [{model, gap_mode, task_id, trial,
                 original_score, rejudged_score, original_c, original_m,
                 rejudged_c, rejudged_m}],
    "per_model_shift": {model: float},
    "n_samples": int,
    "n_per_model": int
  }
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

from evals.runners.client import ModelConfig  # noqa: E402
from evals.runners.grader import Grader  # noqa: E402
from evals.runners.lhc import PROVIDER_DEFAULTS  # noqa: E402

load_dotenv(REPO_ROOT / ".env")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--scorecards-dir",
        default=str(REPO_ROOT / "evals" / "results" / "v0.2" / "sweep"),
    )
    p.add_argument(
        "--per-model",
        type=int,
        default=5,
        help="number of rejudge samples per model (default: 5 — total = per_model × 4)",
    )
    p.add_argument(
        "--output",
        default=str(REPO_ROOT / "evals" / "results" / "v0.2" / "audit-g9.json"),
    )
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    sc_dir = Path(args.scorecards_dir)
    if not sc_dir.exists():
        print(f"[fatal] scorecards dir not found: {sc_dir}", file=sys.stderr)
        return 2

    # Build (model, gap_mode, trial, scorecard_path) index
    print(f"  Loading scorecards from {sc_dir}…")
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
            "path": path,
            "scorecard": sc,
        })
    print(f"  ✓ Loaded {len(scorecards)} scorecards")

    # Sample per-model task-trials uniformly across (gap_mode, trial, task_id)
    rng = random.Random(args.seed)
    by_model: dict[str, list] = {}
    for sc in scorecards:
        by_model.setdefault(sc["model"], []).append(sc)

    samples = []  # (model, gap_mode, trial, task_id, expected_behavior, response_full, original_c, original_m)
    for model, model_scs in by_model.items():
        # Each scorecard has 24 task scores; flatten to (scorecard, task_index)
        candidates = []
        for sc in model_scs:
            for ti, ts in enumerate(sc["scorecard"]["task_scores"]):
                candidates.append((sc, ti, ts))
        chosen = rng.sample(candidates, args.per_model)
        for sc, ti, ts in chosen:
            samples.append({
                "model": model,
                "gap_mode": sc["gap_mode"],
                "trial": sc["trial"],
                "task_id": ts["task_id"],
                "category": ts["category"],
                "expected_behavior": None,  # not stored on scorecard; we'll load from task YAML
                "response_full": ts.get("response_full") or ts.get("response_excerpt", ""),
                "original_c": ts["correctness"],
                "original_m": ts["meta_awareness"],
            })

    # Load expected_behavior from task YAML (it's not stored on each scorecard
    # entry — saves space — but we need it for the rejudge call).
    import yaml
    task_lookup: dict[str, str] = {}
    for cat_dir in (REPO_ROOT / "evals" / "v0.2" / "tasks").iterdir():
        for tp in cat_dir.glob("*.yaml"):
            t = yaml.safe_load(tp.read_text())
            task_lookup[t["id"]] = t["expected_behavior"]
    for s in samples:
        s["expected_behavior"] = task_lookup[s["task_id"]]

    # Set up the judge — fresh Grader instance, fresh API session.
    judge_cfg = PROVIDER_DEFAULTS["anthropic"]
    judge_api_key = os.environ.get(judge_cfg["api_key_env"], "")
    if not judge_api_key:
        print(f"[fatal] no judge API key. set {judge_cfg['api_key_env']} in .env",
              file=sys.stderr)
        return 2
    judge = Grader(
        ModelConfig(
            model=judge_cfg["model"],
            base_url=judge_cfg["base_url"],
            api_key=judge_api_key,
        )
    )
    print(f"  Rejudging {len(samples)} samples with {judge_cfg['model']}…")

    flips = 0
    for i, s in enumerate(samples, 1):
        grade = judge.grade(s["expected_behavior"], s["response_full"])
        s["rejudged_c"] = grade.correctness
        s["rejudged_m"] = grade.meta_awareness
        s["original_score"] = s["original_c"] + s["original_m"]
        s["rejudged_score"] = grade.score
        flipped = (s["original_score"] != s["rejudged_score"])
        if flipped:
            flips += 1
        marker = "FLIP" if flipped else "    "
        print(f"  [{i:>2}/{len(samples)}] {marker}  {s['model']:<22} "
              f"{s['gap_mode']:<11} trial{s['trial']} {s['task_id']:<22} "
              f"orig={s['original_score']} rejudged={s['rejudged_score']} "
              f"(c {s['original_c']}→{s['rejudged_c']}, "
              f"m {s['original_m']}→{s['rejudged_m']})")

    # Per-model shift: how much would the model's overall mean change if we
    # substituted the rejudged scores back in? This needs the per-cell mean
    # change scaled by sample fraction.
    per_model_shifts: dict[str, float] = {}
    for model in by_model:
        m_samples = [s for s in samples if s["model"] == model]
        if not m_samples:
            per_model_shifts[model] = 0.0
            continue
        # Original total task-trials per model: 24 tasks × 3 trials × 4 gap_modes = 288
        # The shift in overall mean from rejudging k samples and the rest unchanged:
        #   delta_mean = sum(rejudged - original) / 288
        delta_sum = sum(s["rejudged_score"] - s["original_score"] for s in m_samples)
        # Project: if we assume the same shift rate held across the full population,
        # the expected shift would be delta_sum / k * 288 / 288 = delta_sum / k
        # In other words, the *empirical sample mean shift* is the per-model shift
        # estimate (since we sampled uniformly).
        per_model_shifts[model] = delta_sum / len(m_samples)

    max_shift = max(abs(v) for v in per_model_shifts.values()) if per_model_shifts else 0.0

    out = {
        "judge_stability_max_shift": max_shift,
        "per_model_shift": per_model_shifts,
        "n_samples": len(samples),
        "n_per_model": args.per_model,
        "n_flips": flips,
        "samples": samples,
    }
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))

    print(f"\n  Total flips: {flips}/{len(samples)} ({100*flips/len(samples):.0f}%)")
    print(f"  Per-model mean shift (rejudged − original):")
    for model, shift in per_model_shifts.items():
        print(f"    {model:<22}  {shift:+.3f}")
    print(f"\n  G9 metric: max |per-model shift| = {max_shift:.3f} (threshold 0.10)")
    print(f"  G9 result: {'PASS' if max_shift < 0.10 else 'FAIL'}")
    print(f"\n  Written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
