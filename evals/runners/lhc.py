"""LHC main runner — load tasks, query model, grade, write scorecard.

Usage:
    python -m evals.runners.lhc \\
        --model ember-v0.1 \\
        --base-url https://api.cinderlabs.ai/v1 \\
        --api-key $CINDER_API_KEY \\
        --output evals/results/ember-v0.1.json
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml
from rich.console import Console
from rich.progress import Progress

from .client import Client, ModelConfig
from .grader import Grader

console = Console()

TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"
CATEGORIES = ("state_recall", "commitment", "resumption")


@dataclass
class TaskScore:
    task_id: str
    category: str
    score: int


@dataclass
class Scorecard:
    model: str
    lhc_version: str
    overall: float
    by_category: dict[str, float]
    task_scores: list[TaskScore]


def load_tasks() -> list[dict]:
    """Load every task YAML under evals/tasks/<category>/."""
    tasks = []
    for category in CATEGORIES:
        category_dir = TASKS_DIR / category
        if not category_dir.exists():
            continue
        for path in sorted(category_dir.glob("*.yaml")):
            with path.open() as f:
                tasks.append(yaml.safe_load(f))
    return tasks


def run_task(client: Client, task: dict) -> str:
    """Send a task's full message sequence to the model and collect the response.

    The setup, gap, and probe messages are concatenated into a single chat
    request — the gap exists to push the setup deep into context, so we do
    not split into separate calls.
    """
    messages = list(task.get("setup", []))
    messages.extend(task.get("gap_messages", []))
    messages.extend(task.get("probe", []))
    return client.chat(messages=messages, tools=task.get("tools"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LHC eval suite.")
    parser.add_argument("--model", required=True, help="model name to query")
    parser.add_argument("--base-url", required=True, help="OpenAI-compatible base URL")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    parser.add_argument("--judge-model", default="claude-sonnet-4-6")
    parser.add_argument("--judge-base-url", default="https://api.anthropic.com/v1")
    parser.add_argument("--judge-api-key", default=os.environ.get("ANTHROPIC_API_KEY", ""))
    parser.add_argument("--output", required=True, help="path to write scorecard JSON")
    args = parser.parse_args()

    target = Client(ModelConfig(model=args.model, base_url=args.base_url, api_key=args.api_key))
    grader = Grader(
        ModelConfig(model=args.judge_model, base_url=args.judge_base_url, api_key=args.judge_api_key)
    )

    tasks = load_tasks()
    if not tasks:
        console.print("[yellow]No tasks found in evals/tasks/. Add task YAML files first.[/yellow]")
        return

    task_scores: list[TaskScore] = []
    with Progress(console=console) as progress:
        task_pb = progress.add_task(f"scoring {args.model}", total=len(tasks))
        for task in tasks:
            response = run_task(target, task)
            grade = grader.grade(task["expected_behavior"], response)
            task_scores.append(
                TaskScore(task_id=task["id"], category=task["category"], score=grade.score)
            )
            progress.advance(task_pb)

    # Aggregate
    by_category: dict[str, float] = {}
    for cat in CATEGORIES:
        cat_scores = [t.score for t in task_scores if t.category == cat]
        by_category[cat] = round(sum(cat_scores) / len(cat_scores), 2) if cat_scores else 0.0

    overall = round(sum(t.score for t in task_scores) / len(task_scores), 2) if task_scores else 0.0

    scorecard = Scorecard(
        model=args.model,
        lhc_version="0.1",
        overall=overall,
        by_category=by_category,
        task_scores=task_scores,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(asdict(scorecard), f, indent=2)

    console.print(f"\n[bold]LHC v0.1 scorecard — {args.model}[/bold]")
    console.print(f"  overall: [bold]{overall:.2f}[/bold] / 4.00")
    for cat, score in by_category.items():
        console.print(f"  {cat}: {score:.2f}")
    console.print(f"\n→ written to {output_path}")


if __name__ == "__main__":
    main()
