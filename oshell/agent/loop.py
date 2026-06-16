"""The agent loop — the shell's beating heart.

Instead of a chat REPL with features bolted on, the model drives: each turn it
may emit text, call tools, read their results, and continue, until it produces
a final answer (or hits the safety cap). Capabilities are just registered
tools, so adding power never means touching this file.

Context management (``pin`` / ``exclude``) lives here as first-class state so
the TUI's context inspector can visualize and edit exactly what the model sees.
"""

from __future__ import annotations

from collections.abc import Iterator

from ..config import Config
from ..providers.base import LLMProvider, Message
from ..tools import ToolRegistry
from .events import (
    AgentEvent,
    LimitReached,
    TextDelta,
    ToolFinished,
    ToolStarted,
    TurnComplete,
)

DEFAULT_SYSTEM_PROMPT = (
    "You are Ollama Shell, a local-first assistant running entirely on the "
    "user's machine. You can call tools to read/write files, check the time, "
    "list models, and (if enabled) search the web. Prefer tools over guessing. "
    "Be concise."
)


class Agent:
    """Owns the conversation, the provider, and the tool registry."""

    def __init__(
        self,
        provider: LLMProvider,
        registry: ToolRegistry,
        config: Config,
        *,
        model: str | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ):
        self.provider = provider
        self.registry = registry
        self.config = config
        self.model = model or config.default_model
        self.messages: list[Message] = [Message(role="system", content=system_prompt)]
        # Context management: indices into ``self.messages``.
        self.pinned: set[int] = {0}  # system prompt is pinned by default
        self.excluded: set[int] = set()

    # ── context management ───────────────────────────────────────────────────
    def pin(self, index: int) -> None:
        self.pinned.add(index)
        self.excluded.discard(index)

    def exclude(self, index: int) -> None:
        if index in self.pinned:
            raise ValueError(f"message {index} is pinned; unpin before excluding")
        self.excluded.add(index)

    def _context(self) -> list[Message]:
        """The messages actually sent to the model (excluded ones dropped)."""
        return [m for i, m in enumerate(self.messages) if i not in self.excluded]

    # ── the loop ─────────────────────────────────────────────────────────────
    def send(self, user_text: str) -> Iterator[AgentEvent]:
        """Run one user turn to completion, yielding events as they happen."""
        self.messages.append(Message(role="user", content=user_text))
        tools = self.registry.specs()

        for _ in range(self.config.max_tool_iterations):
            assistant_text = ""
            tool_calls = []
            for chunk in self.provider.chat(
                self._context(),
                model=self.model,
                tools=tools or None,
                temperature=self.config.temperature,
            ):
                if chunk.content:
                    assistant_text += chunk.content
                    yield TextDelta(chunk.content)
                if chunk.tool_calls:
                    tool_calls.extend(chunk.tool_calls)

            # Record the assistant turn (text and/or tool requests).
            self.messages.append(
                Message(role="assistant", content=assistant_text, tool_calls=tool_calls)
            )

            if not tool_calls:
                yield TurnComplete(assistant_text)
                return

            # Execute each requested tool and feed results back as tool messages.
            for call in tool_calls:
                yield ToolStarted(call.name, call.arguments)
                result = self.registry.dispatch(call)
                self.messages.append(
                    Message(role="tool", content=result, tool_call_id=call.id)
                )
                yield ToolFinished(call.name, result)
            # ...then loop so the model can use those results.

        yield LimitReached(self.config.max_tool_iterations)
