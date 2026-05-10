"""Build tasks.parquet + scorecards.parquet from canonical YAML / JSON.

These Parquet files are the rendering source for the HuggingFace Dataset Viewer
on hugonogueira/lhc-v0.2. The YAML / JSON files under tasks/ and results/
remain the canonical source of truth — the Parquets are a *derived view*
suitable for tabular browsing.

Run from the repo root:

    python evals/v0.2/build_parquet.py

Outputs:
    evals/v0.2/data/tasks.parquet       (24 rows — one per task)
    evals/v0.2/data/scorecards.parquet  (one row per task-trial-cell)

The Parquet directory is gitignored in the working repo; the published copies
live inside the HF dataset under `data/`.

Schema decisions:
- tasks.parquet keeps `setup` / `gap_messages` / `probe` as JSON-encoded strings.
  Each task is a small structured document; flattening to columns would lose
  structure (variable number of messages, nested role/content). JSON-as-string
  is what HF viewer renders cleanly while preserving the structure.
- scorecards.parquet flattens to one row per (model, gap_mode, trial, task_id)
  cell with the score, sub-scores, judge reasoning, and full response. This
  is the shape someone would want to filter/group/aggregate on the HF viewer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TASKS_DIR = REPO_ROOT / "evals" / "v0.2" / "tasks"
PUBLISHED = REPO_ROOT / "evals" / "results" / "published" / "lhc-v0.2"
OUT_DIR = REPO_ROOT / "evals" / "v0.2" / "data"

CATEGORIES = ("state_recall", "commitment", "resumption")


def _dump_messages(msgs: list) -> str:
    """Serialize a setup/probe message list to a compact JSON string."""
    return json.dumps(msgs, ensure_ascii=False)


def build_tasks_table() -> pa.Table:
    """One row per task. 24 rows expected."""
    rows = []
    for cat in CATEGORIES:
        for p in sorted((TASKS_DIR / cat).glob(f"{cat}_v2_*.yaml")):
            task = yaml.safe_load(p.read_text())
            rows.append(
                {
                    "task_id": task["id"],
                    "category": task.get("category", cat),
                    "difficulty": task.get("difficulty"),
                    "description": (task.get("description") or "").strip(),
                    "setup_messages_json": _dump_messages(task.get("setup", [])),
                    "gap_messages_json": _dump_messages(task.get("gap_messages", [])),
                    "probe_messages_json": _dump_messages(task.get("probe", [])),
                    "expected_behavior": (task.get("expected_behavior") or "").strip(),
                    "source_file": str(p.relative_to(REPO_ROOT)),
                }
            )
    print(f"  tasks: {len(rows)} rows")
    return pa.Table.from_pylist(rows)


def build_scorecards_table() -> pa.Table:
    """One row per (model_slug, gap_mode, trial, task_id). 720 rows expected:

    - 48 sweep scorecards × 24 tasks = 1152 rows (4 models × 4 gap modes × 3 trials × 24 tasks)
    - 12 diagnostic scorecards × 24 tasks = 288 rows (2 models × 2 gap modes × 3 trials × 24 tasks)
    Total: 1440 rows.
    """
    rows = []
    sources = [
        ("sweep", PUBLISHED / "sweep"),
        ("diagnostic-ember-rerun", PUBLISHED / "diagnostic-ember-rerun"),
        ("diagnostic-local-qwen", PUBLISHED / "diagnostic-local-qwen"),
    ]
    for source_label, src_dir in sources:
        for p in sorted(src_dir.glob("*.json")):
            sc = json.loads(p.read_text())
            # Filename pattern: <model_slug>__<gap_mode>__trial<N>.json
            stem_parts = p.stem.split("__")
            model_slug = sc.get("model_slug", stem_parts[0])
            gap_mode = sc.get("gap_mode", stem_parts[1])
            trial = int(stem_parts[2][len("trial"):])
            base_model = sc.get("base_model")
            adapter = sc.get("adapter")
            inference_path = sc.get("inference_path")
            for ts in sc["task_scores"]:
                judge_raw = ts.get("judge_reasoning")
                if isinstance(judge_raw, (dict, list)):
                    judge_reasoning = json.dumps(judge_raw, ensure_ascii=False)
                else:
                    judge_reasoning = judge_raw or ""
                rows.append(
                    {
                        "source": source_label,
                        "model_slug": model_slug,
                        "base_model": base_model,
                        "adapter": adapter,
                        "inference_path": inference_path,
                        "gap_mode": gap_mode,
                        "trial": trial,
                        "task_id": ts["task_id"],
                        "category": ts["category"],
                        "score": ts["score"],
                        "correctness": ts.get("correctness"),
                        "meta_awareness": ts.get("meta_awareness"),
                        "response_full": ts.get("response_full") or "",
                        "judge_reasoning": judge_reasoning,
                        "source_file": str(p.relative_to(REPO_ROOT)),
                    }
                )
    print(f"  scorecards: {len(rows)} rows")
    return pa.Table.from_pylist(rows)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Building Parquet companions in {OUT_DIR.relative_to(REPO_ROOT)}/")
    tasks_table = build_tasks_table()
    scorecards_table = build_scorecards_table()

    pq.write_table(tasks_table, OUT_DIR / "tasks.parquet", compression="zstd")
    pq.write_table(scorecards_table, OUT_DIR / "scorecards.parquet", compression="zstd")

    tasks_size = (OUT_DIR / "tasks.parquet").stat().st_size
    sc_size = (OUT_DIR / "scorecards.parquet").stat().st_size
    print(f"  wrote tasks.parquet ({tasks_size:,} bytes)")
    print(f"  wrote scorecards.parquet ({sc_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
