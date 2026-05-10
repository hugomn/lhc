"""Replicate Ember diagnostic: two more independent server-restart trials
under the SAME capped-cache MLX config that diagnostic_ember_rerun.py used.

Why: the first rerun (trial1) produced different per-task scores than the
original sweep, despite identical model/adapter/prefix. MLX is apparently
NOT deterministic across server restarts — only within a single server
session. We need to characterize that variance before writing anything up.

Two more trials, fresh server start each, gap modes current + neutral. Skips
trials whose scorecards already exist so this can be re-run safely.

Output: evals/results/v0.2/diagnostic-ember-rerun/ember-v015-iter900__<mode>__trial<N>.json
        for N in {2, 3}
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
TRIALS = (2, 3)
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


def start_ember_server(trial: int):
    subprocess.call(["pkill", "-f", "mlx_lm.server"])
    time.sleep(3)
    log_path = f"/tmp/ember-replicate-v02-trial{trial}-server.log"
    log = open(log_path, "w")
    proc = subprocess.Popen(
        [
            PYTHON, "-m", "mlx_lm", "server",
            "--model", str(BASE_MODEL),
            "--adapter-path", str(EMBER_ADAPTER),
            "--host", HOST, "--port", str(PORT),
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
    if not BASE_MODEL.exists() or not EMBER_ADAPTER.exists():
        print(f"[fatal] base or adapter dir missing", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    started_all = time.time()

    for trial in TRIALS:
        # Skip if both gap modes already done for this trial
        all_done = all(
            (OUT_DIR / f"ember-v015-iter900__{g}__trial{trial}.json").exists()
            for g in GAP_MODES
        )
        if all_done:
            print(f"\n  trial {trial}: scorecards already exist, skipping")
            continue

        print(f"\n  === trial {trial}: starting fresh server ===")
        proc, log_path = start_ember_server(trial)
        print(f"  Server log: {log_path}")
        if not wait_ready():
            print(f"  [fatal] trial {trial} server didn't come up", file=sys.stderr)
            stop_server(proc)
            return 3
        warm()
        print(f"  Server warmed.")

        try:
            for gap_mode in GAP_MODES:
                out_path = OUT_DIR / f"ember-v015-iter900__{gap_mode}__trial{trial}.json"
                if out_path.exists():
                    print(f"  trial {trial} {gap_mode!r}: scorecard exists, skipping")
                    continue
                print(f"\n  trial {trial} gap_mode={gap_mode!r}…")
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
                    print(f"  [FATAL] trial {trial} {gap_mode} exited rc={rc}",
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
            print(f"  stopping trial {trial} server…")
            stop_server(proc)
            time.sleep(2)
            subprocess.call(["pkill", "-f", "mlx_lm.server"])

    print(f"\n  Replication complete in {(time.time()-started_all)/60:.1f} min")
    print(f"  Scorecards in {OUT_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
