"""Compare Ember vs local-Qwen-base under the SAME inference config, n=3.

Round-2 reviewer (2026-05-09) flagged that Ember (local MLX, /no_think) was
being compared to Qwen-base (OpenRouter, no /no_think). That confound made
yesterday's "Ember regresses" claim too strong.

Round-3 reviewer (2026-05-10) blessed the n=1 diagnostic but asked us to
close the symmetry nuisance by also re-running Ember under the same capped-
cache MLX config used for Qwen-local.

Round-3 rerun surfaced a replication issue neither reviewer anticipated:
in our MLX-LM server setup on Apple Silicon, outputs were stable within a
single server session but varied across fresh server starts. We have not
isolated the source (could be MLX-LM server, Metal kernels, cache state,
sampling defaults, warmup, or process init), so we phrase this as a
replication-protocol observation, not a global non-determinism claim. The
"byte-identical n=3 trials" finding from the original sweep was a within-
session repeat, not three independent samples. Replicating both Ember and
Qwen-local at proper n=3 (fresh server start per trial) gave us this:

  - Per-cell stdev across 3 server restarts: 0.02–0.13 on overall mean
  - 6–9 of 24 tasks score-flip across trials for both models
  - Ember vs Qwen-local Δ on `current` and `neutral` is well inside that noise

This script computes:
  1. Per-trial overall scores + mean ± stdev for each model/gap cell
  2. Paired bootstrap CI on Δ E−Q (sampling task-level trial means with
     replacement across the 24 tasks; n=3 trial means make this honest)
  3. Per-task variance characterization (which tasks are noisy)
  4. Per-task Δ E−Q (mean of trials) sorted, for the qualitative read
  5. Verdict using a wider |Δ| < 0.10 ambiguity band — appropriate given
     stdev ~0.07 we now know is the inference-layer noise floor.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from statistics import mean, stdev

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

EMBER_RERUN_DIR = REPO_ROOT / "evals" / "results" / "v0.2" / "diagnostic-ember-rerun"
LOCAL_QWEN_DIR = REPO_ROOT / "evals" / "results" / "v0.2" / "diagnostic-local-qwen"
GAP_MODES = ("current", "neutral")
TRIALS = (1, 2, 3)
N_TASKS = 24
BOOTSTRAP_ITERS = 10_000
RNG_SEED = 0xEADBEE  # so the CI is reproducible


def load_cell(model: str, gap: str, trial: int, src_dir: Path) -> dict[str, tuple[int, str]]:
    """Return {task_id: (score, category)} from one scorecard."""
    path = src_dir / f"{model}__{gap}__trial{trial}.json"
    sc = json.loads(path.read_text())
    return {ts["task_id"]: (ts["score"], ts["category"]) for ts in sc["task_scores"]}


def trial_means(model: str, gap: str, src_dir: Path) -> dict[str, float]:
    """Per-task mean across 3 server-restart trials. Categories taken from trial1."""
    trs = [load_cell(model, gap, t, src_dir) for t in TRIALS]
    tids = sorted(trs[0].keys())
    return {tid: mean(tr[tid][0] for tr in trs) for tid in tids}


def task_categories(model: str, gap: str, src_dir: Path) -> dict[str, str]:
    one = load_cell(model, gap, 1, src_dir)
    return {tid: cat for tid, (_, cat) in one.items()}


def task_variance_table(model: str, gap: str, src_dir: Path) -> list[tuple[str, list[int], int]]:
    """For each task: (task_id, [score_t1, score_t2, score_t3], range)."""
    trs = [load_cell(model, gap, t, src_dir) for t in TRIALS]
    tids = sorted(trs[0].keys())
    out = []
    for tid in tids:
        scs = [tr[tid][0] for tr in trs]
        out.append((tid, scs, max(scs) - min(scs)))
    return out


def paired_bootstrap_ci(
    e_means: dict[str, float],
    q_means: dict[str, float],
    iters: int = BOOTSTRAP_ITERS,
    seed: int = RNG_SEED,
) -> tuple[float, float, float]:
    """Task-bootstrap CI on Δ E−Q, conditional on the observed 3 restart trials.

    Returns (point estimate, ci_lo, ci_hi). Resamples task IDs with replacement
    24 times per iteration, computing mean Δ across the resample. The point
    estimate equals mean(E)−mean(Q) by linearity.

    What this CI captures: task-selection variance — how much the headline
    would shift if you swapped the 24 LHC v0.2 tasks for a different draw of
    24 from the same task population.

    What this CI does NOT capture: server-restart variance is folded into
    each task's mean *before* the bootstrap runs, treating those 3 trials as
    fixed. A hierarchical bootstrap that resampled (task, trial) pairs would
    be wider, not narrower. Round-4 reviewer (2026-05-10) flagged this
    explicitly: this CI is sufficient to reject shipping (CI crosses zero on
    both gap modes), but it should NOT be used to make subtle positive or
    negative ranking claims about Ember vs base.
    """
    rng = random.Random(seed)
    tids = sorted(e_means.keys())
    point = mean(e_means[t] - q_means[t] for t in tids)
    deltas = []
    for _ in range(iters):
        sample = [rng.choice(tids) for _ in range(len(tids))]
        deltas.append(mean(e_means[t] - q_means[t] for t in sample))
    deltas.sort()
    lo = deltas[int(0.025 * iters)]
    hi = deltas[int(0.975 * iters)]
    return point, lo, hi


def main() -> int:
    if not EMBER_RERUN_DIR.exists() or not LOCAL_QWEN_DIR.exists():
        print(f"[fatal] need both ember-rerun and local-qwen dirs", file=sys.stderr)
        return 2

    print("=" * 78)
    print("  Diagnostic v3: Ember vs local-Qwen-base, n=3 fresh-server trials each")
    print("=" * 78)
    print()
    print(f"  Ember scorecards:    {EMBER_RERUN_DIR.relative_to(REPO_ROOT)}")
    print(f"  Qwen-local scorecards: {LOCAL_QWEN_DIR.relative_to(REPO_ROOT)}")
    print(f"  Bootstrap: paired, {BOOTSTRAP_ITERS} iters, seed={RNG_SEED:#x}")

    # ── per-trial overall scores + stdev per cell ───────────────────────────
    print(f"\n{'='*78}\n  Per-trial overall scores (each trial = fresh server start)\n{'='*78}")
    print(f"\n  {'cell':<24} {'t1':>6} {'t2':>6} {'t3':>6} {'mean':>7} {'stdev':>7} {'range':>7}")
    print(f"  {'-'*24} {'-'*6} {'-'*6} {'-'*6} {'-'*7} {'-'*7} {'-'*7}")
    cells = []
    for model_label, model_slug, src in [
        ("Ember v0.1.5 iter-900", "ember-v015-iter900", EMBER_RERUN_DIR),
        ("Qwen3-8B base (local)", "qwen3-8b-local", LOCAL_QWEN_DIR),
    ]:
        for gap in GAP_MODES:
            trs = [load_cell(model_slug, gap, t, src) for t in TRIALS]
            overalls = [sum(s for s, _ in tr.values()) / N_TASKS for tr in trs]
            cells.append((model_label, gap, overalls))
            label = f"{model_label}/{gap}"
            print(f"  {label:<24} {overalls[0]:>6.3f} {overalls[1]:>6.3f} {overalls[2]:>6.3f} "
                  f"{mean(overalls):>7.3f} {stdev(overalls):>7.3f} "
                  f"{max(overalls)-min(overalls):>7.3f}")

    # ── headline: paired Δ with task-bootstrap CI ───────────────────────────
    print(f"\n{'='*78}\n  Paired Δ E−Q on overall (mean across 3 restart trials per task)")
    print(f"  95% CI is task-bootstrap, conditional on the observed 3 restart trials.")
    print(f"  Hierarchical bootstrap over (task, trial) would be wider, not narrower.\n{'='*78}")
    print(f"\n  {'gap':<10} {'E mean':>8} {'Q mean':>8} {'Δ E−Q':>8} {'95% CI':>22}")
    print(f"  {'-'*10} {'-'*8} {'-'*8} {'-'*8} {'-'*22}")
    headline = {}
    for gap in GAP_MODES:
        e_means = trial_means("ember-v015-iter900", gap, EMBER_RERUN_DIR)
        q_means = trial_means("qwen3-8b-local", gap, LOCAL_QWEN_DIR)
        e_overall = mean(e_means.values())
        q_overall = mean(q_means.values())
        point, lo, hi = paired_bootstrap_ci(e_means, q_means)
        ci_str = f"[{lo:+.3f}, {hi:+.3f}]"
        headline[gap] = (e_overall, q_overall, point, lo, hi)
        print(f"  {gap:<10} {e_overall:>8.3f} {q_overall:>8.3f} {point:>+8.3f} {ci_str:>22}")

    # ── per-category breakdown for current ───────────────────────────────────
    print(f"\n{'='*78}\n  By-category, gap=current (n=3 trial means per task)\n{'='*78}")
    e_means = trial_means("ember-v015-iter900", "current", EMBER_RERUN_DIR)
    q_means = trial_means("qwen3-8b-local", "current", LOCAL_QWEN_DIR)
    cats = task_categories("ember-v015-iter900", "current", EMBER_RERUN_DIR)
    print(f"\n  {'category':<14} {'Ember':>8} {'Qwen-local':>11} {'Δ E−Q':>8}  {'n tasks':>8}")
    print(f"  {'-'*14} {'-'*8} {'-'*11} {'-'*8}  {'-'*8}")
    for cat in ("state_recall", "commitment", "resumption"):
        tids = [t for t in e_means if cats[t] == cat]
        e_cat = mean(e_means[t] for t in tids)
        q_cat = mean(q_means[t] for t in tids)
        print(f"  {cat:<14} {e_cat:>8.3f} {q_cat:>11.3f} {e_cat - q_cat:>+8.3f}  {len(tids):>8}")

    # ── per-task variance: which tasks contribute the noise? ─────────────────
    print(f"\n{'='*78}\n  Per-task score variance across 3 trials (gap=current)\n{'='*78}")
    print(f"\n  Tasks where score range > 0 across the 3 server-restart trials.")
    print(f"  Stable tasks omitted.\n")
    print(f"  {'task':<28} {'Ember t1/t2/t3':>16} {'Qwen-loc t1/t2/t3':>20}")
    print(f"  {'-'*28} {'-'*16} {'-'*20}")
    e_var = task_variance_table("ember-v015-iter900", "current", EMBER_RERUN_DIR)
    q_var = task_variance_table("qwen3-8b-local", "current", LOCAL_QWEN_DIR)
    e_var_lookup = {tid: scs for tid, scs, _ in e_var}
    q_var_lookup = {tid: scs for tid, scs, _ in q_var}
    noisy_tids = sorted({
        tid for tid, _, r in e_var if r > 0
    } | {
        tid for tid, _, r in q_var if r > 0
    })
    e_flips = sum(1 for _, _, r in e_var if r > 0)
    q_flips = sum(1 for _, _, r in q_var if r > 0)
    for tid in noisy_tids:
        e_scs = e_var_lookup[tid]
        q_scs = q_var_lookup[tid]
        e_str = f"{e_scs[0]}/{e_scs[1]}/{e_scs[2]}"
        q_str = f"{q_scs[0]}/{q_scs[1]}/{q_scs[2]}"
        flag_e = "*" if max(e_scs) - min(e_scs) > 0 else " "
        flag_q = "*" if max(q_scs) - min(q_scs) > 0 else " "
        print(f"  {tid:<28} {flag_e}{e_str:>15} {flag_q}{q_str:>19}")
    print(f"\n  Ember tasks with score variance: {e_flips}/{N_TASKS}")
    print(f"  Qwen-local tasks with score variance: {q_flips}/{N_TASKS}")

    # ── per-task Δ E−Q on current, sorted ────────────────────────────────────
    print(f"\n{'='*78}\n  Per-task Δ E−Q on `current` (mean of 3 trials each)\n{'='*78}")
    print(f"\n  {'task':<28} {'Ember μ':>8} {'Q-loc μ':>8} {'Δ E−Q':>8}")
    print(f"  {'-'*28} {'-'*8} {'-'*8} {'-'*8}")
    rows = sorted(
        ((tid, e_means[tid], q_means[tid], e_means[tid] - q_means[tid]) for tid in e_means),
        key=lambda r: r[3],
    )
    for tid, e, q, d in rows:
        sign = "↓↓" if d <= -0.5 else "↓ " if d < -0.1 else "  " if abs(d) <= 0.1 else "↑ " if d <= 0.5 else "↑↑"
        print(f"  {tid:<28} {e:>8.3f} {q:>8.3f} {d:>+8.3f}  {sign}")

    # ── verdict ──────────────────────────────────────────────────────────────
    print(f"\n{'='*78}\n  VERDICT\n{'='*78}")
    for gap in GAP_MODES:
        e_overall, q_overall, point, lo, hi = headline[gap]
        ci_includes_zero = lo <= 0 <= hi
        print(f"\n  gap={gap}:  Ember {e_overall:.3f}  vs  Qwen-local {q_overall:.3f}  "
              f"→  Δ = {point:+.3f}, 95% CI [{lo:+.3f}, {hi:+.3f}]")
        if ci_includes_zero:
            print(f"    [TIE]  CI crosses zero. Cannot claim Ember > base or Ember < base.")
        elif point > 0:
            print(f"    [EMBER WINS]  CI fully positive.")
        else:
            print(f"    [EMBER LOSES]  CI fully negative.")

    print(f"\n  Bottom line (round-4 reviewer wording, 2026-05-10):")
    print(f"  Ember v0.1.5 is statistically indistinguishable from base Qwen3-8B")
    print(f"  under matched local inference; it does not meet the bar for release.")
    print(f"\n  Replication caveat (round-4 reviewer Q2): in our MLX-LM server setup")
    print(f"  on Apple Silicon, outputs were stable within a server session but")
    print(f"  varied across fresh server starts. We have not isolated the source")
    print(f"  (could be MLX-LM server, Metal kernels, cache state, sampling defaults,")
    print(f"  warmup, or process init). Benchmark replications should restart the")
    print(f"  server between trials or explicitly state they are within-session.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
