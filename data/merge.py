"""Stage 1.4 — merge filtered shards, dedupe, and split into train/eval.

Reads every `data/synthetic/v0.1/filtered-*.jsonl` file produced by the
parallel generators, deduplicates by content hash (the assistant's final
turn), reassigns sequential ids, and splits into a train file and a
held-out eval file.

The eval split is small but stratified by category and difficulty so we
can spot over- or under-coverage during training.

Usage:
    python -m data.merge --eval-fraction 0.1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SYNTH_DIR = REPO_ROOT / "data" / "synthetic" / "v0.1"


def content_hash(example: dict) -> str:
    """Hash the assistant final turn — that's the actual training signal,
    so duplicate hashes are duplicate training examples even if other
    fields differ."""
    msgs = example.get("messages", [])
    final = next((m["content"] for m in reversed(msgs) if m.get("role") == "assistant"), "")
    return hashlib.sha256(final.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge and split synthetic shards.")
    parser.add_argument("--eval-fraction", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    shards = sorted(SYNTH_DIR.glob("filtered-*.jsonl"))
    if not shards:
        print("No filtered shards found in data/synthetic/v0.1/", file=sys.stderr)
        return 1

    seen: set[str] = set()
    merged: list[dict] = []
    per_shard: dict[str, int] = {}
    duplicates = 0

    for shard in shards:
        n = 0
        for line in shard.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ex = json.loads(line)
            except json.JSONDecodeError:
                continue
            h = content_hash(ex)
            if h in seen:
                duplicates += 1
                continue
            seen.add(h)
            merged.append(ex)
            n += 1
        per_shard[shard.name] = n

    # Reassign clean sequential ids
    rng = random.Random(args.seed)
    rng.shuffle(merged)
    for i, ex in enumerate(merged, 1):
        ex["id"] = f"ember_v0.1_{i:05d}"

    # Stratified split: keep eval_fraction of each (category, difficulty) bucket
    bucket: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for ex in merged:
        key = (ex.get("category", "?"), ex.get("difficulty", "?"))
        bucket[key].append(ex)

    train: list[dict] = []
    eval_set: list[dict] = []
    for examples in bucket.values():
        rng.shuffle(examples)
        n_eval = max(1, int(len(examples) * args.eval_fraction))
        eval_set.extend(examples[:n_eval])
        train.extend(examples[n_eval:])

    train_path = SYNTH_DIR / "v0.1_train.jsonl"
    eval_path = SYNTH_DIR / "v0.1_eval.jsonl"
    train_path.write_text("\n".join(json.dumps(e) for e in train) + "\n")
    eval_path.write_text("\n".join(json.dumps(e) for e in eval_set) + "\n")

    print(f"Shards merged: {len(shards)}")
    for name, n in per_shard.items():
        print(f"  {name}: {n} unique kept")
    print(f"Duplicates dropped: {duplicates}")
    print(f"Total unique merged: {len(merged)}")
    print(f"Train: {len(train)} → {train_path.name}")
    print(f"Eval:  {len(eval_set)} → {eval_path.name}")
    print()
    print("Train distribution:")
    train_dist = Counter((e["category"], e["difficulty"]) for e in train)
    cats = sorted({c for c, _ in train_dist.keys()})
    diffs = ["seed", "easy", "medium", "hard"]
    print(f'{"":<14} {"seed":>6} {"easy":>6} {"medium":>6} {"hard":>6}')
    for c in cats:
        row = " ".join(f"{train_dist[(c, d)]:>6}" for d in diffs)
        print(f"{c:<14} {row}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
