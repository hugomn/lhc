"""LHC v0.2 sweep analysis — compute gates G1..G13 and emit verdict.

The script consumes the 48 scorecards from the Day 2 sweep
(4 models × 4 gap modes × 3 trials), applies the pre-registered
DECISION.md gates, and emits a structured report. There is no
interactive judgment in this script — its output IS the verdict.

Built before the sweep ran (per DECISION.md §7) so that gate
computations cannot drift to fit the data.

Usage:
    python evals/v0.2/analyze.py \\
        --scorecards-dir evals/results/v0.2/sweep \\
        --audit-results evals/results/v0.2/audit.json   # optional, for G9 + G12
        --output evals/results/v0.2/verdict.json

Scorecard naming convention (the sweep script writes this exact pattern):
    <model_slug>__<gap_mode>__trial<N>.json

with the model_slug in {ember-v015-iter900, qwen3-8b, ministral-8b, llama-31-8b}
and gap_mode in {none, placeholder, neutral, current}.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Pre-registered model identifiers. The script REFUSES to run if the
# scorecard corpus doesn't match exactly — no implicit dropping of
# unexpected models, no implicit substitutions.
EXPECTED_MODELS = {
    "ember-v015-iter900",
    "qwen3-8b",
    "ministral-8b",
    "llama-31-8b",
}
EMBER = "ember-v015-iter900"
QWEN = "qwen3-8b"
MINISTRAL = "ministral-8b"

EXPECTED_GAP_MODES = {"none", "placeholder", "neutral", "current"}
EXPECTED_TRIALS = 3
EXPECTED_TASKS_PER_SCORECARD = 24
EXPECTED_TOTAL_SCORECARDS = (
    len(EXPECTED_MODELS) * len(EXPECTED_GAP_MODES) * EXPECTED_TRIALS
)  # = 48
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_RNG_SEED = 42  # reproducibility


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Cell:
    """One (model, gap_mode) cell — collects trials."""
    model: str
    gap_mode: str
    # task_scores[trial_index][task_id] = score (0/1/2)
    task_scores: list[dict[str, int]] = field(default_factory=list)
    # task_categories[task_id] = "state_recall" | "commitment" | "resumption"
    task_categories: dict[str, str] = field(default_factory=dict)


@dataclass
class GateResult:
    name: str
    description: str
    passed: bool
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Verdict:
    decision_row: str
    action: str
    gate_results: list[GateResult] = field(default_factory=list)
    summary_stats: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_scorecards(scorecards_dir: Path) -> dict[tuple[str, str], Cell]:
    """Load every <model>__<mode>__trial<N>.json into the cell structure.
    Validates the corpus is complete; raises SystemExit if not.
    """
    cells: dict[tuple[str, str], Cell] = {}
    files = sorted(scorecards_dir.glob("*.json"))
    print(f"  Loading {len(files)} scorecards from {scorecards_dir}…")

    for path in files:
        # Parse filename: <model>__<gap_mode>__trial<N>.json
        stem = path.stem
        parts = stem.split("__")
        if len(parts) != 3 or not parts[2].startswith("trial"):
            raise SystemExit(
                f"  [fatal] {path.name}: bad filename. Expected "
                f"<model>__<gap_mode>__trial<N>.json"
            )
        model, gap_mode, trial_part = parts
        try:
            trial_index = int(trial_part[len("trial"):])
        except ValueError:
            raise SystemExit(f"  [fatal] {path.name}: cannot parse trial index")

        if model not in EXPECTED_MODELS:
            raise SystemExit(
                f"  [fatal] {path.name}: unexpected model {model!r}; "
                f"expected one of {sorted(EXPECTED_MODELS)}"
            )
        if gap_mode not in EXPECTED_GAP_MODES:
            raise SystemExit(
                f"  [fatal] {path.name}: unexpected gap_mode {gap_mode!r}"
            )

        sc = json.loads(path.read_text())
        if sc.get("gap_mode") and sc["gap_mode"] != gap_mode:
            raise SystemExit(
                f"  [fatal] {path.name}: filename says gap_mode={gap_mode!r} "
                f"but scorecard says {sc['gap_mode']!r}"
            )
        if len(sc.get("task_scores", [])) != EXPECTED_TASKS_PER_SCORECARD:
            raise SystemExit(
                f"  [fatal] {path.name}: scorecard has "
                f"{len(sc.get('task_scores', []))} task scores, expected "
                f"{EXPECTED_TASKS_PER_SCORECARD}"
            )

        key = (model, gap_mode)
        cell = cells.setdefault(key, Cell(model=model, gap_mode=gap_mode))
        # task_scores[i] is a dict; the trial_index-1 position in the list
        # must be filled with the right trial. Extend with empty placeholders
        # if needed.
        while len(cell.task_scores) < trial_index:
            cell.task_scores.append({})
        for ts in sc["task_scores"]:
            tid = ts["task_id"]
            cell.task_scores[trial_index - 1][tid] = ts["score"]
            cell.task_categories[tid] = ts["category"]

    # Corpus completeness check.
    missing = []
    for model in EXPECTED_MODELS:
        for mode in EXPECTED_GAP_MODES:
            cell = cells.get((model, mode))
            if cell is None:
                missing.append(f"{model}__{mode} (all 3 trials)")
                continue
            if len(cell.task_scores) != EXPECTED_TRIALS:
                missing.append(
                    f"{model}__{mode} (have {len(cell.task_scores)} trials, "
                    f"expected {EXPECTED_TRIALS})"
                )
                continue
            for ti, trial_scores in enumerate(cell.task_scores, start=1):
                if len(trial_scores) != EXPECTED_TASKS_PER_SCORECARD:
                    missing.append(
                        f"{model}__{mode}__trial{ti} "
                        f"({len(trial_scores)}/{EXPECTED_TASKS_PER_SCORECARD} tasks)"
                    )
    if missing:
        msg = "  [fatal] Corpus incomplete. Missing/short:\n    - " + "\n    - ".join(missing)
        raise SystemExit(msg)

    print(f"  ✓ Corpus complete: {len(EXPECTED_MODELS)} models × "
          f"{len(EXPECTED_GAP_MODES)} gap modes × {EXPECTED_TRIALS} trials × "
          f"{EXPECTED_TASKS_PER_SCORECARD} tasks each.")
    return cells


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def cell_overall_mean(cell: Cell) -> float:
    """Mean over all task-trials in the cell (24 tasks × 3 trials = 72 scores)."""
    all_scores = [s for trial in cell.task_scores for s in trial.values()]
    return float(np.mean(all_scores)) if all_scores else 0.0


def cell_category_mean(cell: Cell, category: str) -> float:
    """Mean over task-trials whose task is in the given category."""
    scores = [
        s
        for trial in cell.task_scores
        for tid, s in trial.items()
        if cell.task_categories[tid] == category
    ]
    return float(np.mean(scores)) if scores else 0.0


def per_task_means(cell: Cell) -> dict[str, float]:
    """For each task_id, its mean score across the cell's trials."""
    out = {}
    for tid in cell.task_categories:
        scores = [trial[tid] for trial in cell.task_scores if tid in trial]
        out[tid] = float(np.mean(scores)) if scores else 0.0
    return out


