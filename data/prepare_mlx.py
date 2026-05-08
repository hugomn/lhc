"""Convert v0.1 train/eval splits to MLX-LM's expected format.

MLX-LM's `lora` trainer reads a directory containing exactly:
  - train.jsonl
  - valid.jsonl
  - (optional) test.jsonl

Each row must be `{"messages": [{"role": "...", "content": "..."}]}`.
Our v0.1_train.jsonl / v0.1_eval.jsonl already use that schema but
include extra metadata fields (id, category, difficulty, based_on, axis)
that MLX-LM ignores at best, complains about at worst. We strip them
and write the cleaned files to a fresh directory so the originals stay
intact for analysis.

Usage:
    python -m data.prepare_mlx
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "data" / "synthetic" / "v0.1"
OUT_DIR = SRC_DIR / "mlx_lora"


def clean(example: dict) -> dict:
    """Strip everything except `messages`."""
    return {"messages": example["messages"]}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pairs = [
        (SRC_DIR / "v0.1_train.jsonl", OUT_DIR / "train.jsonl"),
        (SRC_DIR / "v0.1_eval.jsonl", OUT_DIR / "valid.jsonl"),
    ]
    for src, dst in pairs:
        if not src.exists():
            print(f"missing source: {src}", file=sys.stderr)
            return 1
        rows = [json.loads(line) for line in src.read_text().splitlines() if line.strip()]
        cleaned = [clean(r) for r in rows]
        dst.write_text("\n".join(json.dumps(r) for r in cleaned) + "\n")
        print(f"  {src.name} → {dst.relative_to(REPO_ROOT)}  ({len(cleaned)} rows)")

    print(f"\nMLX-LM dataset ready at {OUT_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
