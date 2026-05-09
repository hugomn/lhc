"""Stage 1.3 — synthetic dataset generation.

Generates LHC-shaped post-training examples for Ember v0.1 using the 50
hand-curated seeds in `data/seeds/v0.1.jsonl` as in-context examples for
a strong instruct model (Sonnet 4.6 by default).

Two-stage filtering:
  1. Regex pre-filter — drops examples missing the obvious meta-awareness
     markers ("per the", "from the [SESSION RESUME]", "standing rule").
  2. LLM judge filter — has the same model independently grade each
     surviving example on (correctness, meta_awareness). Drops anything
     not 1/1.

Output: `data/synthetic/v0.1/raw.jsonl` (every generation, even rejects),
plus `data/synthetic/v0.1/filtered.jsonl` (the kept examples).

Usage:
    python -m data.generate --target-count 2000 --batch-size 50
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")
console = Console()

DEFAULT_SEEDS_PATH = REPO_ROOT / "data" / "seeds" / "v0.1.jsonl"
DEFAULT_SYNTH_DIR = REPO_ROOT / "data" / "synthetic" / "v0.1"

CATEGORIES = ("state_recall", "commitment", "resumption")
DIFFICULTIES = ("seed", "easy", "medium", "hard")

GAP_PLACEHOLDER = "[~6,000 tokens of unrelated agent chatter elapses here]"

META_PATTERNS = [
    r"per (the|your|the standing|that|our)",
    r"from the start of",
    r"earlier in this",
    r"from the previous session",
    r"from the \[SESSION RESUME\]",
    r"\[session resume\]",
    r"standing (rule|commitment)",
    r"rule from earlier",
    r"the previous session",
    r"as you (set|defined|noted|established|asked)",
    r"per the (rule|convention|playbook|policy|tier|priority|focus|deadline|exception|standard)",
    r"flagging (a|an|the|inconsistency)",
    r"i('m| am) seeing an inconsistency",
    r"working memory",
    r"contradicts? (the|your)",
    r"based on (the|your|what)",
    r"(the )?exception you set",
]

GENERATOR_SYSTEM_PROMPT = """You are a senior post-training data author for a frontier-AI lab.

You generate training examples for a model called Ember that is being taught the "executor → narrator" behavior: the model should execute tasks correctly AND proactively name the source of any earlier instruction, standing rule, or session-resume payload it is acting on.

Each example you produce is one realistic LHC-shaped scenario, structured exactly like the seed examples shown to you. The scenario tests one of three coherence axes:
  - state_recall — agent recalls a fact, alias, threshold, or rule from earlier in the session
  - commitment — agent honors a standing commitment in the face of a softly contradictory new request
  - resumption — agent picks up a workflow across a session boundary using a [SESSION RESUME] payload

The target assistant turn (the LAST message in the example) MUST:
  1. Execute the requested task correctly. The agent does not refuse, defer, or improvise away from the task.
  2. Explicitly name the source of the earlier context — phrases like "per the standing rule from earlier", "from the [SESSION RESUME] payload", "the exception you set at the start of this session", "as you defined it earlier".
  3. When relevant, name the *why* (e.g. "this rule traces back to the 2024 outage", "Thread A is blocked on Thread B").
  4. Stay in the voice of a focused agent — terse, technical, action-oriented. No flowery preamble.

You will also output a JSON wrapper with metadata fields. Every output goes back as exactly one JSON object on one line, with the same shape as the seed examples:

{"id": "synth_NNNN", "category": "...", "difficulty": "...", "based_on": "<the source LHC task id you derived this from>", "axis": "executor_to_narrator", "messages": [...]}

Critical rules:
  - The user's penultimate message (just before the target assistant turn) must contain the literal placeholder "[~6,000 tokens of unrelated agent chatter elapses here]" to mark the long context gap. Do not generate fake gap content.
  - The example MUST be different from any of the seed examples shown. Do not paraphrase a seed; invent a new scenario in the same style.
  - Output exactly one JSON object. No prose. No markdown fences. No code blocks. No explanations."""


@dataclass(frozen=True)
class GenConfig:
    model: str
    base_url: str
    api_key: str
    target_count: int
    batch_size: int
    n_shots: int
    seed: int


def load_seeds(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def passes_regex(example: dict) -> tuple[bool, str]:
    """Cheap pre-filter. Catches obvious failures before we spend judge tokens."""
    msgs = example.get("messages", [])
    if not msgs:
        return False, "no messages"
    if msgs[-1].get("role") != "assistant":
        return False, "last message not assistant"
    final = msgs[-1].get("content", "")
    if len(final) < 80:
        return False, "final response too short"
    if not any(re.search(p, final, re.IGNORECASE) for p in META_PATTERNS):
        return False, "no meta-awareness markers"
    has_gap = any(GAP_PLACEHOLDER in m.get("content", "") for m in msgs)
    if not has_gap:
        return False, "missing gap placeholder"
    cat = example.get("category")
    if cat not in CATEGORIES:
        return False, f"bad category {cat!r}"
    diff = example.get("difficulty")
    if diff not in DIFFICULTIES:
        return False, f"bad difficulty {diff!r}"
    return True, "ok"


JUDGE_FILTER_PROMPT = """You are reviewing a synthetic post-training example for a model called Ember that is being taught the "executor → narrator" behavior.

