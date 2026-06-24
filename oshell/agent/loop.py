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
    "You are Ollama Shell, a local-first assistant that runs on the user's "
    "machine but can act on the world through the tools listed below. "
    "Prefer calling a tool over guessing or declining. Be concise."
)


def build_system_prompt(registry: ToolRegistry, base: str = DEFAULT_SYSTEM_PROMPT) -> str:
    """Compose a tool-aware system prompt.

    Small local models otherwise fall back to an "I'm an offline LLM with no
    internet" persona and refuse perfectly-doable requests. We therefore list
    the *actual* available tools and, when any reach the network, state plainly
    that the model is NOT disconnected and must use them.
    """
    tools = registry.active()
    if not tools:
        return base
    listing = "\n".join(f"- {t.name}: {t.description}" for t in tools)
    prompt = f"{base}\n\nTools available to you (call them; do not invent results):\n{listing}"

    if any(t.name == "screenshot" for t in tools):
        import platform

        os_name = platform.system()  # Darwin / Linux / Windows
        prompt += (
            "\n\nYou can control the desktop GUI (screenshot, gui_click, gui_type, gui_key), "
            "but PREFER the terminal: use run_command for anything achievable in a shell, and "
            "only use the GUI tools for genuine graphical tasks. When you do use the GUI, take a "
            "screenshot first to see the screen, act, then screenshot again to verify. "
            f"This machine runs {os_name}; use OS-appropriate keys and paths "
            "(e.g. the super/meta key is Command on macOS, the Windows key on Windows)."
        )

    networked = [t.name for t in tools if not t.local_only]
    if networked:
        prompt += (
            "\n\nIMPORTANT: You are NOT a disconnected model — you have live internet "
            f"access through these tools: {', '.join(networked)}. Never tell the user you "
            "cannot access the internet, real-time information, or a specific website. When "
            "they ask for current facts, external information, documentation, or anything you "
            "are not certain of from memory, call web_search (then fetch_url to read a result) "
            "and answer from what you find."
            "\n\nGround every factual claim in actual tool output. Do NOT invent URLs, links, "
            "product pages, videos, prices, citations, or sources, and do not claim something "
            "is 'from your search results' unless it actually appears in a tool result. If a "
            "search returns nothing useful, say so plainly and offer to refine the query — "
            "never fabricate an answer to seem helpful."
        )
    return prompt


class Agent:
    """Owns the conversation, the provider, and the tool registry."""

    def __init__(
        self,
        provider: LLMProvider,
        registry: ToolRegistry,
        config: Config,
        *,
        model: str | None = None,
        system_prompt: str | None = None,
    ):
        self.provider = provider
        self.registry = registry
        self.config = config
        self.model = model or config.default_model
        # Build a tool-aware prompt unless the caller supplies an explicit one.
        self._custom_prompt = system_prompt
        content = system_prompt if system_prompt is not None else build_system_prompt(registry)
        self.messages: list[Message] = [Message(role="system", content=content)]
        # Context management: indices into ``self.messages``.
        self.pinned: set[int] = {0}  # system prompt is pinned by default
        self.excluded: set[int] = set()

    def rebuild_system_prompt(self) -> None:
        """Refresh the system message after the registry changes (tools toggled,
        model switched) so the model is told about the now-active tools."""
        if self._custom_prompt is None and self.messages and self.messages[0].role == "system":
            self.messages[0].content = build_system_prompt(self.registry)

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

    def _model_supports_tools(self) -> bool:
        """Whether the active model accepts tool definitions. Unknown -> assume yes."""
        try:
            caps = self.provider.capabilities(self.model)
        except Exception:
            caps = set()
        return (not caps) or ("tools" in caps)

    # ── the loop ─────────────────────────────────────────────────────────────
    def send(self, user_text: str, images: list[str] | None = None) -> Iterator[AgentEvent]:
        """Run one user turn to completion, yielding events as they happen.

        ``images`` are base64-encoded image data attached to the user message
        for vision-capable models (passed through to the backend verbatim).
        """
        self.messages.append(Message(role="user", content=user_text, images=images or []))
        # Capability-aware: only advertise tools to models that support them.
        # This keeps tools on for image turns with models that do both (e.g.
        # gemma3/4), but suppresses them for vision-only models (e.g. llava) that
        # 400 when tools are present — on any turn.
        tools = self.registry.specs() or None
        if tools and not self._model_supports_tools():
            tools = None

        for _ in range(self.config.max_tool_iterations):
            assistant_text = ""
            tool_calls = []
            for chunk in self.provider.chat(
                self._context(),
                model=self.model,
                tools=tools,
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
            # A tool may return images (e.g. a screenshot) — attach them so the
            # vision model can see them on the next round.
            for call in tool_calls:
                yield ToolStarted(call.name, call.arguments)
                result = self.registry.dispatch_full(call)
                self.messages.append(
                    Message(
                        role="tool",
                        content=result.text,
                        tool_call_id=call.id,
                        images=result.images,
                    )
                )
                yield ToolFinished(call.name, result.text)
            # ...then loop so the model can use those results.

        yield LimitReached(self.config.max_tool_iterations)
