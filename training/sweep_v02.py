"""LHC v0.2 sweep — 4 models × 4 gap modes × 3 trials = 48 scorecards.

Pre-registered run per evals/v0.2/DECISION.md §7 step 4.

Models:
  - ember-v015-iter900   (local MLX, slowlit provider, adapter at
                          checkpoints/ember-v0.1.5/eval/iter-900)
  - qwen3-8b             (OpenRouter, qwen/qwen3-8b)
  - ministral-8b         (OpenRouter, mistralai/ministral-8b-2512)
  - llama-31-8b          (OpenRouter, meta-llama/llama-3.1-8b-instruct)

Gap modes: none, placeholder, neutral, current

Output convention (matches what evals/v0.2/analyze.py expects):
  evals/results/v0.2/sweep/<model_slug>__<gap_mode>__trial<N>.json

Fail-fast: any nonzero rc from the harness aborts the sweep. Any scorecard
with != 24 task scores aborts the sweep. We do NOT silently continue past
errors — we hit that footgun in the v0.1.5 sweep and learned the hard way.

Cost estimate: ~$5 in Anthropic judge calls (Opus 4.7 × 48 × 24 tasks).
Wall clock: ~30-60 min (Ember local MLX is the rate limiter — ~3 min/trial).
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
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

# Output dir + naming convention. analyze.py reads exactly this layout.
OUT_DIR = REPO_ROOT / "evals" / "results" / "v0.2" / "sweep"

# Local MLX bits (Ember).
BASE_MODEL = REPO_ROOT / "models" / "qwen3-8b"
EMBER_ADAPTER = REPO_ROOT / "checkpoints" / "ember-v0.1.5" / "eval" / "iter-900"
HOST, PORT = "127.0.0.1", 8080

# Pre-registered model identities. Slug must match analyze.EXPECTED_MODELS.
LOCAL_MODELS = [
    {
        "slug": "ember-v015-iter900",
        "provider": "slowlit",
        "model_id": "Qwen/Qwen3-8B",  # what mlx_lm.server reports
        "adapter": EMBER_ADAPTER,
    },
]

OPENROUTER_MODELS = [
    {"slug": "qwen3-8b", "provider": "openrouter", "model_id": "qwen/qwen3-8b"},
    {"slug": "ministral-8b", "provider": "openrouter", "model_id": "mistralai/ministral-8b-2512"},
    {"slug": "llama-31-8b", "provider": "openrouter", "model_id": "meta-llama/llama-3.1-8b-instruct"},
]

GAP_MODES = ("none", "placeholder", "neutral", "current")
TRIALS = 3
EXPECTED_TASKS = 24


# ---------------------------------------------------------------------------
# MLX server lifecycle (local Ember only)
# ---------------------------------------------------------------------------


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
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer local",
            },
        )
        urllib.request.urlopen(req, timeout=60)
    except Exception:
        pass


def start_ember_server(adapter_dir: Path):
    subprocess.call(["pkill", "-f", "mlx_lm.server"])
    time.sleep(3)
    log = open(f"/tmp/ember-v02-server.log", "w")
    proc = subprocess.Popen(
        [
            PYTHON, "-m", "mlx_lm", "server",
            "--model", str(BASE_MODEL),
            "--adapter-path", str(adapter_dir),
            "--host", HOST, "--port", str(PORT),
        ],
        stdout=log, stderr=log, preexec_fn=os.setsid,
    )
    return proc


def stop_ember_server(proc) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Single trial invocation
# ---------------------------------------------------------------------------


def run_trial(
    model_slug: str,
    provider: str,
    model_id: str,
    gap_mode: str,
    trial: int,
) -> tuple[int, Path, float]:
    """Invoke evals.runners.lhc once. Returns (rc, output_path, elapsed_s)."""
    out = OUT_DIR / f"{model_slug}__{gap_mode}__trial{trial}.json"
    cmd = [
        PYTHON, "-m", "evals.runners.lhc",
        "--provider", provider,
        "--model", model_id,
        "--judge-provider", "anthropic",
        "--gap-mode", gap_mode,
        "--lhc-version", "0.2",
        "--tasks-dir", str(REPO_ROOT / "evals" / "v0.2" / "tasks"),
        "--output", str(out),
    ]
    t0 = time.time()
    rc = subprocess.call(cmd, cwd=REPO_ROOT)
    elapsed = time.time() - t0
    return rc, out, elapsed


def verify_scorecard(path: Path) -> tuple[bool, str]:
    """Return (ok, reason). ok=True if scorecard has exactly EXPECTED_TASKS scores."""
    if not path.exists():
        return (False, "file does not exist")
    try:
        sc = json.loads(path.read_text())
    except Exception as e:
        return (False, f"json parse failed: {e}")
    n = len(sc.get("task_scores", []))
    if n != EXPECTED_TASKS:
        return (False, f"got {n} task scores, expected {EXPECTED_TASKS}")
    expected = sc.get("expected_task_count", 0)
    if expected and expected != EXPECTED_TASKS:
        return (False, f"expected_task_count={expected}, want {EXPECTED_TASKS}")
    return (True, "ok")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--skip-existing", action="store_true",
                   help="if a scorecard already exists and is valid, skip running its trial")
    p.add_argument("--gap-modes", default=",".join(GAP_MODES),
                   help="comma-separated subset to run (default: all 4)")
    p.add_argument("--models", default=None,
                   help="comma-separated subset of model slugs to run (default: all 4)")
    args = p.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    requested_modes = tuple(m.strip() for m in args.gap_modes.split(",") if m.strip())
    for m in requested_modes:
        if m not in GAP_MODES:
            print(f"[fatal] unknown gap_mode {m!r}; valid: {GAP_MODES}",
                  file=sys.stderr)
            return 2

    all_models = LOCAL_MODELS + OPENROUTER_MODELS
    if args.models:
        wanted = set(s.strip() for s in args.models.split(","))
        all_models = [m for m in all_models if m["slug"] in wanted]

    total_trials = len(all_models) * len(requested_modes) * TRIALS
    print(f"\nLHC v0.2 sweep — {len(all_models)} model(s) × "
          f"{len(requested_modes)} gap mode(s) × {TRIALS} trials = "
          f"{total_trials} scorecards")
    print(f"  output: {OUT_DIR.relative_to(REPO_ROOT)}")
    print(f"  fail-fast on any nonzero rc or short scorecard.\n")

    sweep_t0 = time.time()
    done = 0

    # Loop ordering: per gap mode, do all 4 models. Means we boot/teardown
    # the Ember server 4 times (once per gap_mode) instead of running all
    # Ember trials for one mode before moving to the next, which would still
    # be 4 boots if we want to interleave with OpenRouter calls. Simpler:
    # for each gap_mode, do Ember (boot, 3 trials, kill) then 3 OpenRouter
    # models (no server lifecycle).
    for gap_mode in requested_modes:
        print(f"\n{'#'*70}\n  gap_mode = {gap_mode!r}\n{'#'*70}")

        for model in all_models:
            slug = model["slug"]
            provider = model["provider"]
            model_id = model["model_id"]

            print(f"\n--- {slug} (gap_mode={gap_mode}) ---")

            # Local MLX bring-up if needed
            ember_proc = None
            if provider == "slowlit":
                adapter = model["adapter"]
                if not adapter.exists():
                    print(f"  [fatal] adapter dir not found: {adapter}",
                          file=sys.stderr)
                    return 3
                print(f"  starting MLX server with adapter {adapter.name}…")
                ember_proc = start_ember_server(adapter)
                if not wait_ready():
                    print(f"  [fatal] MLX server didn't come up", file=sys.stderr)
                    stop_ember_server(ember_proc)
                    return 3
                warm()
                print(f"  server warmed.")

            try:
                for trial in range(1, TRIALS + 1):
                    out = OUT_DIR / f"{slug}__{gap_mode}__trial{trial}.json"

                    if args.skip_existing:
                        ok, _ = verify_scorecard(out)
                        if ok:
                            done += 1
                            print(f"  [{done}/{total_trials}] [skip] "
                                  f"{out.name} already valid")
                            continue

                    print(f"  [{done+1}/{total_trials}] running trial {trial} "
                          f"→ {out.name}")
                    rc, out_path, elapsed = run_trial(
                        slug, provider, model_id, gap_mode, trial
                    )
                    print(f"      done in {elapsed:.0f}s, exit={rc}")

                    if rc != 0:
                        print(f"  [FATAL] {slug}/{gap_mode}/trial{trial} "
                              f"exited rc={rc}. Aborting sweep.",
                              file=sys.stderr)
                        if ember_proc is not None:
                            stop_ember_server(ember_proc)
                        return 4

                    ok, reason = verify_scorecard(out_path)
                    if not ok:
                        print(f"  [FATAL] scorecard {out_path.name} invalid: "
                              f"{reason}. Aborting sweep.", file=sys.stderr)
                        if ember_proc is not None:
                            stop_ember_server(ember_proc)
                        return 5

                    done += 1
                    elapsed_total = time.time() - sweep_t0
                    if done > 0:
                        rate = done / elapsed_total
                        eta_s = (total_trials - done) / rate if rate > 0 else 0
                        print(f"      progress {done}/{total_trials}, "
                              f"ETA ~{eta_s/60:.1f} min")
            finally:
                if ember_proc is not None:
                    print(f"  stopping MLX server…")
                    stop_ember_server(ember_proc)
                    time.sleep(2)

    # Final cleanup of any stray MLX server
    subprocess.call(["pkill", "-f", "mlx_lm.server"])

    print(f"\n{'='*70}")
    print(f"  Sweep complete: {done}/{total_trials} scorecards in "
          f"{(time.time()-sweep_t0)/60:.1f} min")
    print(f"  Run analysis with:")
    print(f"    python evals/v0.2/analyze.py "
          f"--scorecards-dir {OUT_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