Score the FINAL ASSISTANT MESSAGE in the example on two binary dimensions:

1. correctness ∈ {0, 1} — does the assistant execute the task that the most recent user message asked for? 1 if yes (paraphrasing OK, extra detail OK). 0 if it dodges the task, asks for clarification when none was needed, refuses without justification, or contradicts itself.

2. meta_awareness ∈ {0, 1} — does the assistant explicitly reference the earlier setup (the original instructions, the standing rule, or the [SESSION RESUME] payload)? 1 if it names the source, even briefly. 0 if it just answers without acknowledging where the constraint came from.

Return ONLY a JSON object on one line:
{"correctness": 0, "meta_awareness": 0}

No prose. No markdown."""


def call_generator(client: OpenAI, model: str, seeds: list[dict], n_shots: int, rng: random.Random) -> str:
    """One generator API call. Returns the raw assistant text."""
    shots = rng.sample(seeds, k=n_shots)

    target_cat = rng.choice(CATEGORIES)
    target_diff = rng.choice(DIFFICULTIES)

    user_lines: list[str] = []
    user_lines.append("Here are a few seed examples to learn the pattern from:\n")
    for i, s in enumerate(shots, 1):
        user_lines.append(f"--- SEED {i} ---")
        user_lines.append(json.dumps(s))
        user_lines.append("")
    user_lines.append("--- END SEEDS ---")
    user_lines.append("")
    user_lines.append(
        f"Now produce ONE new example. Category: {target_cat}. Difficulty: {target_diff}. "
        f"Pick a realistic professional scenario unrelated to the seeds. "
        f"Output exactly one JSON object on a single line, no surrounding text."
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": GENERATOR_SYSTEM_PROMPT},
            {"role": "user", "content": "\n".join(user_lines)},
        ],
        max_tokens=4096,
        temperature=1.0,
    )
    return response.choices[0].message.content or ""


def call_judge(client: OpenAI, model: str, example: dict) -> tuple[int, int] | None:
    """Has the judge model grade one synthetic example. Returns (correctness, meta) or None."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": JUDGE_FILTER_PROMPT},
            {"role": "user", "content": json.dumps(example)},
        ],
        max_tokens=64,
        temperature=1.0,
    )
    raw = (response.choices[0].message.content or "").strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        d = json.loads(raw)
        return int(d.get("correctness", 0)), int(d.get("meta_awareness", 0))
    except Exception:
        return None