# ---------------------------------------------------------------------------
# Paired bootstrap CI for delta(model_A − model_B) on a given gap_mode
# ---------------------------------------------------------------------------


def paired_bootstrap_delta_ci(
    cell_a: Cell,
    cell_b: Cell,
    category: str | None = None,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_RNG_SEED,
) -> tuple[float, float, float]:
    """Return (point_estimate, ci_lower, ci_upper) for the per-task mean delta.

    Per DECISION.md §2: pair by (task_id, trial_index), then bootstrap-resample
    at the TASK level (not the trial level — tasks are exchangeable, trials
    within a task are not).

    Procedure:
      1. For each task, compute mean(model_A scores) − mean(model_B scores)
         where the means are taken across the 3 trials. This gives one
         per-task delta.
      2. Bootstrap-resample the list of per-task deltas 10000 times.
      3. Take the 2.5th and 97.5th percentiles of the resample means.
    """
    assert cell_a.gap_mode == cell_b.gap_mode, (
        f"paired comparison requires same gap_mode, got "
        f"{cell_a.gap_mode!r} vs {cell_b.gap_mode!r}"
    )

    # Per-task delta = mean(A's trials on task) − mean(B's trials on task).
    per_task_deltas: list[float] = []
    for tid in sorted(cell_a.task_categories):
        if category and cell_a.task_categories[tid] != category:
            continue
        a_scores = [trial[tid] for trial in cell_a.task_scores]
        b_scores = [trial[tid] for trial in cell_b.task_scores]
        per_task_deltas.append(float(np.mean(a_scores) - np.mean(b_scores)))

    if not per_task_deltas:
        return (0.0, 0.0, 0.0)

    arr = np.array(per_task_deltas)
    point = float(arr.mean())

    rng = np.random.default_rng(seed)
    n = len(arr)
    resample_means = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        resample_means[i] = arr[idx].mean()
    lo, hi = np.percentile(resample_means, [2.5, 97.5])
    return (point, float(lo), float(hi))


