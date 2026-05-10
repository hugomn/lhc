"""Diagnostic — run base Qwen3-8B locally via MLX, same /no_think prefix as Ember.

Background: external review of 2026-05-09 (round 2) caught two methodology
holes in yesterday's Ember-vs-Qwen comparison:

  1. Ember runs through local MLX with the slowlit provider's /no_think
     system prefix. Qwen3-8B base ran through OpenRouter without that prefix.
     Different inference configurations.
  2. Ember's local MLX sampling is deterministic — all 3 trials are byte-
     identical per cell. The other 3 models (all OpenRouter) have real
     trial-to-trial variance.

Yesterday's "Ember worse than Qwen by Δ -0.25 (95% CI [-0.46, -0.06])"
might be partly attributable to these inference confounds, not to weights.

This script does the apples-to-apples comparison: base Qwen3-8B on the
same local MLX server, same /no_think prefix, same harness path, current +
neutral gap modes (matches Ember's worst-regression conditions).

We run only 1 trial per cell since MLX sampling is deterministic — pretending
n=3 inflates fake variance. Cost: 24 tasks × 2 modes × 1 trial = 48 task-
runs total, ~$2 in judge calls, ~30 min wall.

Output: evals/results/v0.2/diagnostic-local-qwen/qwen3-8b-local__<mode>__trial1.json

Then compare:
    Ember (8 cells: 4 modes × 1 unique-trial since deterministic)
        vs
    Qwen-local (2 cells: current/neutral × 1 trial)
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
HOST, PORT = "127.0.0.1", 8080

OUT_DIR = REPO_ROOT / "evals" / "results" / "v0.2" / "diagnostic-local-qwen"
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


def start_qwen_base_server():
    """Start mlx_lm.server with NO adapter — just base Qwen3-8B."""
    subprocess.call(["pkill", "-f", "mlx_lm.server"])
    time.sleep(3)
    log_path = "/tmp/qwen-base-v02-server.log"
    log = open(log_path, "w")
    proc = subprocess.Popen(
        [
            PYTHON, "-m", "mlx_lm", "server",
            "--model", str(BASE_MODEL),
            # NO --adapter-path — that's the whole point of this comparison
            "--host", HOST, "--port", str(PORT),
            # Cap prompt cache: previous run OOM'd at ~12GB after 10 cached
            # prefixes accumulated. Base Qwen3-8B (no LoRA) needs more headroom.
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

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Verify Ember's MLX is fully stopped before we start a fresh base server
    print(f"\n  Starting MLX server with base Qwen3-8B (no adapter) at {HOST}:{PORT}…")
    proc, log_path = start_qwen_base_server()
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
            out_path = OUT_DIR / f"qwen3-8b-local__{gap_mode}__trial1.json"
            print(f"\n  Running gap_mode={gap_mode!r}…")
            t0 = time.time()
            # Important: --provider slowlit gives us the SAME /no_think
            # prefix that Ember uses. That's the whole point.
            cmd = [
                PYTHON, "-m", "evals.runners.lhc",
                "--provider", "slowlit",        # same provider config as Ember
                "--model", "Qwen/Qwen3-8B",     # what mlx_lm.server reports
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
                print(f"  [FATAL] qwen-base-local/{gap_mode} exited rc={rc}",
                      file=sys.stderr)
                return 4

            # Verify scorecard
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

    print(f"\n  Diagnostic complete in {(time.time()-started)/60:.1f} min")
    print(f"  Scorecards in {OUT_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
