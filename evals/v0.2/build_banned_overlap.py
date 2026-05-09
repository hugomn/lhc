"""Build the LHC v0.2 banned-overlap manifest.

Background: an external review (2026-05-08) found that LHC v0.1 tasks were
heavily contaminated by training data. Every one of the 12 LHC v0.1 tasks
has 5-11 derivative `based_on` examples in `data/seeds/*` and corresponding
`data/synthetic/**/mlx_lora/train.jsonl`. Comparing Ember (trained on this
data) to other 8B models (not trained on it) on LHC v0.1 is not a fair
fight; the leaderboard claims are invalid until LHC v0.2 is built without
overlap.

This script extracts the contamination footprint from current training data
and writes a manifest that LHC v0.2 task authors must check their tasks
against. Output is `evals/v0.2/banned_overlap.json` with the schema:

    {
      "generated_at": "2026-05-09",
      "sources": [<list of files scanned>],
      "by_lhc_task": {
        "<lhc_task_id>": {
          "derivative_seed_ids": [...],
          "named_entities": [...],
          "distinctive_phrases": [...],
          "domain_shape": "...",
          "scenario_summary": "..."
        }, ...
      },
      "scenario_defining_entities": [...],   # union of top-15 per task
      "global_banned_scaffolding_phrases": [...]  # frame phrases the model has seen
    }

Re-run this whenever training data changes and BEFORE authoring any new LHC
task. Example (the v0.2 path can't be a Python module due to the dot, so run
as a script):

    python evals/v0.2/build_banned_overlap.py
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Files that contain training data for Ember. If a v0.2 task overlaps with
# any entity / phrase / scenario in these files, it leaks signal to Ember
# that other models do not have.
SOURCE_FILES = [
    REPO_ROOT / "data" / "seeds" / "v0.1.jsonl",
    REPO_ROOT / "data" / "seeds" / "v0.1.5.jsonl",
    REPO_ROOT / "data" / "synthetic" / "v0.1" / "mlx_lora" / "train.jsonl",
    REPO_ROOT / "data" / "synthetic" / "v0.1" / "mlx_lora" / "valid.jsonl",
    REPO_ROOT / "data" / "synthetic" / "v0.1.5" / "mlx_lora" / "train.jsonl",
    REPO_ROOT / "data" / "synthetic" / "v0.1.5" / "mlx_lora" / "valid.jsonl",
]

# Distinctive phrases used in LHC v0.1 task scaffolding. Any phrase that
# appears here AND appears verbatim in training data is a contamination
# vector: the model has been taught to recognize the LHC frame itself.
SCAFFOLDING_PHRASES = [
    "[SESSION RESUME]",
    "Working memory from previous session",
    "Standing rule for this session",
    "standing commitment",
    "pre-commitment",
    "Continue the original task",
    "Picking up where I left off",
    "[~6,000 tokens of unrelated agent chatter elapses here]",
]

# Named-entity extraction. We use a deliberately permissive set of patterns —
# false positives are cheap (we just over-ban), false negatives are expensive
# (an entity slips into v0.2 unflagged). Tune as we discover new patterns.
PROPER_NOUN_RE = re.compile(
    # Sequences of 1-3 Capitalized words, with allowance for hyphens, possessives,
    # and digits (e.g. "Acme Corp", "Maria Okonkwo", "PR #921", "Vertiv", "GPT-5",
    # "iter-700"). Excludes single common words like "Slack" / "Github" / "Friday"
    # via a stoplist below.
    r"\b("
    r"(?:[A-Z][a-zA-Z]{2,}(?:[-/][A-Z][a-zA-Z]+)*)"          # Capitalized word, optional hyphen-joined
    r"(?:\s+[A-Z][a-zA-Z]+){0,2}"                            # plus 0-2 more
    r")\b"
)

# Common-but-uninteresting Capitalized tokens that we don't want to ban.
# Adding to this list is fine; over-banning costs author hours during v0.2
# authoring.
ENTITY_STOPWORDS = {
    "Slack", "Github", "GitHub", "Linear", "Notion", "Postgres", "Redis",
    "Stripe", "Python", "Markdown", "Lorem", "Ipsum",
    # Days, months, common time refs
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
    "EOD", "EOW", "QA", "PR", "CI", "API", "URL", "JSON", "YAML", "SQL", "DB",
    "AWS", "GCP", "Azure", "S3", "EC2",
    # Generic role / title nouns that frequently appear capitalized
    "Senior", "Junior", "Engineer", "Manager", "Director", "Lead",
    # Generic protocol / cert nouns
    "TLS", "SSL", "OAuth", "OAuth2", "SAML", "SSO", "CORS",
    # Generic ack words
    "Acknowledged", "Done", "Got",
    # Other very common
    "User", "Assistant", "System", "TODO", "FIXME", "WIP",
    "Standing", "Continue", "Continuing", "Picking", "Reading", "Working",
    "Memory", "Session", "Thread",
    # Very common sentence-initial Capitalized words. These appeared in the
    # extracted "entity" lists because the regex grabs anything Capitalized
    # at the start of a sentence; they're not entities, just punctuation
    # artifacts. Banning them adds zero contamination signal but causes
    # large numbers of false-positive hits during v0.2 authoring checks.
    "The", "You", "Your", "We", "Our", "It", "Its", "He", "She", "They",
    "I", "Me", "My", "Mine",
    "This", "That", "These", "Those",
    "What", "When", "Where", "Which", "Who", "Why", "How",
    "Yes", "No", "Maybe", "Both", "Either", "Neither",
    "All", "Any", "Anything", "Everything", "Nothing", "Some", "Something",
    "Confirm", "Confirmed", "Confirms", "Confirming",
    "Per", "Above", "Below", "Before", "After", "During", "While",
    "Today", "Yesterday", "Tomorrow", "Now", "Later", "Earlier", "Soon",
    "Apply", "Reply", "Respond", "Send", "Give", "Take",
    "Quick", "Quickly", "Slow", "Slowly", "Fast", "Faster",
    "Just", "Only", "Even", "Also", "Still", "Yet", "Already",
    "Standard", "Default", "Normal", "Custom",
    "Missing", "Found", "Available", "Unavailable",
    "Post", "Posted", "Posting",  # 'Post' was hit because of "Incident Command Post"
    "Incident",  # generic noun, scenario words like "wildfire incident command" are caught via shapes instead
    "NOT", "AND", "OR", "ALL", "ANY", "ONLY",  # all-caps emphasis words
    # More common Capitalized verbs/nouns observed in the synth top-50 noise list:
    "Next", "Last", "Status", "Task", "Can", "Here", "There", "Once", "Twice",
    "For", "From", "Of", "On", "In", "At", "By", "With", "Without",
    "Holding", "Running", "Ready", "Executing", "Run", "Actions", "Action",
    "Note", "Notes", "Okay", "Let", "Lets", "Letting",
    "Understood", "Acknowledge", "Acknowledged",
    "Will", "Would", "Should", "Could", "Must", "Cannot", "Can't",
    "Draft", "Drafting", "Drafted", "Updated", "Update", "Updates",
    "Rule", "Rules", "Note", "Reminder",
    "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
    "First", "Second", "Third", "Fourth", "Last",
    "Pausing", "Continuing", "Resuming", "Picking",
    "Executing", "Holding", "Flagging", "Tagged", "Flagged",
    "Reply", "Send", "Take", "Give", "Use", "Used", "Using",
    # More noise words found during commitment-batch authoring check:
    "Hard", "Soft", "One", "Phase", "Section", "Looking", "New", "Old",
    "Looking", "Listening", "Watching", "Waiting", "Coming", "Going",
    "Right", "Left", "Open", "Closed", "Hold", "Holds",
    "Most", "Least", "More", "Less",
    "Each", "Every", "None",
    "After", "Before",  # already had Before/After but be safe
    "Since", "Until", "Through",
    "Including", "Excluding", "Considering",
    "Maybe", "Probably", "Possibly", "Likely",
    "Item", "Items", "Member", "Members",
    "Type", "Types", "Kind", "Kinds", "Sort", "Sorts",
    "End", "Ends", "Start", "Starts",
    # More noise found during resumption-batch authoring check:
    "Log", "Logged", "Logs", "Page", "Pages", "Cut", "Pick", "Picks", "Picking",
    "Pull", "Pulled", "Pulling", "Push", "Pushed", "Pushing",
    "Step", "Steps", "Stop", "Stops", "Run", "Ran", "Runs",
    "Proceeding", "Proceed", "Proceeds",
    "Remaining", "Remained", "Remains",
    "Resume", "Resumed", "Resumes",
    "Calling", "Called", "Calls", "Call",
    "Want", "Wants", "Wanted", "Need", "Needs", "Needed",
    "Decision", "Decisions", "Decided",
    "Selected", "Selecting", "Selects",
    "ETA", "ETAs", "PDF", "PDFs",
    "Picked", "Picks",  # already had Pick
    "Routing", "Routed", "Routes",
    "Not",  # all-caps emphasis already in stoplist; the title-case one too
    "Scale", "Scaled", "Scales", "Scaling",
    "Logging", "Develop", "Write", "Read",
    "Clean", "Filtered", "Otherwise", "Pausing", "Pausing",
    # 4-letter and longer common Capitalized words observed during contamination check
    "Both", "Either", "Neither",
    "UTC",  # timezone notation, frequent in agent transcripts but not scenario-defining
}


def extract_text(messages: list[dict]) -> str:
    """Concatenate all message contents into a single string for entity extraction."""
    return "\n".join(m.get("content", "") for m in messages)


def extract_entities(text: str) -> set[str]:
    """Return the set of distinct named entities found in `text`, minus stopwords."""
    out: set[str] = set()
    for m in PROPER_NOUN_RE.finditer(text):
        ent = m.group(1).strip()
        # Reject if it's just a stopword or only stopwords.
        tokens = re.split(r"[\s\-/]", ent)
        if all(t in ENTITY_STOPWORDS for t in tokens if t):
            continue
        # Reject standalone single-token stopwords
        if ent in ENTITY_STOPWORDS:
            continue
        out.add(ent)
    return out


def find_scaffolding_phrases(text: str) -> set[str]:
    """Return the subset of SCAFFOLDING_PHRASES that appear in `text`."""
    return {p for p in SCAFFOLDING_PHRASES if p in text}


# Common content-bearing lowercase bigrams/trigrams that the proper-noun regex
# can't catch but that are scenario-defining (e.g. "audit log", "AI Act",
# "data subject access request"). We curate these by hand from observed seed
# scenarios; extend as new seed scenarios are added.
DOMAIN_SHAPE_PHRASES = [
    # state_recall
    "database migration", "code-freeze", "Friday code-freeze",
    "page thresholds", "error_rate", "latency_p99", "on-call shift",
    "refund tool", "Enterprise tier", "refund-pending-review",
    # commitment
    "explicit approval", "production deploy", "deploy to production",
    "British English", "audit log pipeline", "24-hour soak", "staging soak",
    "PR reviewer", "senior reviewer", "junior reviewer",
    # resumption
    "[SESSION RESUME]", "Working memory", "Black Forest Labs", "BFL",
    "European AI Act", "AI Act", "GDPR", "DSAR", "data subject access request",
    "Redis to Postgres", "auth service", "schema migration",
    "datacenter UPS", "UPS systems", "Vertiv", "Eaton", "Schneider Electric",
    "Maria Okonkwo",
]


def find_domain_shapes(text: str) -> set[str]:
    """Return the subset of DOMAIN_SHAPE_PHRASES that appear (case-insensitive) in `text`."""
    text_lower = text.lower()
    return {p for p in DOMAIN_SHAPE_PHRASES if p.lower() in text_lower}


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> int:
    print("Building banned-overlap manifest…")
    print(f"  scanning {len(SOURCE_FILES)} source files")

    # Aggregator structures
    by_lhc_task: dict[str, dict] = defaultdict(
        lambda: {
            "derivative_seed_ids": set(),
            "named_entities": Counter(),
            "scaffolding_phrases": set(),
            "domain_shapes": set(),
            "first_user_msg_samples": [],
        }
    )
    # Synthetic training files are stripped of `based_on`. Aggregate them
    # under a synthetic bucket so authors see entities introduced by synth-
    # generation that aren't tied to a specific LHC task.
    synth_bucket = {
        "named_entities": Counter(),
        "scaffolding_phrases": set(),
        "domain_shapes": set(),
    }

    total = 0
    for path in SOURCE_FILES:
        records = load_records(path)
        if not records:
            print(f"  [skip] {path.relative_to(REPO_ROOT)} (missing or empty)")
            continue
        print(f"  [ok]   {path.relative_to(REPO_ROOT)}: {len(records)} records")
        total += len(records)

        for rec in records:
            text = extract_text(rec.get("messages", []))
            entities = extract_entities(text)
            scaffolding = find_scaffolding_phrases(text)
            shapes = find_domain_shapes(text)

            based_on = rec.get("based_on")
            if based_on:
                bucket = by_lhc_task[based_on]
                if rec.get("id"):
                    bucket["derivative_seed_ids"].add(rec["id"])
                for e in entities:
                    bucket["named_entities"][e] += 1
                bucket["scaffolding_phrases"].update(scaffolding)
                bucket["domain_shapes"].update(shapes)
                # First user message snippet (first 200 chars), for human spot-check
                first_user = next(
                    (m["content"][:200] for m in rec.get("messages", []) if m.get("role") == "user"),
                    "",
                )
                if len(bucket["first_user_msg_samples"]) < 3 and first_user:
                    bucket["first_user_msg_samples"].append(first_user)
            else:
                for e in entities:
                    synth_bucket["named_entities"][e] += 1
                synth_bucket["scaffolding_phrases"].update(scaffolding)
                synth_bucket["domain_shapes"].update(shapes)

    print(f"  total records scanned: {total}")
    print(f"  found {len(by_lhc_task)} LHC-task derivatives")

    # Build "scenario-defining entities" list: the union of the top-30 entities
    # per LHC-task bucket. This is the signal authors actually need — entities
    # tightly associated with one task family. Using a global frequency
    # threshold instead drowns the list in pronouns and SQL keywords. Top-30
    # (not top-15) catches lower-frequency but distinctive scenario names like
    # "Vertiv", "Eaton", "Magnify" that the obvious-overlap check would miss.
    scenario_entities: set[str] = set()
    for bucket in by_lhc_task.values():
        for e, _ in bucket["named_entities"].most_common(30):
            # additional cleanup: skip 1-token entities ≤2 chars (likely noise).
            # 3-char acronyms (BFL, ACL, ARR) are kept — they're often the
            # distinctive scenario name even when short.
            if " " not in e and "-" not in e and len(e) <= 2:
                continue
            scenario_entities.add(e)
    scenario_banned_entities = sorted(scenario_entities)
    print(f"  scenario-defining entities (top-30 per task, deduped): "
          f"{len(scenario_banned_entities)}")

    # Materialize the manifest
    out = {
        "generated_at": date.today().isoformat(),
        "schema_version": 1,
        "sources": [str(p.relative_to(REPO_ROOT)) for p in SOURCE_FILES if p.exists()],
        "total_records_scanned": total,
        "by_lhc_task": {},
        "synthetic_only_bucket": {
            "named_entities_top50": [
                e for e, _ in synth_bucket["named_entities"].most_common(50)
            ],
            "scaffolding_phrases": sorted(synth_bucket["scaffolding_phrases"]),
        },
        "scenario_defining_entities": scenario_banned_entities,
        "global_banned_scaffolding_phrases": sorted(
            set().union(*(b["scaffolding_phrases"] for b in by_lhc_task.values()))
            | synth_bucket["scaffolding_phrases"]
        ),
    }
    # Aggregate all domain shapes seen anywhere in training
    all_domain_shapes: set[str] = set()
    for bucket in by_lhc_task.values():
        all_domain_shapes.update(bucket["domain_shapes"])
    all_domain_shapes.update(synth_bucket["domain_shapes"])
    out["domain_shape_phrases_seen"] = sorted(all_domain_shapes)

    for tid, bucket in sorted(by_lhc_task.items()):
        out["by_lhc_task"][tid] = {
            "derivative_seed_ids": sorted(bucket["derivative_seed_ids"]),
            "derivative_count": len(bucket["derivative_seed_ids"]),
            # Top-30 entities for this task family — over-share, not under-share
            "named_entities_top30": [
                e for e, _ in bucket["named_entities"].most_common(30)
            ],
            "scaffolding_phrases": sorted(bucket["scaffolding_phrases"]),
            "domain_shapes": sorted(bucket["domain_shapes"]),
            "first_user_msg_samples": bucket["first_user_msg_samples"],
        }

    out_path = REPO_ROOT / "evals" / "v0.2" / "banned_overlap.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nManifest written to {out_path.relative_to(REPO_ROOT)}")
    print(f"  {len(out['by_lhc_task'])} per-LHC-task buckets")
    print(f"  {len(out['scenario_defining_entities'])} scenario-defining entities banned")
    print(f"  {len(out['global_banned_scaffolding_phrases'])} scaffolding phrases banned")
    print(f"  {len(out['domain_shape_phrases_seen'])} domain-shape phrases seen in training")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
