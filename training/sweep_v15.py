"""Sweep multiple v0.1.5 checkpoints with 3 trials each.

Same lifecycle as eval_one but iterates across checkpoints, restarting
the server between them.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_MODEL = REPO_ROOT / "models" / "qwen3-8b"
EVAL_DIR = REPO_ROOT / "checkpoints" / "ember-v0.1.5" / "eval"
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


def warm() -> None:
    try:
        warm_req = urllib.request.Request(
            f"http://{HOST}:{PORT}/v1/chat/completions",
            data=json.dumps({
                "model": "Qwen/Qwen3-8B",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            }).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
        )
        urllib.request.urlopen(warm_req, timeout=60)
    except Exception:
        pass


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--iters", default="300,600,900")
    p.add_argument("--trials", type=int, default=3)
    args = p.parse_args()

    iter_list = [int(x.strip()) for x in args.iters.split(",") if x.strip()]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()

    for it in iter_list:
        adapter_dir = EVAL_DIR / f"iter-{it}"
        if not adapter_dir.exists():
            print(f"  [skip] {adapter_dir} missing", file=sys.stderr)
            continue

        print(f"\n{'='*60}")
        print(f"  v0.1.5 CHECKPOINT iter-{it} ({args.trials} trials)")
        print(f"{'='*60}")

        # Stop any running server
        subprocess.call(["pkill", "-f", "mlx_lm.server"])
        time.sleep(3)

        log = open(f"/tmp/ember-v0.1.5-server-iter{it}.log", "w")
        server = subprocess.Popen(
            [
                PYTHON, "-m", "mlx_lm", "server",
                "--model", str(BASE_MODEL),
                "--adapter-path", str(adapter_dir),
                "--host", HOST, "--port", str(PORT),
            ],
            stdout=log, stderr=log, preexec_fn=os.setsid,
        )

        if not wait_ready():
            print(f"  server didn't come up", file=sys.stderr)
            try:
                os.killpg(os.getpgid(server.pid), signal.SIGTERM)
            except Exception:
                pass
            continue
        warm()
        print(f"  server warm, starting trials")

        # Fail-fast (post-2026-05-08 review): if any trial errors, abort the
        # remaining trials for THIS checkpoint and continue to the next one.
        # We don't kill the whole sweep — partial sweep data is still useful
        # — but we never silently publish a partial scorecard.
        for trial in range(1, args.trials + 1):
            out = OUT_DIR / f"ember-v0.1.5-iter{it}-{trial}.json"
            print(f"\n  [trial {trial}] → {out.name}")
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
            print(f"  done in {time.time()-t0:.0f}s, exit={rc}")
            if rc != 0:
                print(f"  [WARN] trial {trial} failed (exit={rc}); skipping remaining trials for iter-{it}",
                      file=sys.stderr)
                break

        try:
            os.killpg(os.getpgid(server.pid), signal.SIGTERM)
        except Exception:
            pass

    subprocess.call(["pkill", "-f", "mlx_lm.server"])
    print(f"\nAll done in {(time.time()-started)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