# ---------------------------------------------------------------------------
# Variance attribution (G13) — simple two-factor SS decomposition
# ---------------------------------------------------------------------------


def variance_attribution(cells: dict[tuple[str, str], Cell]) -> dict[str, float]:
    """Compute a simple SS decomposition of overall task-trial scores.

    For each task-trial cell value y, attribute variance to:
      - SS(model)   = sum over models of N_m * (mean_model − grand_mean)^2
      - SS(gap)     = sum over gaps   of N_g * (mean_gap   − grand_mean)^2
      - SS(total)   = sum of (y − grand_mean)^2 across all task-trials

    This is the same shape as a one-way ANOVA but computed independently
    per factor (no interaction term) — sufficient for the G13 question
    "does gap_mode account for more variance than model_id?"
    """
    rows = []
    for (model, gap_mode), cell in cells.items():
        for trial in cell.task_scores:
            for tid, score in trial.items():
                rows.append((model, gap_mode, tid, score))
    if not rows:
        return {"ss_model": 0.0, "ss_gap": 0.0, "ss_total": 0.0}

    scores = np.array([r[3] for r in rows], dtype=float)
    grand = float(scores.mean())

    # SS by model
    by_model: dict[str, list[float]] = defaultdict(list)
    by_gap: dict[str, list[float]] = defaultdict(list)
    for model, gap, _tid, sc in rows:
        by_model[model].append(sc)
        by_gap[gap].append(sc)

    ss_model = sum(len(v) * (np.mean(v) - grand) ** 2 for v in by_model.values())
    ss_gap = sum(len(v) * (np.mean(v) - grand) ** 2 for v in by_gap.values())
    ss_total = float(((scores - grand) ** 2).sum())

    return {
        "ss_model": float(ss_model),
        "ss_gap": float(ss_gap),
        "ss_total": ss_total,
        "frac_model": float(ss_model / ss_total) if ss_total > 0 else 0.0,
        "frac_gap": float(ss_gap / ss_total) if ss_total > 0 else 0.0,
        "grand_mean": grand,
    }


# ---------------------------------------------------------------------------
# Rank inversion (G10)
# ---------------------------------------------------------------------------


def rank_inversion(cells: dict[tuple[str, str], Cell]) -> dict[str, Any]:
    """Compute model rankings per gap mode and the max position swap
    between `neutral` and `current`.
    """
    def ranks_for(mode: str) -> list[tuple[str, float]]:
        rows = [
            (m, cell_overall_mean(cells[(m, mode)]))
            for m in EXPECTED_MODELS
        ]
        # Sort by mean desc; deterministic on ties via model name.
        rows.sort(key=lambda x: (-x[1], x[0]))
        return rows

    neutral_ranks = ranks_for("neutral")
    current_ranks = ranks_for("current")

    neutral_pos = {m: i for i, (m, _) in enumerate(neutral_ranks)}
    current_pos = {m: i for i, (m, _) in enumerate(current_ranks)}

    max_swap = max(abs(neutral_pos[m] - current_pos[m]) for m in EXPECTED_MODELS)

    return {
        "neutral_ranks": neutral_ranks,
        "current_ranks": current_ranks,
        "max_position_swap": max_swap,
    }


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


