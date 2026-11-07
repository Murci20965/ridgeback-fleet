"""A thin OpenRouter client. It runs server-side only; the key never reaches the browser."""

from __future__ import annotations

import os
from typing import Any, Protocol

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Tried in order. OpenRouter moves to the next on downtime or rate limits.
DEFAULT_MODELS = ("anthropic/claude-haiku-5.5", "anthropic/claude-sonnet-5.5")
MAX_OUTPUT_TOKENS = 700
TIMEOUT_SECONDS = 30.0


class LLMError(Exception):
    """A failed model call. `message` is safe to show to the user."""

    def __init__(self, message: str, log_detail: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.log_detail = log_detail


class LLMClient(Protocol):
    def complete(self, messages: list[dict], tools: list[dict]) -> dict[str, Any]: ...


class OpenRouterClient:
    def __init__(self, models: tuple[str, ...] | None = None) -> None:
        configured = os.environ.get("OPENROUTER_MODELS")
        self.models = models or (tuple(configured.split(",")) if configured else DEFAULT_MODELS)

    def complete(self, messages: list[dict], tools: list[dict]) -> dict[str, Any]:
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise LLMError("The assistant isn't configured yet.", "OPENROUTER_API_KEY is not set")
        try:
            response = httpx.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "HTTP-Referer": os.environ.get("APP_URL", "http://localhost:3000"),
                    "X-OpenRouter-Title": "Ridgeback Fleet",
                },
                json={
                    "models": list(self.models),
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": 0,
                    "max_tokens": MAX_OUTPUT_TOKENS,
                },
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException as exc:
            raise LLMError("The assistant took too long. Try again.", str(exc)) from exc
        except httpx.HTTPError as exc:
            raise LLMError("Couldn't reach the assistant. Try again.", str(exc)) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise LLMError(
                "The assistant is unavailable right now. Try again shortly.",
                f"status {response.status_code}: not JSON",
            ) from exc

        # A provider can fail after a 200, so the body is checked as well as the status.
        error = body.get("error")
        if response.status_code >= 400 or error:
            code = (error or {}).get("code", response.status_code)
            detail = f"status {response.status_code}: {(error or {}).get('message', '')}"
            if code == 429:
                raise LLMError("The assistant is busy. Try again in a minute.", detail)
            if code in (402, 403):
                raise LLMError("The assistant has reached its usage limit.", detail)
            raise LLMError("The assistant is unavailable right now. Try again shortly.", detail)

        choices = body.get("choices") or []
        if not choices:
            raise LLMError("The assistant returned nothing. Try again.", "no choices in response")
        return {
            "message": choices[0]["message"],
            "model": body.get("model"),
            "usage": body.get("usage") or {},
        }
