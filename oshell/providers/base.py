"""Provider-agnostic LLM interface.

The shell never talks to a backend directly; it talks to an ``LLMProvider``.
This is what lets the same agent loop and TUI run against Ollama today and an
OpenAI-compatible endpoint or MLX server tomorrow — exactly the multi-runtime
setup described in the workspace notes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    """A single chat message. ``tool_calls`` / ``tool_call_id`` carry tool-use."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    images: list[str] = field(default_factory=list)  # base64 for vision models

    def to_wire(self) -> dict[str, Any]:
        """Serialize to the dict shape Ollama/OpenAI chat APIs expect."""
        msg: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = [tc.to_wire() for tc in self.tool_calls]
        if self.images:
            msg["images"] = self.images
        return msg


@dataclass
class ToolCall:
    """A model's request to invoke a tool."""

    name: str
    arguments: dict[str, Any]
    id: str | None = None

    def to_wire(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.name, "arguments": self.arguments},
        }


@dataclass
class ChatChunk:
    """One streamed piece of a response.

    A stream yields many ``ChatChunk``s with ``content`` deltas, then a final
    chunk with ``done=True`` that may also carry ``tool_calls``.
    """

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    done: bool = False


class LLMProvider(ABC):
    """Minimal surface every backend must implement."""

    name: str = "base"

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        *,
        model: str,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        stream: bool = True,
    ) -> Iterator[ChatChunk]:
        """Stream a model response, optionally with tool definitions in scope."""

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return the model names available on this backend."""

    def health(self) -> bool:
        """Cheap reachability check; defaults to 'can we list models'."""
        try:
            self.list_models()
            return True
        except Exception:
            return False