def compute_gates(
    cells: dict[tuple[str, str], Cell],
    audit_results: dict | None = None,
) -> list[GateResult]:
    out: list[GateResult] = []

    # Cell shortcuts
    def C(m: str, g: str) -> Cell:
        return cells[(m, g)]

    # G1: current overall, Ember ≥ Qwen + 0.20
    delta_g1 = cell_overall_mean(C(EMBER, "current")) - cell_overall_mean(C(QWEN, "current"))
    out.append(GateResult(
        name="G1",
        description="current overall: Ember ≥ Qwen + 0.20",
        passed=delta_g1 >= 0.20,
        detail={
            "ember_mean": cell_overall_mean(C(EMBER, "current")),
            "qwen_mean": cell_overall_mean(C(QWEN, "current")),
            "delta": delta_g1,
            "threshold": 0.20,
        },
    ))

    # G2: current resumption, Ember ≥ Qwen + 0.30
    delta_g2 = (
        cell_category_mean(C(EMBER, "current"), "resumption")
        - cell_category_mean(C(QWEN, "current"), "resumption")
    )
    out.append(GateResult(
        name="G2",
        description="current resumption: Ember ≥ Qwen + 0.30",
        passed=delta_g2 >= 0.30,
        detail={
            "ember_resumption_mean": cell_category_mean(C(EMBER, "current"), "resumption"),
            "qwen_resumption_mean": cell_category_mean(C(QWEN, "current"), "resumption"),
            "delta": delta_g2,
            "threshold": 0.30,
        },
    ))

    # G3: neutral overall, Ember ≥ Qwen + 0.10
    delta_g3 = cell_overall_mean(C(EMBER, "neutral")) - cell_overall_mean(C(QWEN, "neutral"))
    out.append(GateResult(
        name="G3",
        description="neutral overall: Ember ≥ Qwen + 0.10",
        passed=delta_g3 >= 0.10,
        detail={
            "ember_mean": cell_overall_mean(C(EMBER, "neutral")),
            "qwen_mean": cell_overall_mean(C(QWEN, "neutral")),
            "delta": delta_g3,
            "threshold": 0.10,
        },
    ))

    # G4: paired bootstrap 95% CI lower bound for current overall delta > 0
    point, lo, hi = paired_bootstrap_delta_ci(
        C(EMBER, "current"), C(QWEN, "current")
    )
    out.append(GateResult(
        name="G4",
        description="paired-bootstrap 95% CI lower bound (current overall, Ember − Qwen) > 0.00",
        passed=lo > 0.0,
        detail={
            "delta_point_estimate": point,
            "ci_lower_95": lo,
            "ci_upper_95": hi,
        },
    ))

    # G5: current overall, Ministral ≥ Ember + 0.20
    delta_g5 = cell_overall_mean(C(MINISTRAL, "current")) - cell_overall_mean(C(EMBER, "current"))
    out.append(GateResult(
        name="G5",
        description="current overall: Ministral ≥ Ember + 0.20",
        passed=delta_g5 >= 0.20,
        detail={
            "ministral_mean": cell_overall_mean(C(MINISTRAL, "current")),
            "ember_mean": cell_overall_mean(C(EMBER, "current")),
            "delta": delta_g5,
            "threshold": 0.20,
        },
    ))

    # G6: neutral overall, Ministral ≥ Ember + 0.15
    delta_g6 = cell_overall_mean(C(MINISTRAL, "neutral")) - cell_overall_mean(C(EMBER, "neutral"))
    out.append(GateResult(
        name="G6",
        description="neutral overall: Ministral ≥ Ember + 0.15",
        passed=delta_g6 >= 0.15,
        detail={
            "ministral_mean": cell_overall_mean(C(MINISTRAL, "neutral")),
            "ember_mean": cell_overall_mean(C(EMBER, "neutral")),
            "delta": delta_g6,
            "threshold": 0.15,
        },
    ))

    # G7: current resumption, Ministral ≥ Ember + 0.30
    delta_g7 = (
        cell_category_mean(C(MINISTRAL, "current"), "resumption")
        - cell_category_mean(C(EMBER, "current"), "resumption")
    )
    out.append(GateResult(
        name="G7",
        description="current resumption: Ministral ≥ Ember + 0.30",
        passed=delta_g7 >= 0.30,
        detail={
            "ministral_resumption_mean": cell_category_mean(C(MINISTRAL, "current"), "resumption"),
            "ember_resumption_mean": cell_category_mean(C(EMBER, "current"), "resumption"),
            "delta": delta_g7,
            "threshold": 0.30,
        },
    ))

    # G8: NO gap mode shows Ember ahead of Ministral by ≥ 0.10
    # (Note: G8 is phrased as a gates-fail-if-violated condition. "Passed"
    # here means: it is true that no gap mode shows Ember ahead by ≥ 0.10.)
    deltas_per_mode = {
        mode: cell_overall_mean(C(EMBER, mode)) - cell_overall_mean(C(MINISTRAL, mode))
        for mode in EXPECTED_GAP_MODES
    }
    max_ember_lead = max(deltas_per_mode.values())
    out.append(GateResult(
        name="G8",
        description="No gap mode shows Ember ahead of Ministral by ≥ 0.10",
        passed=max_ember_lead < 0.10,
        detail={
            "ember_minus_ministral_per_mode": deltas_per_mode,
            "max_ember_lead": max_ember_lead,
            "threshold": 0.10,
        },
    ))

    # G9: judge instability — needs audit input. If not provided, mark
    # passed=None so we can flag "cannot evaluate yet" downstream.
    if audit_results and "judge_stability_max_shift" in audit_results:
        max_shift = float(audit_results["judge_stability_max_shift"])
        out.append(GateResult(
            name="G9",
            description="Judge stability: max overall shift on rejudge < 0.10",
            passed=max_shift < 0.10,
            detail={
                "max_overall_shift_under_rejudge": max_shift,
                "threshold": 0.10,
            },
        ))
    else:
        out.append(GateResult(
            name="G9",
            description="Judge stability: max overall shift on rejudge < 0.10",
            passed=False,  # conservative: assume worst until measured
            detail={
                "status": "NOT YET MEASURED — audit pass required",
            },
        ))

    # G10: rank inversion across neutral vs current
    inv = rank_inversion(cells)
    out.append(GateResult(
        name="G10",
        description="No rank changes >2 positions across neutral vs current",
        passed=inv["max_position_swap"] <= 2,
        detail={
            "neutral_ranks": [(m, round(s, 3)) for m, s in inv["neutral_ranks"]],
            "current_ranks": [(m, round(s, 3)) for m, s in inv["current_ranks"]],
            "max_position_swap": inv["max_position_swap"],
        },
    ))

    # G11: CI overlap. Both Ember/Qwen AND Ember/Ministral CIs include ±0.15.
    p_eq, lo_eq, hi_eq = paired_bootstrap_delta_ci(
        C(EMBER, "current"), C(QWEN, "current")
    )
    p_em, lo_em, hi_em = paired_bootstrap_delta_ci(
        C(EMBER, "current"), C(MINISTRAL, "current")
    )
    eq_includes = lo_eq <= -0.15 and hi_eq >= 0.15
    em_includes = lo_em <= -0.15 and hi_em >= 0.15
    out.append(GateResult(
        name="G11",
        description="CI overlap: NOT both Ember/Qwen and Ember/Ministral CIs span ±0.15",
        passed=not (eq_includes and em_includes),
        detail={
            "ember_qwen_ci": [lo_eq, hi_eq],
            "ember_qwen_spans_pm15": eq_includes,
            "ember_ministral_ci": [lo_em, hi_em],
            "ember_ministral_spans_pm15": em_includes,
        },
    ))

    # G12: manual audit miss-rate. Audit-input only.
    if audit_results and "manual_audit_miss_rate" in audit_results:
        miss = float(audit_results["manual_audit_miss_rate"])
        out.append(GateResult(
            name="G12",
            description="Manual audit miss-rate < 5%",
            passed=miss < 0.05,
            detail={
                "miss_rate": miss,
                "threshold": 0.05,
                "audited_count": audit_results.get("audited_task_trials", "?"),
            },
        ))
    else:
        out.append(GateResult(
            name="G12",
            description="Manual audit miss-rate < 5%",
            passed=False,
            detail={"status": "NOT YET MEASURED — manual audit required"},
        ))

    # G13: variance attribution. Pass if SS(model) > SS(gap).
    var = variance_attribution(cells)
    out.append(GateResult(
        name="G13",
        description="SS(model) > SS(gap_mode) — capability dominates over distractor sensitivity",
        passed=var["ss_model"] > var["ss_gap"],
        detail={
            "ss_model": var["ss_model"],
            "ss_gap": var["ss_gap"],
            "ss_total": var["ss_total"],
            "frac_model": var["frac_model"],
            "frac_gap": var["frac_gap"],
        },
    ))

    return out


