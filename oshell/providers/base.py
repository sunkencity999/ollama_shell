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
class PullProgress:
    """One streamed step of a model download.

    ``total``/``completed`` are bytes for the layer currently downloading;
    either may be missing on bookkeeping steps ("verifying sha256", "success").
    """

    status: str = ""
    total: int | None = None
    completed: int | None = None

    @property
    def percent(self) -> float | None:
        """Layer progress 0–100, when byte counts are known."""
        if self.total and self.completed is not None:
            return 100.0 * self.completed / self.total
        return None


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
        num_ctx: int | None = None,
    ) -> Iterator[ChatChunk]:
        """Stream a model response, optionally with tool definitions in scope.

        ``num_ctx`` requests a context-window size (tokens) from backends that
        honor it per-request (Ollama). Backends that manage context server-side
        ignore it.
        """

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return the model names available on this backend."""

    def list_models_info(self) -> list[dict[str, str]]:
        """Model names plus cheap display metadata, when the backend has it.

        Each dict has at least ``name``; backends that know more (Ollama's
        /api/tags carries parameter size, quantization, and bytes on disk) add
        ``size``, ``quant``, and ``disk``. Used for badges in the model picker —
        callers must tolerate missing keys.
        """
        return [{"name": n} for n in self.list_models()]

    def capabilities(self, model: str) -> set[str]:
        """Return capability tags for a model (e.g. {"vision", "tools"}).

        Empty set means "unknown" — callers should assume the model supports
        whatever they need rather than disabling it. Backends that can introspect
        (Ollama) override this.
        """
        return set()

    def max_context(self, model: str) -> int | None:
        """The model's trained maximum context length (tokens), if known.

        ``None`` means "unknown" — callers fall back to a conservative default.
        Backends that can introspect (Ollama's /api/show) override this.
        """
        return None

    def supports_model_management(self) -> bool:
        """Whether this backend can pull and delete models.

        UIs use this to show or hide management affordances; the default
        methods below raise for backends that leave it False.
        """
        return False

    def pull_model(self, name: str) -> Iterator[PullProgress]:
        """Download a model onto the backend, yielding progress steps."""
        raise NotImplementedError(f"the {self.name} backend cannot pull models")

    def delete_model(self, name: str) -> None:
        """Remove a model from the backend."""
        raise NotImplementedError(f"the {self.name} backend cannot delete models")

    def loaded_models(self) -> list[dict[str, Any]]:
        """Models currently resident in memory: ``{name, size, size_vram, …}``.

        Backends that can't tell return an empty list (the vitals tile then
        shows "nothing loaded").
        """
        return []

    def health(self) -> bool:
        """Cheap reachability check; defaults to 'can we list models'."""
        try:
            self.list_models()
            return True
        except Exception:
            return False
