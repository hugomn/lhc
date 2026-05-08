"""Verbose single-task tracer — for human inspection of one full LHC run.

Prints, for one task:
  1. The exact messages sent to the target model
  2. The raw response (content + reasoning_content if any)
  3. The exact judge prompt
  4. The raw judge response
  5. The final parsed scores

Use this when you want to understand what the harness is actually doing,
or when a result looks weird and you need to see every step.

Usage:
    python -m evals.runners.trace --task state_recall_001 --provider moonshot
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from .client import Client, ModelConfig
from .gap import generate_gap
from .grader import JUDGE_SYSTEM_PROMPT, _parse_judge_json
from .lhc import PROVIDER_DEFAULTS, TASKS_DIR

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
console = Console()


def find_task(task_id: str) -> dict | None:
    for path in TASKS_DIR.rglob("*.yaml"):
        with path.open() as f:
            t = yaml.safe_load(f)
        if t.get("id") == task_id:
            return t
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Trace a single LHC task end-to-end.")
    parser.add_argument("--task", required=True, help="task id, e.g. state_recall_001")
    parser.add_argument("--provider", default="moonshot")
    parser.add_argument("--judge-provider", default="moonshot")
    parser.add_argument("--gap-tokens", type=int, default=6000)
    args = parser.parse_args()

    task = find_task(args.task)
    if task is None:
        console.print(f"[red]Task {args.task} not found.[/red]")
        return

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

    # ── Step 1: assemble messages ────────────────────────────
    console.print(Rule(f"[bold cyan]STEP 1 — assemble messages for {task['id']}[/bold cyan]"))
    setup = list(task.get("setup", []))
    gap = generate_gap(target_tokens=args.gap_tokens, seed=hash(task["id"]) & 0xFFFFFFFF)
    probe = list(task.get("probe", []))
    messages = setup + gap.messages + probe

    console.print(f"setup messages   : {len(setup)}")
    console.print(f"gap messages     : {len(gap.messages)}  (~{gap.estimated_tokens} tokens)")
    console.print(f"probe messages   : {len(probe)}")
    console.print(f"TOTAL messages   : {len(messages)}")

    # Show first/last few messages so you can see the structure
    console.print("\n[dim]First 3 messages (the setup):[/dim]")
    for m in messages[:3]:
        body = m["content"][:120].replace("\n", " ")
        console.print(f"  [{m['role']:>9}] {body}…")
    console.print("[dim]…\nLast 2 messages (the probe):[/dim]")
    for m in messages[-2:]:
        body = m["content"][:120].replace("\n", " ")
        console.print(f"  [{m['role']:>9}] {body}…")

    # ── Step 2: target model call ────────────────────────────
    console.print(Rule(f"[bold cyan]STEP 2 — call target model: {target_cfg.model}[/bold cyan]"))
    console.print(
        f"POST {target_cfg.base_url}/chat/completions\n"
        f"  model={target_cfg.model}  temp={target_cfg.temperature}  max_tokens={target_cfg.max_tokens}\n"
    )
    target = Client(target_cfg)
    response = target.chat(messages=messages)

    console.print(Panel(
        response[:2000] + ("…" if len(response) > 2000 else ""),
        title=f"target response ({len(response)} chars)",
        border_style="green",
    ))

    # ── Step 3: assemble grader prompt ───────────────────────
    console.print(Rule(f"[bold cyan]STEP 3 — assemble grader prompt[/bold cyan]"))
    grader_user_prompt = (
        f"EXPECTED BEHAVIOR:\n{task['expected_behavior']}\n\n"
        f"AGENT RESPONSE:\n{response}\n\n"
        f"Return the JSON object now."
    )
    console.print(Panel(
        JUDGE_SYSTEM_PROMPT.strip(),
        title="judge system prompt",
        border_style="dim",
    ))
    console.print(Panel(
        grader_user_prompt[:1200] + ("…" if len(grader_user_prompt) > 1200 else ""),
        title="judge user prompt (truncated)",
        border_style="dim",
    ))

    # ── Step 4: judge call ────────────────────────────
    console.print(Rule(f"[bold cyan]STEP 4 — call judge: {judge_cfg.model}[/bold cyan]"))
    console.print(
        f"POST {judge_cfg.base_url}/chat/completions\n"
        f"  model={judge_cfg.model}\n"
    )
    judge = Client(judge_cfg)
    judge_raw = judge.chat(messages=[
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": grader_user_prompt},
    ]).strip()

    console.print(Panel(
        judge_raw[:600] + ("…" if len(judge_raw) > 600 else ""),
        title=f"judge raw response ({len(judge_raw)} chars)",
        border_style="yellow",
    ))

    # ── Step 5: parse + final score ───────────────────────────
    console.print(Rule("[bold cyan]STEP 5 — parse + final score[/bold cyan]"))
    correctness, meta = _parse_judge_json(judge_raw)
    total = correctness + meta
    console.print(f"  correctness    : [bold]{correctness}[/bold] / 1")
    console.print(f"  meta-awareness : [bold]{meta}[/bold] / 1")
    console.print(f"  TOTAL          : [bold]{total}[/bold] / 2")


if __name__ == "__main__":
    main()
