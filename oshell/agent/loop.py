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
    "\n\nNever announce an action and then stop. If you say you will search, "
    "fetch a page, write a file, or do anything else with a tool, CALL THAT "
    "TOOL in the same turn — do not end your reply with 'one moment', 'let me "
    "look that up', or 'I'll go do that' and no tool call. Either perform the "
    "action now or give your final answer."
)

# Future-intent cues + action verbs. When a turn ends with text that pairs the
# two but emits NO tool call, the model has *promised* an action without doing
# it (a common small-model failure that leaves the user hanging). We nudge once.
_FUTURE_CUES = (
    "i'll",
    "i will",
    "i am going to",
    "i'm going to",
    "i am about to",
    "going to",
    "let me",
    "one moment",
    "hold on",
    "give me a moment",
    "moment while",
    "stand by",
    "bear with me",
)
_ACTION_CUES = (
    "search",
    "look",
    "fetch",
    "find",
    "check",
    "research",
    "re-verify",
    "verify",
    "rewrite",
    "update",
    "write",
    "save",
    "overwrite",
    "perform",
    "create",
    "generate",
    "download",
    "open",
    "browse",
    "query",
)


def _looks_like_unfulfilled_promise(text: str) -> bool:
    """True if the text announces an imminent tool action but performs none."""
    if not text:
        return False
    t = text.lower()
    return any(f in t for f in _FUTURE_CUES) and any(a in t for a in _ACTION_CUES)


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

    has_mechanic = any(t.name.startswith("mechanic_") for t in tools)
    has_drift = any(t.name.startswith("drift_") for t in tools)
    if has_mechanic or has_drift:
        prompt += (
            "\n\nMachine memory: this box has local telemetry you can consult — prefer it "
            "over one-shot shell commands for questions about what is NORMAL or what CHANGED, "
            "because a fresh command has no baseline and no history."
        )
        if has_mechanic:
            prompt += (
                "\n- mechanic_* tools know this machine's runtime baselines (CPU, memory, "
                "Docker, Ollama models). For 'is this normal?', 'why is it slow?', or any "
                "resource question, call mechanic_is_this_normal / mechanic_baseline_for "
                "FIRST, then investigate with run_command."
            )
        if has_drift:
            prompt += (
                "\n- drift_* tools know this box's operational state over time (ports, "
                "services, packages, users, cron). For 'what changed?', 'did something get "
                "installed?', or 'why did this start happening?', call drift_diff_latest "
                "(or drift_diff for specific snapshots) FIRST."
            )
        if has_mechanic and has_drift:
            prompt += (
                "\n- The diagnosis pattern: mechanic says WHETHER something is off, drift "
                "says WHAT configuration moved, run_command lets you fix it. Chain them."
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
        self._ctx_cache: dict[str, int] = {}  # model -> resolved context window

    def effective_context(self) -> int:
        """The context window (tokens) this agent actually runs the model with.

        An explicit ``context_length`` in config wins. Otherwise (0 = auto) ask
        the backend for the model's trained maximum and cap it at
        AUTO_CONTEXT_CAP so big-context models don't allocate a surprise
        multi-GB KV cache; unknown maximum falls back to a conservative 8192.
        The result is passed to the backend as ``num_ctx`` on every request —
        without that, Ollama runs at its own default (often 4k) and silently
        truncates long conversations.
        """
        if self.config.context_length and self.config.context_length > 0:
            return self.config.context_length
        if self.model not in self._ctx_cache:
            from ..config import AUTO_CONTEXT_CAP

            try:
                trained = self.provider.max_context(self.model)
            except Exception:
                trained = None
            self._ctx_cache[self.model] = min(trained or 8192, AUTO_CONTEXT_CAP)
        return self._ctx_cache[self.model]

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

        nudges = 0  # how many "you promised — now do it" prods we've issued this turn
        for _ in range(self.config.max_tool_iterations):
            assistant_text = ""
            tool_calls = []
            for chunk in self.provider.chat(
                self._context(),
                model=self.model,
                tools=tools,
                temperature=self.config.temperature,
                num_ctx=self.effective_context(),
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
                # The model promised an action but called no tool — prod it to
                # actually carry it out instead of leaving the user hanging.
                if (
                    tools
                    and nudges < self.config.max_promise_nudges
                    and _looks_like_unfulfilled_promise(assistant_text)
                ):
                    nudges += 1
                    self.messages.append(
                        Message(
                            role="user",
                            content=(
                                "Stop. You described an action but called no tool — the user "
                                "sees only your message and nothing happens. Do NOT reply with "
                                "more narration, apologies, or 'one moment'. Emit the tool call "
                                "now (e.g. web_search / fetch_url / create_document). If you are "
                                "genuinely finished, give the final answer with no promises."
                            ),
                        )
                    )
                    continue
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

        # Cap reached. Rather than dead-stopping mid-research, give the model one
        # final, tool-free turn to deliver a usable answer from what it gathered.
        yield LimitReached(self.config.max_tool_iterations)
        self.messages.append(
            Message(
                role="user",
                content=(
                    "You've hit the tool-call limit for this turn. Do not call any more "
                    "tools — give your best final answer now using what you've already "
                    "gathered, and briefly note anything you could not finish."
                ),
            )
        )
        final_text = ""
        for chunk in self.provider.chat(
            self._context(),
            model=self.model,
            tools=None,
            temperature=self.config.temperature,
            num_ctx=self.effective_context(),
        ):
            if chunk.content:
                final_text += chunk.content
                yield TextDelta(chunk.content)
        self.messages.append(Message(role="assistant", content=final_text))
        yield TurnComplete(final_text)
