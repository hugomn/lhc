"""Thin OpenAI-compatible client used by the LHC harness.

Works against any endpoint that implements the chat completions API:
OpenAI, Anthropic (via proxy), Moonshot/Kimi, vLLM-served models, etc.

Reasoning models (Kimi K2.6, DeepSeek R1, OpenAI o-series) split their
output into a hidden `reasoning_content` channel and a final `content`
channel. With a tight `max_tokens` budget the reasoning consumes the
entire budget and `content` arrives empty. Two mitigations are wired here:

  - default `max_tokens` is large enough to comfortably hold both
  - the client falls back to `reasoning_content` when `content` is empty,
    so the harness can grade what the model actually produced
"""

from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI


@dataclass(frozen=True)
class ModelConfig:
    model: str
    base_url: str
    api_key: str
    # Reasoning models burn thousands of tokens on the hidden CoT before
    # emitting any content. 16k keeps long reasoning + a substantive answer.
    max_tokens: int = 16384
    temperature: float = 1.0  # K2.6 and several reasoning-class models reject anything else


class Client:
    """Minimal wrapper that hides the OpenAI SDK from the rest of the harness."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def chat(self, messages: list[dict[str, str]], tools: list[dict] | None = None) -> str:
        """Send a single chat completion and return the assistant text.

        Tools are accepted but tool-call handling is the runner's job, not the
        client's — this stays a thin transport layer.

        Falls back to `reasoning_content` when `content` is empty so reasoning
        models that exhaust the token budget mid-thought still surface output
        to the grader.
        """
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=messages,
            tools=tools,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        )
        msg = response.choices[0].message
        content = msg.content or ""
        if not content:
            # Reasoning models often expose this attribute; OpenAI SDK passes
            # through unknown fields via __dict__ on the message.
            content = getattr(msg, "reasoning_content", "") or ""
        return content
