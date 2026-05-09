"""Run N trials of LHC against ONE checkpoint, with explicit server lifecycle.

Simpler than eval_sweep — no checkpoint swapping. Use this to add trials
to a single checkpoint after the fact.

Usage:
    python -m training.eval_one --iter 400 --trials 2 --start-trial 2
"""

from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
import json as _json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_MODEL = REPO_ROOT / "models" / "qwen3-8b"
DEFAULT_EVAL_DIR = REPO_ROOT / "checkpoints" / "ember-v0.1" / "eval"
OUT_DIR = REPO_ROOT / "evals" / "results"
HOST, PORT = "127.0.0.1", 8080
PYTHON = sys.executable


def wait_ready(timeout_s: int = 180) -> bool:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            with urllib.request.urlopen(f"http://{HOST}:{PORT}/v1/models", timeout=2) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError, socket.timeout):
            pass
        time.sleep(2)
    return False


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--iter", type=int, required=True)
    p.add_argument("--trials", type=int, default=1)
    p.add_argument("--start-trial", type=int, default=1)
    p.add_argument("--checkpoint-dir", default=str(DEFAULT_EVAL_DIR),
                   help="dir containing iter-N/ adapter subdirs")
    p.add_argument("--out-prefix", default="ember-v0.1",
                   help="output filename prefix; results land at <prefix>-iter<N>-<trial>.json")
    args = p.parse_args()

    eval_dir = Path(args.checkpoint_dir)
    adapter_dir = eval_dir / f"iter-{args.iter}"
    if not adapter_dir.exists():
        print(f"missing {adapter_dir}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.call(["pkill", "-f", "mlx_lm.server"])
    time.sleep(3)

    log = open(f"/tmp/ember-server-iter{args.iter}.log", "w")
    server = subprocess.Popen(
        [
            PYTHON, "-m", "mlx_lm", "server",
            "--model", str(BASE_MODEL),
            "--adapter-path", str(adapter_dir),
            "--host", HOST, "--port", str(PORT),
        ],
        stdout=log, stderr=log, preexec_fn=os.setsid,
    )

    print(f"  starting server with adapter {adapter_dir.name}…")
    if not wait_ready():
        print(f"  server failed to start", file=sys.stderr)
        try:
            os.killpg(os.getpgid(server.pid), signal.SIGTERM)
        except Exception:
            pass
        return 2

    # warm
    try:
        warm_req = urllib.request.Request(
            f"http://{HOST}:{PORT}/v1/chat/completions",
            data=_json.dumps({
                "model": "Qwen/Qwen3-8B",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            }).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
        )
        urllib.request.urlopen(warm_req, timeout=60)
        print(f"  server warmed and ready")
    except Exception as e:
        print(f"  warmup error (continuing): {e}", file=sys.stderr)

    started = time.time()
    for i in range(args.trials):
        trial_num = args.start_trial + i
        out = OUT_DIR / f"{args.out_prefix}-iter{args.iter}-{trial_num}.json"
        print(f"\n  [trial {trial_num}] → {out.name}")
        t0 = time.time()
        rc = subprocess.call(
            [
                PYTHON, "-m", "evals.runners.lhc",
                "--provider", "slowlit",
                "--judge-provider", "anthropic",
                "--output", str(out),
            ],
            cwd=REPO_ROOT,
        )
        print(f"  trial {trial_num} done in {time.time()-t0:.0f}s, exit={rc}")

    print(f"\n  total: {(time.time()-started)/60:.1f} min")

    try:
        os.killpg(os.getpgid(server.pid), signal.SIGTERM)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