def parse_one(raw: str) -> dict | None:
    """Pull the first valid JSON object out of the model's output."""
    s = raw.strip()
    s = s.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    # If model wrapped multiple things, take the first {...} that parses
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(s)):
        c = s[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start : i + 1])
                except Exception:
                    return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic LHC training examples.")
    parser.add_argument("--target-count", type=int, default=2000)
    parser.add_argument("--batch-size", type=int, default=50, help="how many to generate before rolling judge filter")
    parser.add_argument("--n-shots", type=int, default=5, help="seed examples shown per generation call")
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-attempts", type=int, default=None, help="hard cap on generator calls (default: 3x target_count)")
    parser.add_argument("--shard", default="main", help="shard name for parallel runs; output files are named raw-<shard>.jsonl, filtered-<shard>.jsonl")
    parser.add_argument("--seeds-path", default=str(DEFAULT_SEEDS_PATH), help="path to seeds JSONL")
    parser.add_argument("--out-dir", default=str(DEFAULT_SYNTH_DIR), help="output directory for raw and filtered shards")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    raw_path = out_dir / f"raw-{args.shard}.jsonl"
    filtered_path = out_dir / f"filtered-{args.shard}.jsonl"

    seeds = load_seeds(Path(args.seeds_path))
    if not seeds:
        console.print(f"[red]No seeds found at {args.seeds_path}[/red]")
        return 1

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
    if not api_key:
        console.print("[red]ANTHROPIC_API_KEY not set in .env[/red]")
        return 1

    client = OpenAI(api_key=api_key, base_url=base_url)

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    # Resume support — if raw.jsonl exists, count how many we already have
    raw_existing = 0
    if raw_path.exists():
        raw_existing = sum(1 for _ in raw_path.open())
    filtered_existing = 0
    if filtered_path.exists():
        filtered_existing = sum(1 for _ in filtered_path.open())

    if filtered_existing >= args.target_count:
        console.print(
            f"[green]Already have {filtered_existing} filtered examples (≥{args.target_count}). "
            f"Nothing to do.[/green]"
        )
        return 0

    console.print(
        f"[bold]Generating synthetic LHC examples[/bold]\n"
        f"  target: {args.target_count} (already have {filtered_existing} filtered, {raw_existing} raw)\n"
        f"  generator: {args.model}\n"
        f"  judge filter: {args.model}\n"
        f"  n_shots per call: {args.n_shots}\n"
        f"  batch size: {args.batch_size}\n"
    )

    raw_f = raw_path.open("a", buffering=1)  # line-buffered append
    filt_f = filtered_path.open("a", buffering=1)

    needed = args.target_count - filtered_existing
    max_attempts = args.max_attempts or (args.target_count * 3)
    attempts = 0
    parse_failures = 0
    regex_failures = 0
    judge_failures = 0
    accepted = 0
    next_id = filtered_existing

    started = time.time()
    while accepted < needed and attempts < max_attempts:
        try:
            raw = call_generator(client, args.model, seeds, args.n_shots, rng)
        except Exception as e:
            console.print(f"[yellow]generator call error: {e} — backing off 5s[/yellow]")
            time.sleep(5)
            attempts += 1
            continue
        attempts += 1

        ex = parse_one(raw)
        if ex is None:
            parse_failures += 1
            raw_f.write(json.dumps({"_parse_error": True, "raw": raw[:500]}) + "\n")
            if attempts % 25 == 0:
                _print_status(attempts, accepted, needed, parse_failures, regex_failures, judge_failures, started)
            continue

        # Save raw output regardless of whether it passes filter
        raw_f.write(json.dumps(ex) + "\n")

        ok, reason = passes_regex(ex)
        if not ok:
            regex_failures += 1
            if attempts % 25 == 0:
                _print_status(attempts, accepted, needed, parse_failures, regex_failures, judge_failures, started)
            continue

        # Judge filter — gate examples on Sonnet's own grading of them
        try:
            judged = call_judge(client, args.model, ex)
        except Exception as e:
            console.print(f"[yellow]judge call error: {e} — counted as judge failure[/yellow]")
            judge_failures += 1
            continue
        if judged is None:
            judge_failures += 1
            continue
        c, m = judged
        if c != 1 or m != 1:
            judge_failures += 1
            if attempts % 25 == 0:
                _print_status(attempts, accepted, needed, parse_failures, regex_failures, judge_failures, started)
            continue

        # Passed. Stamp a synth id and write to the filtered file.
        next_id += 1
        ex["id"] = f"synth_{next_id:04d}"
        filt_f.write(json.dumps(ex) + "\n")
        accepted += 1
        if accepted % args.batch_size == 0:
            _print_status(attempts, accepted, needed, parse_failures, regex_failures, judge_failures, started)

    raw_f.close()
    filt_f.close()

    elapsed = time.time() - started
    console.print(
        f"\n[bold green]Done.[/bold green] "
        f"accepted={accepted} attempts={attempts} elapsed={elapsed:.0f}s\n"
        f"parse_fail={parse_failures} regex_fail={regex_failures} judge_fail={judge_failures}\n"
        f"yield: {accepted}/{attempts} = {(accepted/attempts*100 if attempts else 0):.1f}%\n"
        f"→ {filtered_path}"
    )
    return 0


def _print_status(attempts: int, accepted: int, needed: int, p: int, r: int, j: int, started: float) -> None:
    elapsed = time.time() - started
    rate = accepted / elapsed * 60 if elapsed > 0 else 0
    eta = (needed - accepted) / rate if rate > 0 else 0
    console.print(
        f"  attempts={attempts} kept={accepted}/{needed} "
        f"(parse={p} regex={r} judge={j}) "
        f"yield={accepted/max(1,attempts)*100:.0f}% "
        f"rate={rate:.0f}/min eta={eta:.0f}min"
    )


if __name__ == "__main__":
    sys.exit(main())
