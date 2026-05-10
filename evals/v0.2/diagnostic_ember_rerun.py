"""Rerun Ember v0.1.5 iter-900 under the SAME capped-cache MLX server config
that diagnostic_local_qwen.py uses, so the apples-to-apples comparison loads
both sides from runs taken under matched server settings.

Round-3 reviewer (2026-05-10) called the asymmetry — local Qwen freshly run
under capped cache vs. Ember loaded from the prior sweep — the "last nuisance
objection" worth closing. Decision unchanged either way; this just makes the
audit record clean.

Same gap modes (current + neutral), same n=1 (MLX is deterministic), same
prompt-cache cap (2 entries / 4 GB).

Output: evals/results/v0.2/diagnostic-ember-rerun/ember-v015-iter900__<mode>__trial1.json
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PYTHON = sys.executable

BASE_MODEL = REPO_ROOT / "models" / "qwen3-8b"
EMBER_ADAPTER = REPO_ROOT / "checkpoints" / "ember-v0.1.5" / "eval" / "iter-900"
HOST, PORT = "127.0.0.1", 8080

OUT_DIR = REPO_ROOT / "evals" / "results" / "v0.2" / "diagnostic-ember-rerun"
GAP_MODES = ("current", "neutral")
EXPECTED_TASKS = 24


def wait_ready(timeout_s: int = 180) -> bool:
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
        time.sleep(2)
    return False


def warm() -> None:
    try:
        req = urllib.request.Request(
            f"http://{HOST}:{PORT}/v1/chat/completions",
            data=json.dumps(
                {
                    "model": "Qwen/Qwen3-8B",
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                }
            ).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
        )
        urllib.request.urlopen(req, timeout=60)
    except Exception:
        pass


def start_ember_server():
    """Start mlx_lm.server with Ember adapter AND the capped-cache flags."""
    subprocess.call(["pkill", "-f", "mlx_lm.server"])
    time.sleep(3)
    log_path = "/tmp/ember-rerun-v02-server.log"
    log = open(log_path, "w")
    proc = subprocess.Popen(
        [
            PYTHON, "-m", "mlx_lm", "server",
            "--model", str(BASE_MODEL),
            "--adapter-path", str(EMBER_ADAPTER),
            "--host", HOST, "--port", str(PORT),
            # Match the diagnostic_local_qwen cache cap so both sides of the
            # comparison run under identical server settings.
            "--prompt-cache-size", "2",
            "--prompt-cache-bytes", "4000000000",
        ],
        stdout=log, stderr=log, preexec_fn=os.setsid,
    )
    return proc, log_path


def stop_server(proc) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        pass


def main() -> int:
    if not BASE_MODEL.exists():
        print(f"[fatal] base model dir not found: {BASE_MODEL}", file=sys.stderr)
        return 2
    if not EMBER_ADAPTER.exists():
        print(f"[fatal] ember adapter dir not found: {EMBER_ADAPTER}", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n  Starting MLX server with Ember adapter ({EMBER_ADAPTER.name}) at {HOST}:{PORT}…")
    proc, log_path = start_ember_server()
    print(f"  Server log: {log_path}")
    if not wait_ready():
        print(f"  [fatal] server didn't come up", file=sys.stderr)
        stop_server(proc)
        return 3
    warm()
    print(f"  Server warmed.")

    started = time.time()
    try:
        for gap_mode in GAP_MODES:
            out_path = OUT_DIR / f"ember-v015-iter900__{gap_mode}__trial1.json"
            print(f"\n  Running gap_mode={gap_mode!r}…")
            t0 = time.time()
            cmd = [
                PYTHON, "-m", "evals.runners.lhc",
                "--provider", "slowlit",
                "--model", "Qwen/Qwen3-8B",
                "--judge-provider", "anthropic",
                "--gap-mode", gap_mode,
                "--lhc-version", "0.2",
                "--tasks-dir", str(REPO_ROOT / "evals" / "v0.2" / "tasks"),
                "--output", str(out_path),
            ]
            rc = subprocess.call(cmd, cwd=REPO_ROOT)
            elapsed = time.time() - t0
            print(f"  done in {elapsed:.0f}s, exit={rc}")
            if rc != 0:
                print(f"  [FATAL] ember-rerun/{gap_mode} exited rc={rc}",
                      file=sys.stderr)
                return 4

            try:
                sc = json.loads(out_path.read_text())
                n = len(sc.get("task_scores", []))
                if n != EXPECTED_TASKS:
                    print(f"  [FATAL] scorecard has {n} tasks, expected {EXPECTED_TASKS}",
                          file=sys.stderr)
                    return 5
                print(f"  scorecard OK: overall={sc['overall']:.3f}, "
                      f"by_cat={sc['by_category']}")
            except Exception as e:
                print(f"  [FATAL] scorecard read failed: {e}", file=sys.stderr)
                return 6
    finally:
        print(f"\n  Stopping MLX server…")
        stop_server(proc)
        time.sleep(2)
        subprocess.call(["pkill", "-f", "mlx_lm.server"])

    print(f"\n  Ember rerun complete in {(time.time()-started)/60:.1f} min")
    print(f"  Scorecards in {OUT_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
