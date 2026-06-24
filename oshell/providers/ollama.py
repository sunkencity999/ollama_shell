"""Ollama backend implemented directly against its REST API.

We talk to ``/api/chat`` and ``/api/tags`` with ``requests`` (a light core
dependency) rather than pulling in the full ``ollama`` client. The chat
endpoint streams newline-delimited JSON; we translate each line into a
``ChatChunk``. Tool definitions are passed through verbatim — Ollama returns
``message.tool_calls`` for models that support function calling.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import requests

from .base import ChatChunk, LLMProvider, Message, ToolCall


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, host: str = "http://localhost:11434", timeout: float = 120.0):
        self.host = host.rstrip("/")
        self.timeout = timeout
        self._caps_cache: dict[str, set[str]] = {}

    def list_models(self) -> list[str]:
        resp = requests.get(f"{self.host}/api/tags", timeout=self.timeout)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]

    def capabilities(self, model: str) -> set[str]:
        """Capability tags from /api/show (e.g. completion, vision, tools), cached."""
        if model in self._caps_cache:
            return self._caps_cache[model]
        caps: set[str] = set()
        try:
            resp = requests.post(
                f"{self.host}/api/show", json={"model": model}, timeout=self.timeout
            )
            resp.raise_for_status()
            caps = set(resp.json().get("capabilities", []))
        except Exception:  # unknown -> empty (callers assume capable)
            caps = set()
        self._caps_cache[model] = caps
        return caps

    def chat(
        self,
        messages: list[Message],
        *,
        model: str,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        stream: bool = True,
    ) -> Iterator[ChatChunk]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [m.to_wire() for m in messages],
            "stream": stream,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools
            # Ollama does not stream partial tool calls; force a single response
            # so we get a complete tool_calls array in one shot.
            payload["stream"] = False

        resp = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            stream=payload["stream"],
            timeout=self.timeout,
        )
        resp.raise_for_status()

        if not payload["stream"]:
            yield _chunk_from_message(resp.json(), done=True)
            return

        for line in resp.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            yield _chunk_from_message(data, done=data.get("done", False))


def _chunk_from_message(data: dict[str, Any], *, done: bool) -> ChatChunk:
    """Translate one Ollama response object into a ChatChunk."""
    msg = data.get("message", {}) or {}
    tool_calls = [
        ToolCall(
            name=tc["function"]["name"],
            arguments=_parse_args(tc["function"].get("arguments", {})),
            id=tc.get("id"),
        )
        for tc in msg.get("tool_calls", []) or []
    ]
    return ChatChunk(content=msg.get("content", ""), tool_calls=tool_calls, done=done)


def _parse_args(args: Any) -> dict[str, Any]:
    """Tool-call arguments may arrive as a dict or a JSON string."""
    if isinstance(args, str):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return {}
    return args or {}
