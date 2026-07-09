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
        self._show_cache: dict[str, dict[str, Any]] = {}  # /api/show responses

    def list_models(self) -> list[str]:
        resp = requests.get(f"{self.host}/api/tags", timeout=self.timeout)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]

    def list_models_info(self) -> list[dict[str, str]]:
        """Names + display metadata from /api/tags (no extra round-trips)."""
        resp = requests.get(f"{self.host}/api/tags", timeout=self.timeout)
        resp.raise_for_status()
        out: list[dict[str, str]] = []
        for m in resp.json().get("models", []):
            details = m.get("details") or {}
            info: dict[str, str] = {"name": m["name"]}
            if details.get("parameter_size"):
                info["size"] = details["parameter_size"]
            if details.get("quantization_level"):
                info["quant"] = details["quantization_level"]
            out.append(info)
        return out

    def _show(self, model: str) -> dict[str, Any]:
        """The /api/show response for a model, cached (capabilities + model_info)."""
        if model not in self._show_cache:
            try:
                resp = requests.post(
                    f"{self.host}/api/show", json={"model": model}, timeout=self.timeout
                )
                resp.raise_for_status()
                self._show_cache[model] = resp.json() or {}
            except Exception:  # unknown -> empty (callers assume capable)
                self._show_cache[model] = {}
        return self._show_cache[model]

    def capabilities(self, model: str) -> set[str]:
        """Capability tags from /api/show (e.g. completion, vision, tools), cached."""
        return set(self._show(model).get("capabilities", []))

    def max_context(self, model: str) -> int | None:
        """The model's trained context window from /api/show model_info.

        The key is architecture-prefixed (e.g. ``gemma3.context_length``), so
        match on the suffix.
        """
        info = self._show(model).get("model_info") or {}
        for key, value in info.items():
            if key.endswith(".context_length") and isinstance(value, int):
                return value
        return None

    def chat(
        self,
        messages: list[Message],
        *,
        model: str,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        stream: bool = True,
        num_ctx: int | None = None,
    ) -> Iterator[ChatChunk]:
        options: dict[str, Any] = {"temperature": temperature}
        if num_ctx:
            # Without this Ollama runs the model at ITS default context (often
            # 4k) and silently truncates long conversations.
            options["num_ctx"] = num_ctx
        payload: dict[str, Any] = {
            "model": model,
            "messages": [m.to_wire() for m in messages],
            "stream": stream,
            "options": options,
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
