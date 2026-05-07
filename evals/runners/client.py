"""Thin OpenAI-compatible client used by the LHC harness.

Works against any endpoint that implements the chat completions API:
OpenAI, Anthropic (via proxy), Moonshot/Kimi, vLLM-served models, etc.
"""

from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI


@dataclass(frozen=True)
class ModelConfig:
    model: str
    base_url: str
    api_key: str
    max_tokens: int = 4096
    temperature: float = 0.0


class Client:
    """Minimal wrapper that hides the OpenAI SDK from the rest of the harness."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def chat(self, messages: list[dict[str, str]], tools: list[dict] | None = None) -> str:
        """Send a single chat completion and return the assistant text.

        Tools are accepted but tool-call handling is the runner's job, not the
        client's — this stays a thin transport layer.
        """
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=messages,
            tools=tools,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        )
        return response.choices[0].message.content or ""
