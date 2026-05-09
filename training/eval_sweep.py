"""Stage 4 eval sweep — score every checkpoint of interest on LHC × N trials.

Workflow per checkpoint:
  1. (Re)start mlx_lm.server with the chosen adapter.
  2. Run `evals.runners.lhc --provider slowlit` N times, writing each
     scorecard to evals/results/ember-v0.1-iterNNN-<trial>.json.
  3. Stop the server.

Then loop to the next checkpoint.

Usage:
    python -m training.eval_sweep --iters 100,400,700 --trials 3
"""

from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_MODEL = REPO_ROOT / "models" / "qwen3-8b"
EVAL_DIR = REPO_ROOT / "checkpoints" / "ember-v0.1" / "eval"
OUT_DIR = REPO_ROOT / "evals" / "results"

PYTHON = sys.executable
HOST = "127.0.0.1"
PORT = 8080


def wait_for_server_ready(timeout_s: int = 120) -> bool:
    """Poll /v1/models until it returns 200 (server fully loaded), or timeout."""
    import urllib.request, urllib.error
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            with urllib.request.urlopen(
                f"http://{HOST}:{PORT}/v1/models", timeout=2
            ) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError, socket.timeout):
            pass
        time.sleep(1)
    return False


def stop_server() -> None:
    subprocess.call(["pkill", "-f", "mlx_lm.server"])
    time.sleep(2)


def start_server(adapter_dir: Path) -> subprocess.Popen:
    log = open(REPO_ROOT / f"/tmp/ember-server-{adapter_dir.name}.log", "w")
    return subprocess.Popen(
        [
            PYTHON, "-m", "mlx_lm", "server",
            "--model", str(BASE_MODEL),
            "--adapter-path", str(adapter_dir),
            "--host", HOST,
            "--port", str(PORT),
        ],
        stdout=log, stderr=log,
        preexec_fn=os.setsid,
    )


def run_eval(out_path: Path) -> int:
    """Run one full LHC eval against the running server."""
    return subprocess.call(
        [
            PYTHON, "-m", "evals.runners.lhc",
            "--provider", "slowlit",
            "--judge-provider", "anthropic",
            "--output", str(out_path),
        ],
        cwd=REPO_ROOT,
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--iters", default="100,400,700", help="comma-separated checkpoint iterations to eval")
    p.add_argument("--trials", type=int, default=3)
    args = p.parse_args()

    iter_list = [int(x.strip()) for x in args.iters.split(",") if x.strip()]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    total = len(iter_list) * args.trials
    done = 0
    started = time.time()

    for it in iter_list:
        adapter_dir = EVAL_DIR / f"iter-{it}"
        if not adapter_dir.exists():
            print(f"[skip] {adapter_dir} not found", file=sys.stderr)
            continue

        print(f"\n{'=' * 60}")
        print(f"  CHECKPOINT iter-{it}  ({args.trials} trials)")
        print(f"{'=' * 60}")

        stop_server()
        proc = start_server(adapter_dir)
        if not wait_for_server_ready(timeout_s=120):
            print(f"[fail] server didn't come up for iter-{it}", file=sys.stderr)
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                pass
            continue

        for trial in range(1, args.trials + 1):
            out = OUT_DIR / f"ember-v0.1-iter{it}-{trial}.json"
            print(f"\n  [trial {trial}/{args.trials}] → {out.name}")
            t0 = time.time()
            rc = run_eval(out)
            elapsed = time.time() - t0
            done += 1
            remaining = (total - done) * (elapsed if elapsed > 0 else 60)
            print(
                f"  done in {elapsed:.0f}s, exit={rc}, "
                f"progress {done}/{total}, ETA ~{remaining/60:.1f} min"
            )

        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            pass

    stop_server()
    print(f"\nAll done in {(time.time()-started)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