def apply_decision_matrix(gates: list[GateResult]) -> tuple[str, str]:
    """Return (decision_row, action) per DECISION.md §6.

    Order: G9–G13 first (any failure → benchmark insufficient). Then
    Ember-vs-base. Then Ember-vs-Ministral.
    """
    by_name = {g.name: g for g in gates}

    insufficient_gates = ["G9", "G10", "G11", "G12", "G13"]
    failing_insufficient = [n for n in insufficient_gates if not by_name[n].passed]
    if failing_insufficient:
        return (
            f"Benchmark insufficient ({', '.join(failing_insufficient)} fired)",
            "STOP. Do not ship. Do not invest more training cycles. "
            "Build a different evaluation: hybrid of LongBench / RULER / 8–12 "
            "hand-built held-out product tasks. Re-decide everything from there.",
        )

    g1234_pass = all(by_name[n].passed for n in ("G1", "G2", "G3", "G4"))
    g5678_pass = all(by_name[n].passed for n in ("G5", "G6", "G7", "G8"))
    g5678_some = any(not by_name[n].passed for n in ("G5", "G6", "G7", "G8")) and not g5678_pass

    if not g1234_pass:
        return (
            "Ember not better than base (G1–G4 fail)",
            "STOP the v0.1.5 line. Whatever Ember v0.1.5 is doing, it is not "
            "measurably improving on base Qwen3-8B in a clean comparison. "
            "Either retrain on a different recipe (more distractor-style data, "
            "different rank/modules) or pivot base. Do not publish v0.1.",
        )

    if g1234_pass and g5678_pass:
        # Ember beats base, AND loses to Ministral (G5–G8 all pass means
        # Ministral genuinely better).
        return (
            "Ember beats base, loses to Ministral (G1–G4 pass AND G5–G8 pass)",
            "Two sub-options: (a) if Ember's resumption gap is gap-style-only "
            "(G7 holds but G6 doesn't), train against distractors and re-test; "
            "(b) if Ember loses on neutral too, switch base model (Mistral 8B-class "
            "with native long context, or Qwen3-8B + YaRN re-evaluated). "
            "Do not publish v0.1.",
        )

    if g1234_pass and not g5678_pass and not g5678_some:
        # G5–G8 ALL fail: Ministral does not clearly beat Ember.
        return (
            "Ember beats base, NOT worse than Ministral (G1–G4 pass AND G5–G8 fail)",
            "VALIDATE on held-out product tasks (≥ 8 real agent workflows; see "
            "OQ-01 in journal). If product tasks agree, publish as "
            "hugonogueira/ember-v0.1 with a model card that states the LHC v0.2 "
            "numbers, the published methodology, and the held-out product results. "
            "Do not publish before product validation.",
        )

    # G1–G4 pass, G5–G8 mixed (some pass, some fail): treat as ambiguous
    return (
        "Ember beats base, ambiguous vs Ministral (G1–G4 pass AND G5–G8 mixed)",
        "Treat as Ember tied with Ministral. Validate on held-out product tasks "
        "before publishing. Do not publish before product validation.",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--scorecards-dir",
        default=str(REPO_ROOT / "evals" / "results" / "v0.2" / "sweep"),
        help="directory containing the 48 sweep scorecards",
    )
    p.add_argument(
        "--audit-results",
        default=None,
        help="optional JSON with audit results "
             "(keys: judge_stability_max_shift, manual_audit_miss_rate, audited_task_trials)",
    )
    p.add_argument(
        "--output",
        default=str(REPO_ROOT / "evals" / "results" / "v0.2" / "verdict.json"),
        help="path to write the structured verdict JSON",
    )
    args = p.parse_args()

    sc_dir = Path(args.scorecards_dir)
    if not sc_dir.exists():
        print(f"[fatal] scorecards dir not found: {sc_dir}", file=sys.stderr)
        return 2

    cells = load_scorecards(sc_dir)

    audit_results = None
    if args.audit_results:
        audit_path = Path(args.audit_results)
        if audit_path.exists():
            audit_results = json.loads(audit_path.read_text())
            print(f"  ✓ Loaded audit results: {sorted(audit_results.keys())}")
        else:
            print(f"  [warn] audit-results path not found: {audit_path}")

    print("\n  Computing gates G1..G13…")
    gates = compute_gates(cells, audit_results=audit_results)
    decision_row, action = apply_decision_matrix(gates)

    # Build summary stats: per (model, mode) overall + per-category means.
    summary: dict[str, Any] = {"per_cell": {}}
    for (model, mode), cell in cells.items():
        summary["per_cell"][f"{model}__{mode}"] = {
            "overall_mean": round(cell_overall_mean(cell), 3),
            "by_category": {
                cat: round(cell_category_mean(cell, cat), 3)
                for cat in ("state_recall", "commitment", "resumption")
            },
        }

    verdict = Verdict(
        decision_row=decision_row,
        action=action,
        gate_results=gates,
        summary_stats=summary,
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(asdict(verdict), indent=2))

    # Console report
    print(f"\n{'='*70}\n  GATE RESULTS\n{'='*70}")
    for g in gates:
        mark = "✓ PASS" if g.passed else "✗ FAIL"
        print(f"  {mark}  {g.name:>3}  {g.description}")
        # Show the single most decision-relevant detail line
        if g.name in ("G1", "G2", "G3", "G5", "G6", "G7"):
            print(f"          delta={g.detail['delta']:+.3f}  threshold={g.detail['threshold']}")
        elif g.name == "G4":
            print(f"          point={g.detail['delta_point_estimate']:+.3f}  "
                  f"95% CI = [{g.detail['ci_lower_95']:+.3f}, {g.detail['ci_upper_95']:+.3f}]")
        elif g.name == "G8":
            print(f"          max Ember lead over Ministral across modes: "
                  f"{g.detail['max_ember_lead']:+.3f}")
        elif g.name == "G10":
            print(f"          max position swap (neutral vs current): {g.detail['max_position_swap']}")
        elif g.name == "G11":
            print(f"          Ember/Qwen CI: [{g.detail['ember_qwen_ci'][0]:+.3f}, {g.detail['ember_qwen_ci'][1]:+.3f}]")
            print(f"          Ember/Ministral CI: [{g.detail['ember_ministral_ci'][0]:+.3f}, {g.detail['ember_ministral_ci'][1]:+.3f}]")
        elif g.name == "G13":
            print(f"          SS(model)={g.detail['ss_model']:.2f}  "
                  f"SS(gap)={g.detail['ss_gap']:.2f}  "
                  f"frac_model={g.detail['frac_model']:.3f}  "
                  f"frac_gap={g.detail['frac_gap']:.3f}")
        elif g.name in ("G9", "G12"):
            if "status" in g.detail:
                print(f"          {g.detail['status']}")

    print(f"\n{'='*70}\n  DECISION (per DECISION.md §6)\n{'='*70}")
    print(f"  Row: {decision_row}")
    print(f"\n  Action: {action}")
    print(f"\n  Verdict written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
