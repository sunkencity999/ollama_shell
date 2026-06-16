"""OpenAI-compatible backend (LM Studio, vLLM, llama.cpp server, etc.).

Many local runtimes expose the OpenAI ``/v1/chat/completions`` schema. This
provider lets the same shell drive any of them by pointing ``provider.host`` at
the server and (optionally) setting ``provider.api_key``.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import requests

from .base import ChatChunk, LLMProvider, Message, ToolCall


class OpenAICompatProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        host: str = "http://localhost:1234",
        api_key: str | None = None,
        timeout: float = 120.0,
    ):
        self.base = host.rstrip("/")
        # Allow either a bare host or a full ".../v1" base.
        if not self.base.endswith("/v1"):
            self.base += "/v1"
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def list_models(self) -> list[str]:
        resp = requests.get(f"{self.base}/models", headers=self._headers(), timeout=self.timeout)
        resp.raise_for_status()
        return [m["id"] for m in resp.json().get("data", [])]

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
            "temperature": temperature,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            payload["stream"] = stream = False  # collect tool calls in one response

        resp = requests.post(
            f"{self.base}/chat/completions",
            headers=self._headers(),
            json=payload,
            stream=stream,
            timeout=self.timeout,
        )
        resp.raise_for_status()

        if not stream:
            choice = resp.json()["choices"][0]["message"]
            yield ChatChunk(
                content=choice.get("content") or "",
                tool_calls=_parse_tool_calls(choice.get("tool_calls")),
                done=True,
            )
            return

        for line in resp.iter_lines():
            if not line or not line.startswith(b"data: "):
                continue
            body = line[len(b"data: "):]
            if body.strip() == b"[DONE]":
                yield ChatChunk(done=True)
                return
            delta = json.loads(body)["choices"][0]["delta"]
            yield ChatChunk(content=delta.get("content") or "")


def _parse_tool_calls(raw: Any) -> list[ToolCall]:
    out: list[ToolCall] = []
    for tc in raw or []:
        fn = tc.get("function", {})
        args = fn.get("arguments", "{}")
        try:
            parsed = json.loads(args) if isinstance(args, str) else (args or {})
        except json.JSONDecodeError:
            parsed = {}
        out.append(ToolCall(name=fn.get("name", ""), arguments=parsed, id=tc.get("id")))
    return out
