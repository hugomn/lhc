"""Stage 1.2 — few-shot validation gate.

Runs the LHC benchmark against a target model, but with K seed examples
injected as in-context demonstrations before each task. Tests whether the
seeds in `data/seeds/v0.1.jsonl` actually teach the executor → narrator
behavior we're targeting.

Decision gate: if few-shot K2.6 lifts meta-awareness from ~0.42 to ≥0.65
on held-out LHC tasks, the seed set is teaching the right thing and we
proceed to Stage 1.3 (scale to ~2k synthetic examples). If not, we
redesign the seeds before spending API on synthetic generation.

Held-out evaluation: when scoring an LHC task, we exclude any seed whose
`based_on` field matches the task id, so the evaluation never sees a seed
derived from the same source task. This is the closest thing to a
train/test split that preserves both the seed coverage and the eval
fairness.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress

from .client import Client, ModelConfig
from .gap import generate_gap
from .grader import Grader
from .lhc import CATEGORIES, DEFAULT_GAP_TOKENS, PROVIDER_DEFAULTS, TASKS_DIR

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
console = Console()

SEEDS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "seeds" / "v0.1.jsonl"


@dataclass
class FewShotTaskScore:
    task_id: str
    category: str
    score: int
    correctness: int
    meta_awareness: int
    response_excerpt: str = ""
    judge_reasoning: str = ""
    seeds_used: list[str] = field(default_factory=list)


@dataclass
class FewShotScorecard:
    model: str
    judge: str
    lhc_version: str
    n_shots: int
    overall: float
    correctness_avg: float
    meta_avg: float
    by_category: dict[str, float]
    task_scores: list[FewShotTaskScore] = field(default_factory=list)


def load_seeds() -> list[dict]:
    return [json.loads(line) for line in SEEDS_PATH.read_text().splitlines() if line.strip()]


def load_tasks() -> list[dict]:
    tasks: list[dict] = []
    for category in CATEGORIES:
        category_dir = TASKS_DIR / category
        if not category_dir.exists():
            continue
        for path in sorted(category_dir.glob("*.yaml")):
            with path.open() as f:
                tasks.append(yaml.safe_load(f))
    return tasks


def pick_shots(seeds: list[dict], task_id: str, n: int, prefer_category: str | None = None) -> list[dict]:
    """Pick n seeds for the few-shot prompt, excluding any derived from the eval task.

    Bias toward seeds in the same category as the eval task — those carry the
    most transferable signal. Fill the remainder from other categories so the
    model sees the pattern across all three.
    """
    eligible = [s for s in seeds if s.get("based_on") != task_id]
    if prefer_category:
        same_cat = [s for s in eligible if s["category"] == prefer_category]
        other = [s for s in eligible if s["category"] != prefer_category]
        ordered = same_cat + other
    else:
        ordered = eligible
    return ordered[:n]


def assemble_few_shot_messages(
    task: dict, shots: list[dict], gap_tokens: int
) -> list[dict[str, str]]:
    """Build the message sequence: shot demonstrations → task setup → gap → probe.

    Each shot's full message thread is concatenated, prefixed with a brief
    'EXAMPLE n:' delimiter so the model can tell apart the demos from the
    real task. After all shots, the actual task is appended in the standard
    LHC shape.
    """
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are an autonomous agent operating across long sessions. "
                "When you act, you proactively reference the earlier setup, "
                "standing rules, or session-resume payload that justifies "
                "your action. You execute correctly AND name the source. "
                f"Below are {len(shots)} examples of this style. After the "
                "examples, the real task begins."
            ),
        }
    ]

    for i, shot in enumerate(shots, 1):
        messages.append(
            {"role": "user", "content": f"--- EXAMPLE {i} (do not respond — just learn the pattern) ---"}
        )
        messages.extend(shot["messages"])

    messages.append(
        {"role": "user", "content": "--- END OF EXAMPLES. THE REAL TASK BEGINS NOW. ---"}
    )

    # Real task setup → gap → probe (same structure as runners/lhc.py)
    messages.extend(task.get("setup", []))
    gap = generate_gap(target_tokens=gap_tokens, seed=hash(task["id"]) & 0xFFFFFFFF)
    messages.extend(gap.messages)
    messages.extend(task.get("probe", []))
    return messages


def main() -> None:
    parser = argparse.ArgumentParser(description="LHC few-shot validation gate.")
    parser.add_argument("--provider", default="moonshot", choices=list(PROVIDER_DEFAULTS))
    parser.add_argument("--judge-provider", default="anthropic", choices=list(PROVIDER_DEFAULTS))
    parser.add_argument("--n-shots", type=int, default=5, help="number of seed demos per task")
    parser.add_argument("--gap-tokens", type=int, default=DEFAULT_GAP_TOKENS)
    parser.add_argument("--output", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    target_d = PROVIDER_DEFAULTS[args.provider]
    target_cfg = ModelConfig(
        model=target_d["model"],
        base_url=target_d["base_url"],
        api_key=os.environ.get(target_d["api_key_env"], ""),
    )
    judge_d = PROVIDER_DEFAULTS[args.judge_provider]
    judge_cfg = ModelConfig(
        model=judge_d["model"],
        base_url=judge_d["base_url"],
        api_key=os.environ.get(judge_d["api_key_env"], ""),
    )
    if not target_cfg.api_key or not judge_cfg.api_key:
        console.print("[red]Missing API key — check .env[/red]")
        return

    seeds = load_seeds()
    tasks = load_tasks()
    if args.limit:
        tasks = tasks[: args.limit]

    console.print(
        f"[bold]Few-shot validation:[/bold] target={target_cfg.model} "
        f"judge={judge_cfg.model} n_shots={args.n_shots} tasks={len(tasks)}"
    )

    target = Client(target_cfg)
    grader = Grader(judge_cfg)

    task_scores: list[FewShotTaskScore] = []
    with Progress(console=console) as progress:
        pb = progress.add_task("scoring", total=len(tasks))
        for task in tasks:
            shots = pick_shots(
                seeds, task_id=task["id"], n=args.n_shots, prefer_category=task["category"]
            )
            messages = assemble_few_shot_messages(task, shots, args.gap_tokens)
            try:
                response = target.chat(messages=messages)
            except Exception as e:
                console.print(f"\n[red]{task['id']} target call failed: {e}[/red]")
                progress.advance(pb)
                continue

            grade = grader.grade(task["expected_behavior"], response)
            task_scores.append(
                FewShotTaskScore(
                    task_id=task["id"],
                    category=task["category"],
                    score=grade.score,
                    correctness=grade.correctness,
                    meta_awareness=grade.meta_awareness,
                    response_excerpt=response[:400].replace("\n", " "),
                    judge_reasoning=grade.raw,
                    seeds_used=[s["id"] for s in shots],
                )
            )
            progress.advance(pb)

    if not task_scores:
        console.print("[yellow]No tasks scored.[/yellow]")
        return

    # Aggregate
    by_category: dict[str, float] = {}
    for cat in CATEGORIES:
        cat_scores = [t.score for t in task_scores if t.category == cat]
        by_category[cat] = round(sum(cat_scores) / len(cat_scores), 2) if cat_scores else 0.0

    overall = round(sum(t.score for t in task_scores) / len(task_scores), 3)
    correctness_avg = round(sum(t.correctness for t in task_scores) / len(task_scores), 3)
    meta_avg = round(sum(t.meta_awareness for t in task_scores) / len(task_scores), 3)

    scorecard = FewShotScorecard(
        model=target_cfg.model,
        judge=judge_cfg.model,
        lhc_version="0.1",
        n_shots=args.n_shots,
        overall=overall,
        correctness_avg=correctness_avg,
        meta_avg=meta_avg,
        by_category=by_category,
        task_scores=task_scores,
    )

    output_path = (
        Path(args.output)
        if args.output
        else (
            Path(__file__).resolve().parent.parent
            / "results"
            / f"fewshot-{target_cfg.model.replace('/','_')}-n{args.n_shots}.json"
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(scorecard), indent=2))

    console.print(f"\n[bold]Few-shot LHC scorecard — {target_cfg.model} (n={args.n_shots})[/bold]")
    console.print(f"  overall:        {overall:.3f} / 2.000")
    console.print(f"  correctness:    {correctness_avg:.3f} / 1.000")
    console.print(f"  meta-awareness: {meta_avg:.3f} / 1.000  [bold]<<< the gate metric[/bold]")
    for cat, score in by_category.items():
        console.print(f"  {cat:<14} {score:.2f}")
    console.print(f"\n→ {output_path}")

    # Decision gate
    console.print("\n[bold]Decision gate (Stage 1.2):[/bold]")
    if meta_avg >= 0.65:
        console.print(f"  [green]PASS[/green]  meta_awareness {meta_avg:.3f} ≥ 0.65")
        console.print("  → seeds teach the right behavior, proceed to Stage 1.3 (scale to ~2k)")
    else:
        console.print(f"  [red]FAIL[/red]  meta_awareness {meta_avg:.3f} < 0.65")
        console.print("  → redesign seeds before generating synthetic data at scale")


if __name__ == "__main__":
    main()
