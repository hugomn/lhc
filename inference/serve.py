"""Production server wrapper around vLLM.

Adds auth, rate limiting, and request logging on top of vLLM's OpenAI
compatible server. Skeleton — auth and rate limiting land before the
public endpoint goes live.
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve Ember via vLLM.")
    parser.add_argument("--model", required=True, help="HF repo or local path")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    raise NotImplementedError(
        f"vLLM server wrapper not yet implemented. For now run vLLM directly:\n"
        f"  vllm serve {args.model} --host {args.host} --port {args.port}\n"
        f"Auth + rate limiting layer lands before the public api.cinderlabs.ai endpoint."
    )


if __name__ == "__main__":
    sys.exit(main())
