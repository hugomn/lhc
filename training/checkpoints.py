"""Stage 4 helper — package per-iter checkpoints as loadable adapter dirs.

MLX-LM's `load_adapters` expects a directory containing both
  - adapter_config.json  (the LoRA/DoRA config used during training)
  - adapters.safetensors (the actual weights)

Our training run wrote one adapter_config.json + one weights file per
iter as `0000NNN_adapters.safetensors`. To eval each iter independently,
we need to materialize each as its own self-contained dir.

Run once per training run to expand checkpoints into eval-ready dirs:
    python -m training.checkpoints

Output layout:
    checkpoints/ember-v0.1/
        adapter_config.json
        adapters.safetensors          (final, iter 1000)
        0000NNN_adapters.safetensors  (per-iter raw weights)
        eval/
            iter-100/{adapter_config.json, adapters.safetensors}
            iter-200/...
            ...
            iter-1000/...
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_DIR = REPO_ROOT / "checkpoints" / "ember-v0.1"
EVAL_DIR = CHECKPOINT_DIR / "eval"


def main() -> int:
    config_src = CHECKPOINT_DIR / "adapter_config.json"
    if not config_src.exists():
        print(f"missing {config_src}", file=sys.stderr)
        return 1

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(r"^0+(\d+)_adapters\.safetensors$")

    n = 0
    for src in sorted(CHECKPOINT_DIR.glob("0*_adapters.safetensors")):
        m = pattern.match(src.name)
        if not m:
            continue
        iter_num = int(m.group(1))
        dst_dir = EVAL_DIR / f"iter-{iter_num}"
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config_src, dst_dir / "adapter_config.json")
        shutil.copy2(src, dst_dir / "adapters.safetensors")
        print(f"  iter-{iter_num:>4}: {dst_dir.relative_to(REPO_ROOT)}")
        n += 1

    print(f"\npackaged {n} checkpoint(s) for eval")
    return 0


if __name__ == "__main__":
    sys.exit(main())
