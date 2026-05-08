"""Data preparation entry point.

Skeleton — actual generation, anonymization, and merge logic land in
follow-up commits as the dataset spec is finalized.
"""

from __future__ import annotations

import argparse
import sys


def cmd_synthetic(args: argparse.Namespace) -> int:
    raise NotImplementedError(
        "synthetic data generation: pending dataset spec finalization. "
        "See data/README.md for the planned pipeline."
    )


def cmd_traces(args: argparse.Namespace) -> int:
    raise NotImplementedError(
        "trace anonymization: pending. Real traces live in data/traces/ "
        "and are gitignored."
    )


def cmd_merge(args: argparse.Namespace) -> int:
    raise NotImplementedError("merge/split: pending dataset spec finalization.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ember data preparation pipeline.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_synth = sub.add_parser("synthetic", help="generate synthetic LHC training examples")
    p_synth.add_argument("--base-model", required=True)
    p_synth.add_argument("--target-count", type=int, default=20_000)
    p_synth.add_argument("--output", required=True)
    p_synth.set_defaults(func=cmd_synthetic)

    p_traces = sub.add_parser("traces", help="anonymize raw agent traces")
    p_traces.add_argument("--input", required=True)
    p_traces.add_argument("--output", required=True)
    p_traces.set_defaults(func=cmd_traces)

    p_merge = sub.add_parser("merge", help="merge sources, dedupe, split")
    p_merge.add_argument("--synthetic", required=True)
    p_merge.add_argument("--traces")
    p_merge.add_argument("--output", required=True)
    p_merge.set_defaults(func=cmd_merge)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
