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
from typing import Any

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


def build_system_prompt(
    registry: ToolRegistry, base: str = DEFAULT_SYSTEM_PROMPT, memory: Any = None
) -> str:
    """Compose a tool-aware system prompt.

    Small local models otherwise fall back to an "I'm an offline LLM with no
    internet" persona and refuse perfectly-doable requests. We therefore list
    the *actual* available tools and, when any reach the network, state plainly
    that the model is NOT disconnected and must use them. Stored memories are
    injected so the model remembers the user across sessions.
    """
    tools = registry.active()
    if not tools:
        return base
    listing = "\n".join(f"- {t.name}: {t.description}" for t in tools)
    prompt = f"{base}\n\nTools available to you (call them; do not invent results):\n{listing}"

    names = {t.name for t in tools}
    if "browser_open" in names:
        prompt += (
            "\n\nWeb strategy: to merely READ a page's text, use fetch_url (cheapest). For "
            "INTERACTIVE web tasks — logging in, clicking, filling forms, or dynamic apps "
            "like Gmail/dashboards — use the HIDDEN BROWSER tools (browser_open, "
            "browser_screenshot, browser_click, browser_type, browser_key): it runs "
            "off-screen (no display takeover). Open a URL, screenshot to see the rendered "
            "page, then click/type by the coordinates you see. Prefer the hidden browser "
            "over the desktop GUI for anything in a browser."
        )
    if "screenshot" in names:
        import platform

        os_name = platform.system()  # Darwin / Linux / Windows
        prompt += (
            "\n\nYou can control the desktop GUI (screenshot, gui_click, gui_type, gui_key), "
            "but PREFER the terminal: use run_command for anything achievable in a shell, and "
            "only use the GUI tools for genuine graphical tasks. When you do use the GUI, take a "
            "screenshot first to see the screen, act, then screenshot again to verify. "
            "If what the user wants isn't visible, OPEN it yourself and proceed — don't just "
            "report an empty screen. Launch apps with run_command (macOS: "
            "`open -a 'Google Chrome' <url>`; Windows: `start <url>`; Linux: `xdg-open <url>`), "
            "then screenshot again. "
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

    if "remember" in names:
        prompt += (
            "\n\nLong-term memory: when the user shares a durable preference or fact about "
            "themselves worth keeping for future sessions (their name, tools they use, how "
            "they like answers, ongoing projects), call remember(...) with one concise "
            "sentence. Don't store secrets/passwords or transient details unless asked."
        )
    if memory is not None:
        items = memory.recent(40)
        if items:
            facts = "\n".join(f"- {m['text']}" for m in items)
            prompt += f"\n\nThings you remember about the user (long-term memory):\n{facts}"
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
        memory: Any = None,
    ):
        self.provider = provider
        self.registry = registry
        self.config = config
        self.memory = memory  # MemoryStore (or None) — injected facts + remember tool
        self.model = model or config.default_model
        # Build a tool-aware prompt unless the caller supplies an explicit one.
        self._custom_prompt = system_prompt
        content = (
            system_prompt
            if system_prompt is not None
            else build_system_prompt(registry, memory=memory)
        )
        self.messages: list[Message] = [Message(role="system", content=content)]
        # Context management: indices into ``self.messages``.
        self.pinned: set[int] = {0}  # system prompt is pinned by default
        self.excluded: set[int] = set()

    def rebuild_system_prompt(self) -> None:
        """Refresh the system message after the registry changes (tools toggled,
        model switched) or memory updates, so the model has the current tools+facts."""
        if self._custom_prompt is None and self.messages and self.messages[0].role == "system":
            self.messages[0].content = build_system_prompt(self.registry, memory=self.memory)

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
