"""Benchmark 8B-class open models on LHC via OpenRouter.

Runs 3 trials per model and writes scorecards to
evals/results/openrouter-<slug>-{1,2,3}.json so we can compare the
same way we compare Ember v0.1.5 trials.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "evals" / "results"
PYTHON = sys.executable

MODELS = [
    ("qwen/qwen3-8b",                    "qwen3-8b-or"),
    ("mistralai/ministral-8b-2512",      "ministral-8b"),
    ("cohere/command-r7b-12-2024",       "command-r7b"),
    ("microsoft/phi-4-mini-instruct",    "phi-4-mini"),
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--trials", type=int, default=3)
    args = p.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()

    for model_id, slug in MODELS:
        print(f"\n{'='*60}\n  {slug}  ({model_id})\n{'='*60}")
        for trial in range(1, args.trials + 1):
            out = OUT_DIR / f"openrouter-{slug}-{trial}.json"
            print(f"\n  [trial {trial}/{args.trials}] → {out.name}")
            t0 = time.time()
            rc = subprocess.call(
                [
                    PYTHON, "-m", "evals.runners.lhc",
                    "--provider", "openrouter",
                    "--model", model_id,
                    "--judge-provider", "anthropic",
                    "--output", str(out),
                ],
                cwd=REPO_ROOT,
            )
            print(f"  done in {time.time()-t0:.0f}s, exit={rc}")

    print(f"\nAll done in {(time.time()-started)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
