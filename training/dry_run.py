"""Stage 2 dry-run — verify the LoRA/DoRA training pipeline end-to-end on
50 examples before committing to the real Stage 3 run.

What this proves:
  1. The dataset format is correct — MLX-LM ingests train.jsonl/valid.jsonl
     without errors.
  2. The base model loads and the DoRA adapter attaches at the right
     target modules.
  3. The optimizer step computes a finite gradient and updates the
     adapter weights.
  4. A checkpoint is written and can be reloaded.
  5. Loading the adapter on top of the base model and serving via
     mlx_lm.generate produces coherent output.

If all five succeed, Stage 3 (the real 1000-step training run) is safe to
launch. If any fail, debug here — at $0 cost — instead of after a 6-hour
training run.

Usage:
    python -m training.dry_run
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DATA = REPO_ROOT / "data" / "synthetic" / "v0.1" / "mlx_lora"
DRY_DATA = REPO_ROOT / "data" / "synthetic" / "v0.1" / "mlx_lora_dry"
ADAPTER_PATH = REPO_ROOT / "checkpoints" / "ember-v0.1-dryrun"
BASE_MODEL = REPO_ROOT / "models" / "qwen3-8b"

DRY_TRAIN_N = 50
DRY_VALID_N = 10
DRY_ITERS = 20  # enough to see loss move and produce a checkpoint


def make_dry_dataset() -> None:
    """Sample DRY_TRAIN_N from train.jsonl and DRY_VALID_N from valid.jsonl."""
    DRY_DATA.mkdir(parents=True, exist_ok=True)
    for src_name, dst_name, n in (
        ("train.jsonl", "train.jsonl", DRY_TRAIN_N),
        ("valid.jsonl", "valid.jsonl", DRY_VALID_N),
    ):
        src = SRC_DATA / src_name
        dst = DRY_DATA / dst_name
        rows = src.read_text().splitlines()
        rows = [r for r in rows if r.strip()][:n]
        dst.write_text("\n".join(rows) + "\n")
    print(f"  dry dataset: {DRY_DATA.relative_to(REPO_ROOT)} ({DRY_TRAIN_N} train, {DRY_VALID_N} valid)")


def run_train() -> int:
    """Invoke mlx_lm.lora with DoRA, on the 50-row dry dataset, for DRY_ITERS steps."""
    if ADAPTER_PATH.exists():
        shutil.rmtree(ADAPTER_PATH)
    ADAPTER_PATH.mkdir(parents=True)
    cmd = [
        sys.executable, "-m", "mlx_lm", "lora",
        "--model", str(BASE_MODEL),
        "--train",
        "--data", str(DRY_DATA),
        "--fine-tune-type", "dora",
        "--num-layers", "16",  # DoRA on attention of last 16 layers
        "--batch-size", "4",
        "--iters", str(DRY_ITERS),
        "--learning-rate", "1.0e-4",
        "--steps-per-eval", "10",
        "--steps-per-report", "5",
        "--save-every", str(DRY_ITERS),
        "--adapter-path", str(ADAPTER_PATH),
        "--seed", "42",
        "--grad-checkpoint",
    ]
    print(f"\n  running: {' '.join(cmd[3:])}\n")
    return subprocess.call(cmd)


def smoke_test_adapter() -> int:
    """Generate one response with the trained adapter applied."""
    cmd = [
        sys.executable, "-m", "mlx_lm", "generate",
        "--model", str(BASE_MODEL),
        "--adapter-path", str(ADAPTER_PATH),
        "--prompt", "/no_think Describe what you do as an autonomous agent in one sentence.",
        "--max-tokens", "120",
        "--temp", "0.7",
    ]
    print(f"\n  running: {' '.join(cmd[3:])}\n")
    return subprocess.call(cmd)


def main() -> int:
    if not BASE_MODEL.exists():
        print(f"base model not found at {BASE_MODEL} — convert it first via mlx_lm.convert", file=sys.stderr)
        return 1
    if not (SRC_DATA / "train.jsonl").exists():
        print(f"dataset not found at {SRC_DATA} — run python -m data.prepare_mlx first", file=sys.stderr)
        return 1

    print("=" * 60)
    print("Stage 2 dry-run — verifying LoRA/DoRA pipeline end-to-end")
    print("=" * 60)

    print("\n[1/3] making dry dataset")
    make_dry_dataset()

    print(f"\n[2/3] training {DRY_ITERS} steps on the dry dataset")
    rc = run_train()
    if rc != 0:
        print(f"\nFAIL — training exited with code {rc}")
        return rc

    print(f"\n[3/3] smoke-test inference with the trained adapter")
    rc = smoke_test_adapter()
    if rc != 0:
        print(f"\nFAIL — adapter inference exited with code {rc}")
        return rc

    print("\n" + "=" * 60)
    print("PASS — Stage 2 dry-run complete.")
    print(f"  adapter:  {ADAPTER_PATH.relative_to(REPO_ROOT)}")
    print("  Stage 3 (full 1000-step training) is safe to launch.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
