"""LHC main runner — load tasks, query model, grade, write scorecard.

Usage:
    python -m evals.runners.lhc \\
        --provider moonshot \\
        --judge-provider anthropic \\
        --output evals/results/kimi-k2-baseline.json
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

# Load .env at module import — keeps every CLI invocation auto-keyed.
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

console = Console()

TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"
CATEGORIES = ("state_recall", "commitment", "resumption")

# Default gap size. Each task can override via `gap_tokens` in its YAML.
DEFAULT_GAP_TOKENS = 6000


@dataclass
class TaskScore:
    task_id: str
    category: str
    score: int  # 0..2 (correctness + meta_awareness), or -1 if unscored
    correctness: int = 0
    meta_awareness: int = 0
    response_excerpt: str = ""  # first 400 chars — for human spot-check
    judge_reasoning: str = ""


@dataclass
class Scorecard:
    model: str
    lhc_version: str
    overall: float
    by_category: dict[str, float]
    task_scores: list[TaskScore] = field(default_factory=list)


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


def run_task(client: Client, task: dict, gap_override: int | None = None) -> tuple[str, int]:
    """Send a task's full message sequence (setup → gap → probe).

    Returns (response_text, actual_gap_token_count).
    """
    messages = list(task.get("setup", []))

    # CLI override wins; else per-task `gap_tokens`; else DEFAULT_GAP_TOKENS.
    target = gap_override if gap_override is not None else task.get("gap_tokens", DEFAULT_GAP_TOKENS)
    gap = generate_gap(target_tokens=target, seed=hash(task["id"]) & 0xFFFFFFFF)
    messages.extend(gap.messages)

    messages.extend(task.get("probe", []))
    return client.chat(messages=messages, tools=task.get("tools")), gap.estimated_tokens


PROVIDER_DEFAULTS = {
    "moonshot": {
        "model": os.environ.get("MOONSHOT_MODEL", "kimi-k2.6"),
        "base_url": os.environ.get("MOONSHOT_BASE_URL", "https://api.moonshot.ai/v1"),
        "api_key_env": "MOONSHOT_API_KEY",
    },
    "openai": {
        "model": "gpt-5",
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "api_key_env": "OPENAI_API_KEY",
    },
    "anthropic": {
        # Default to Opus 4.7 — Anthropic's recommendation for hardest grading
        # tasks as of May 2026, including judge-as-grader. Sonnet 4.6 is the
        # cheaper alternative ($3/$15 vs $5/$25 MTok); pick via --judge-model
        # if cost matters more than judge quality on a given run.
        "model": os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7"),
        "base_url": os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "deepseek": {
        # Default to deepseek-v4-pro — legacy "deepseek-chat" / "deepseek-reasoner"
        # ids retire 2026-07-24.
        "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro"),
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "slowlit": {
        "model": os.environ.get("SLOWLIT_MODEL", "ember-v0.1"),
        "base_url": os.environ.get("SLOWLIT_BASE_URL", "http://localhost:8080/v1"),
        "api_key_env": "SLOWLIT_API_KEY",
        # Qwen3 (and Ember v0.1, derived from it) is a thinking model that
        # emits <think>...</think> blocks by default. /no_think suppresses
        # that for clean comparison against non-reasoning baselines.
        # Override via SLOWLIT_SYSTEM_PREFIX="" if you want to keep think mode.
        "system_prompt_prefix": os.environ.get("SLOWLIT_SYSTEM_PREFIX", "/no_think"),
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LHC eval suite.")
    parser.add_argument(
        "--provider",
        choices=list(PROVIDER_DEFAULTS),
        help="shortcut for --model/--base-url/--api-key from .env (e.g. moonshot)",
    )
    parser.add_argument("--model", help="model name (overrides --provider default)")
    parser.add_argument("--base-url", help="OpenAI-compatible base URL (overrides --provider default)")
    parser.add_argument("--api-key", help="overrides any provider default key")
    parser.add_argument(
        "--judge-provider",
        choices=list(PROVIDER_DEFAULTS),
        default="deepseek",
        help="judge provider for grading (default: deepseek)",
    )
    parser.add_argument("--judge-model", help="judge model name (overrides judge-provider default)")
    parser.add_argument("--judge-base-url")
    parser.add_argument("--judge-api-key")
    parser.add_argument(
        "--output",
        default=None,
        help="path to write scorecard JSON (default: evals/results/<model>.json)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="run only the first N tasks (for dry runs / debugging)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the assembled messages for the first task and exit (no API calls)",
    )
    parser.add_argument(
        "--gap-tokens",
        type=int,
        default=None,
        help="override the gap size for every task (sweep coherence cliff without editing YAML)",
    )
    args = parser.parse_args()

    # Resolve target model from --provider if used; explicit flags win.
    args.system_prompt_prefix = ""
    if args.provider:
        defaults = PROVIDER_DEFAULTS[args.provider]
        args.model = args.model or defaults["model"]
        args.base_url = args.base_url or defaults["base_url"]
        args.api_key = args.api_key or os.environ.get(defaults["api_key_env"], "")
        args.system_prompt_prefix = defaults.get("system_prompt_prefix", "")

    # Resolve judge similarly.
    judge_defaults = PROVIDER_DEFAULTS[args.judge_provider]
    args.judge_model = args.judge_model or judge_defaults["model"]
    args.judge_base_url = args.judge_base_url or judge_defaults["base_url"]
    args.judge_api_key = args.judge_api_key or os.environ.get(judge_defaults["api_key_env"], "")

    if not args.model or not args.base_url:
        console.print(
            "[red]Need --provider OR (--model AND --base-url). "
            "Run with --help for options.[/red]"
        )
        return

    if not args.api_key:
        console.print(
            f"[red]No API key for target. Set the env var in .env or pass --api-key.[/red]"
        )
        return

    tasks = load_tasks()
    if not tasks:
        console.print("[yellow]No tasks found in evals/tasks/. Add task YAML files first.[/yellow]")
        return

    if args.limit:
        tasks = tasks[: args.limit]
        console.print(f"[dim]Limited to first {len(tasks)} task(s).[/dim]")

    if args.dry_run:
        console.print("[bold]Dry run — assembled messages for first task:[/bold]\n")
        first = tasks[0]
        gap_target = args.gap_tokens if args.gap_tokens is not None else first.get(
            "gap_tokens", DEFAULT_GAP_TOKENS
        )
        gap = generate_gap(target_tokens=gap_target, seed=hash(first["id"]) & 0xFFFFFFFF)
        all_msgs = list(first.get("setup", [])) + gap.messages + list(first.get("probe", []))
        for i, m in enumerate(all_msgs):
            console.print(f"[cyan]{i:02d} {m['role']:>10}[/cyan] | {m['content'][:80]}")
        console.print(
            f"\n[dim]{len(all_msgs)} messages, ~{gap.estimated_tokens} gap tokens.[/dim]"
        )
        return

    target = Client(
        ModelConfig(
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            system_prompt_prefix=args.system_prompt_prefix,
        )
    )

    # Judge is optional — if no key set, we skip grading and dump raw responses
    # so the human can eyeball them. Useful first time we run against a new
    # model and have not yet validated the harness end-to-end.
    grader: Grader | None = None
    if args.judge_api_key:
        grader = Grader(
            ModelConfig(
                model=args.judge_model,
                base_url=args.judge_base_url,
                api_key=args.judge_api_key,
            )
        )
    else:
        console.print(
            "[yellow]No judge API key — recording raw responses, no scoring.[/yellow]"
        )

    task_scores: list[TaskScore] = []
    with Progress(console=console) as progress:
        task_pb = progress.add_task(f"scoring {args.model}", total=len(tasks))
        for task in tasks:
            try:
                response, actual_gap = run_task(target, task, gap_override=args.gap_tokens)
            except Exception as e:
                console.print(f"\n[red]Task {task['id']} failed: {e}[/red]")
                progress.advance(task_pb)
                continue

            excerpt = response[:400].replace("\n", " ")

            if grader:
                grade = grader.grade(task["expected_behavior"], response)
                task_scores.append(
                    TaskScore(
                        task_id=task["id"],
                        category=task["category"],
                        score=grade.score,
                        correctness=grade.correctness,
                        meta_awareness=grade.meta_awareness,
                        response_excerpt=excerpt,
                        judge_reasoning=grade.raw,
                    )
                )
            else:
                # No judge — record -1 as "not scored" so we can still inspect
                task_scores.append(
                    TaskScore(
                        task_id=task["id"],
                        category=task["category"],
                        score=-1,
                        response_excerpt=excerpt,
                    )
                )

            progress.advance(task_pb)

    # Aggregate (skip -1 unscored entries)
    scored = [t for t in task_scores if t.score >= 0]
    by_category: dict[str, float] = {}
    for cat in CATEGORIES:
        cat_scores = [t.score for t in scored if t.category == cat]
        by_category[cat] = round(sum(cat_scores) / len(cat_scores), 2) if cat_scores else 0.0

    overall = round(sum(t.score for t in scored) / len(scored), 2) if scored else 0.0

    scorecard = Scorecard(
        model=args.model,
        lhc_version="0.1",
        overall=overall,
        by_category=by_category,
        task_scores=task_scores,
    )

    output_path = Path(args.output) if args.output else (
        Path(__file__).resolve().parent.parent / "results" / f"{args.model.replace('/', '_')}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(asdict(scorecard), f, indent=2)

    # Per-dimension aggregates — the rubric is now two binaries averaged
    # independently, plus their sum. Both views are useful: combined gives
    # the headline LHC score; the split tells us *which* dimension the
    # model is failing on.
    if scored:
        avg_correct = sum(t.correctness for t in scored) / len(scored)
        avg_meta = sum(t.meta_awareness for t in scored) / len(scored)
    else:
        avg_correct = avg_meta = 0.0

    console.print(f"\n[bold]LHC v0.1 scorecard — {args.model}[/bold]")
    if grader:
        console.print(f"  overall:        [bold]{overall:.2f}[/bold] / 2.00")
        console.print(f"  correctness:    {avg_correct:.2f} / 1.00")
        console.print(f"  meta-awareness: {avg_meta:.2f} / 1.00")
        for cat, score in by_category.items():
            console.print(f"  {cat:<14} {score:.2f}")
    else:
        console.print("  [dim](unscored — no judge API key set)[/dim]")
    console.print(f"\n→ written to {output_path}")

    # Always print task-level results so the human sees what happened
    console.print("\n[bold]Per-task:[/bold]")
    for t in task_scores:
        if t.score >= 0:
            tag = f"[bold]{t.correctness}/{t.meta_awareness}[/bold]"
        else:
            tag = "[dim]—/—[/dim]"
        console.print(f"  {tag}  {t.task_id} ({t.category})")
        if t.response_excerpt:
            console.print(f"       [dim]{t.response_excerpt[:150]}…[/dim]")


if __name__ == "__main__":
    main()
