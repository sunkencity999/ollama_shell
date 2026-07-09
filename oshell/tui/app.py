"""A Textual workspace for Ollama Shell.

Three live views, kept in a tabbed sidebar beside the conversation:

* **Tools**    — the full active tool roster (local vs network) plus which
  optional capabilities this install actually has. This is what makes the TUI
  reflect the *current* app: every migrated capability shows up here.
* **Context**  — the pin/exclude state, i.e. exactly what the model is shown.
* **Activity** — a live log of tool calls and their results.

The agent loop is synchronous and streaming, so each turn runs in a worker
*thread* and marshals events back onto the UI thread via ``call_from_thread``.
"""

from __future__ import annotations

import re
import time
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, RichLog, Static, TabbedContent, TabPane

from .. import desktop
from ..agent import Agent, LimitReached, TextDelta, ToolFinished, ToolStarted, TurnComplete
from ..capabilities import optional_features
from ..config import Config
from ..providers import get_provider
from ..tools import default_registry
from .menu import (
    INSTALLABLE_FEATURES,
    AttachImageScreen,
    FeaturesScreen,
    MenuScreen,
    ModelScreen,
    MoodScreen,
    ThemeScreen,
    feature_installed,
)

# Matches fenced code blocks in the model's reply (for "copy last code block").
_CODE_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)


class ChatInput(Input):
    """A single-line Input that diverts *multi-line* pastes to the app.

    Textual's Input keeps only the first line of a pasted block; for a chat
    where people paste logs/code that's lossy. We post the full text to the app
    instead (single-line pastes fall through to normal behavior)."""

    class MultilinePasted(Message):
        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    def _on_paste(self, event: events.Paste) -> None:
        # Textual dispatches _on_paste to every class in the MRO; for multi-line
        # we divert and prevent_default() so Input's default (first-line-only)
        # handler is skipped. For single-line we do nothing and let Input's own
        # _on_paste run (calling super() here would double-insert).
        if event.text and "\n" in event.text:
            self.post_message(self.MultilinePasted(event.text))
            event.prevent_default()
            event.stop()


def _context_fill(agent: Agent) -> float:
    """Rough fraction of the context window the in-context messages occupy.

    A chars/4 token estimate — honest enough for a gauge, cheap enough to run
    on every refresh. Excluded messages don't count; that's the whole point.
    """
    chars = sum(
        len(m.content) + 16  # + a little per-message wire overhead
        for i, m in enumerate(agent.messages)
        if i not in agent.excluded
    )
    return min(chars / 4 / max(agent.effective_context(), 1), 1.0)


def _fmt_tokens(n: int) -> str:
    """32768 -> '32k'; keeps small numbers literal."""
    return f"{n // 1024}k" if n >= 4096 and n % 1024 == 0 else str(n)


def _safe_update(widget: Static, content: Text, plain: str) -> None:
    """Update a Static, never letting a render error crash the session.

    The side panels show model/tool output that can contain anything. We build
    a ``rich.text.Text`` with explicit styles (no markup parsing of dynamic
    content, so brackets/ANSI/control chars are inert), but still guard the
    update so any unexpected render failure degrades to inert plain text rather
    than taking down the whole app mid-turn.
    """
    try:
        widget.update(content)
    except Exception:
        try:
            widget.update(Text(plain or " "))
        except Exception:
            pass


class ToolsPanel(Static):
    """Live roster: active tools (local/network) + optional-feature status.

    Tools the model has actually reached for this session glow — bold name plus
    a dim ×N count — so the panel reads as an instrument, not a static list.
    The rendered text is also kept on ``self.text`` so it can be inspected
    without reaching into Textual's lazily-realized render internals.
    """

    text: str = ""

    def render_for(self, agent: Agent, counts: dict[str, int] | None = None) -> None:
        counts = counts or {}
        body = Text()
        plain: list[str] = ["Active tools"]
        body.append("Active tools", style="bold")
        for t in agent.registry.active():
            if t.sensitive:
                tag, style = "exec", "red"
            elif t.local_only:
                tag, style = "local", "green"
            else:
                tag, style = "net", "yellow"
            n = counts.get(t.name, 0)
            body.append("\n  ")
            body.append(tag, style=style)
            body.append(" ")
            # Heat: used-this-session tools are bold; untouched ones stay quiet.
            body.append(t.name, style="bold" if n else "")
            line = f"  {tag} {t.name}"
            if n:
                body.append(f" ×{n}", style="dim")
                line += f" ×{n}"
            plain.append(line)
        body.append("\n\n")
        body.append("Optional features", style="bold")
        plain += ["", "Optional features"]
        for cap in optional_features(agent.config):
            mark, mstyle = ("✓", "green") if cap.available else ("✗", "dim")
            body.append("\n  ")
            body.append(mark, style=mstyle)
            body.append(f" {cap.name} ")
            body.append(f"({cap.detail})", style="dim")
            plain.append(f"  {mark} {cap.name} ({cap.detail})")
        self.text = "\n".join(plain)
        _safe_update(self, body, self.text)


class ContextInspector(Static):
    """Shows every message and whether it's pinned / excluded / in-context,
    topped by a fill gauge estimating how much of the model's context window
    the in-context messages occupy (so pin/exclude has visible consequences)."""

    text: str = ""

    def refresh_view(self, agent: Agent) -> None:
        body = Text()
        body.append("Context", style="bold")
        body.append("  📌 pinned  🚫 excluded")
        fill = _context_fill(agent)
        blocks = round(fill * 10)
        gauge = "▰" * blocks + "▱" * (10 - blocks)
        size = _fmt_tokens(agent.effective_context())
        auto = "" if agent.config.context_length else " (auto)"
        gauge_line = f"{gauge} {fill:.0%} of ~{size} tokens{auto}"
        body.append("\n")
        body.append(gauge_line, style="red" if fill > 0.85 else "dim")
        plain: list[str] = ["Context  📌 pinned  🚫 excluded", gauge_line]
        for i, msg in enumerate(agent.messages):
            mark = "📌" if i in agent.pinned else ("🚫" if i in agent.excluded else "  ")
            raw = msg.content or f"<{len(msg.tool_calls)} tool call(s)>"
            preview = raw[:28].replace("\n", " ")
            body.append(f"\n{mark} ")
            body.append(f"{i:>2}", style="dim")
            body.append(" ")
            body.append(msg.role[:4], style="cyan")
            body.append(f" {preview}")
            plain.append(f"{mark} {i:>2} {msg.role[:4]} {preview}")
        self.text = "\n".join(plain)
        _safe_update(self, body, self.text)


class OllamaShellTUI(App):
    """The top-level Textual application."""

    CSS = """
    #body { height: 1fr; }
    #convo-pane { width: 2fr; }
    #conversation { height: 1fr; border: round $accent; padding: 0 1; }
    #live { height: auto; max-height: 8; padding: 0 1; color: $text-muted; }
    #sidebar { width: 1fr; }
    #tools, #context { padding: 0 1; }
    #activity { padding: 0 1; }
    Input { dock: bottom; }
    """
    # Esc is the primary menu key — F-keys are unreliable on macOS (the OS grabs
    # them). F2 / Ctrl+O are kept as hidden alternates for other platforms.
    BINDINGS = [
        Binding("escape", "open_menu", "Menu"),
        Binding("ctrl+t", "show_tools", "Tools"),
        Binding("ctrl+y", "copy_reply", "Copy reply"),
        Binding("ctrl+b", "copy_code", "Copy code"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("f2", "open_menu", "Menu", show=False),
        Binding("ctrl+o", "open_menu", "Menu", show=False),
    ]

    def __init__(self, agent: Agent, show_clock: bool = True, show_menu_on_start: bool = True):
        super().__init__()
        self.agent = agent
        # The header clock is live (changes every second); tests/snapshots turn
        # it off so renders are deterministic.
        self._show_clock = show_clock
        # Old-school: greet with the menu. Tests/snapshots disable it.
        self._show_menu_on_start = show_menu_on_start
        # Live-region state (read by the spinner timer on the UI thread, written
        # by the turn worker thread — plain attribute assignments are atomic).
        self._busy = False
        self._status = "Thinking"  # what the model is doing right now
        self._stream = ""  # assistant text as it streams in this round
        self._spin = 0
        self._live_text = ""  # what the live region currently shows (for tests)
        self._pending_paste = ""  # multi-line pasted text, sent with the next message
        self._pending_images: list[str] = []  # base64 images attached to next message
        self._last_reply = ""  # the model's most recent reply (for quick copy)
        # Ambient-effects state (see oshell/tui/ambient.py).
        self._ember: tuple[str, float] | None = None  # (color, monotonic birth time)
        self._idle_since = time.monotonic()  # for the idle fireflies
        self._burst: float | None = None  # LimitReached spark storm (birth time)
        # Per-session tool usage — drives the "heat" in the Tools panel.
        self._tool_counts: Counter[str] = Counter()

    _SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=self._show_clock)
        with Horizontal(id="body"):
            with Vertical(id="convo-pane"):
                # min_width: render to the pane's real width (the default of 78
                # makes full-width renderables like Rule/Markdown overflow into
                # a horizontal scrollbar on narrower panes).
                yield RichLog(
                    id="conversation", wrap=True, markup=True, highlight=True, min_width=20
                )
            with TabbedContent(id="sidebar", initial="tab-tools"):
                with TabPane("Tools", id="tab-tools"):
                    yield ToolsPanel(id="tools")
                with TabPane("Context", id="tab-context"):
                    yield ContextInspector(id="context")
                with TabPane("Activity", id="tab-activity"):
                    yield RichLog(id="activity", wrap=True, markup=True)
        # Live region: spinner/status while working, streamed reply as it
        # builds, and the idle mood. Full-width — the weather isn't clipped to
        # the conversation column, it runs under the sidebar too.
        yield Static("", id="live")
        yield ChatInput(
            placeholder="Message the model…  (Esc menu · Ctrl+P palette · Ctrl+C quit)"
        )
        yield Footer()

    def _subtitle(self) -> str:
        # A glance, not a paragraph — the Tools tab carries the full roster.
        net = [t for t in self.agent.registry.active() if not t.local_only]
        n = len(self.agent.registry)
        tail = f"{len(net)} net" if net else "fully local"
        return f"{self.agent.model} · {self.agent.provider.name} · {n} tools · {tail}"

    def on_mount(self) -> None:
        self.title = "Ollama Shell"
        self.sub_title = self._subtitle()
        try:
            self.theme = self.agent.config.theme
        except Exception:
            pass  # unknown theme name in config — keep the default
        self.query_one(ToolsPanel).render_for(self.agent)
        self.query_one(ContextInspector).refresh_view(self.agent)
        if not self._maybe_resume_session():
            self._show_welcome()
        if any(t.sensitive for t in self.agent.registry.active()):
            self._conversation().write(
                "[yellow]⚠ Autonomous shell:[/] the model can run commands on this machine "
                "(run_command) without asking. Each command is shown inline."
            )
        # Drives the live spinner / streaming preview.
        self.set_interval(0.1, self._tick)
        if self._show_menu_on_start:
            self.action_open_menu()

    def _show_welcome(self) -> None:
        """A small card so a fresh conversation feels inhabited, not bare."""
        a = self.agent
        net = [t.name for t in a.registry.active() if not t.local_only]
        badge = (
            f"[yellow]◐ {len(net)} networked tool{'s' if len(net) != 1 else ''}[/yellow]"
            if net
            else "[green]● fully local[/green]"
        )
        names = {t.name for t in a.registry.active()}
        first = (
            "is my CPU usage normal right now?"
            if any(n.startswith("mechanic_") for n in names)
            else "what's eating my CPU?"
        )
        second = (
            "what changed on this box today?"
            if any(n.startswith("drift_") for n in names)
            else "summarize ~/notes.md"
        )
        body = (
            f"[b]{escape(a.model)}[/b] [dim]· {escape(a.provider.name)} · "
            f"{len(a.registry)} tools[/dim]  {badge}\n\n"
            f"[dim]Try:[/dim] [italic]{first}[/italic]\n"
            f"[dim]  · [/dim][italic]{second}[/italic]\n"
            "[dim]  · [/dim][italic]/daydream[/italic] 💭\n\n"
            "[dim]Esc menu · Ctrl+P palette\n"
            "Ctrl+Y copy reply · Ctrl+B copy code[/dim]"
        )
        self._conversation().write(
            Panel(body, border_style="dim", padding=(0, 1), expand=False)
        )

    def _maybe_resume_session(self) -> bool:
        """Load and render the previous conversation, if any. True if resumed."""
        scfg = self.agent.config.session
        if not scfg.persist:
            return False
        from .. import session as session_mod

        prior = session_mod.load_session(scfg.path)
        if not prior:
            return False
        self.agent.messages.extend(prior)  # keep [system] + restored turns
        convo = self._conversation()
        convo.write(f"[dim]— resumed {len(prior)} earlier messages —[/dim]")
        for m in prior:
            if m.role == "user":
                convo.write(f"[bold green]›[/] {escape(m.content)}")
            elif m.role == "assistant" and m.content:
                self._write_reply(m.content)
                self._last_reply = m.content
        self.query_one(ContextInspector).refresh_view(self.agent)
        return True

    def _write_reply(self, text: str) -> None:
        """Commit a finished reply to the transcript as rendered Markdown.

        Model output is arbitrary — if the Markdown render chokes, fall back to
        inert escaped text rather than losing the reply (or the session).
        """
        convo = self._conversation()
        try:
            convo.write(Markdown(text))
        except Exception:
            convo.write(escape(text))

    def _tick(self) -> None:
        """Render the live region: spinner+status while working, or streamed text.

        With ambient effects on, this strip is also where the periphery lives:
        the thinking status drifts through aurora hues, tool completions leave a
        fading ember, and a long-idle shell hosts a few fireflies. Motion never
        enters the transcript itself.
        """
        from . import ambient

        effects = self.agent.config.fun.effects
        self._spin += 1
        if effects and self._burst is not None:
            # LimitReached: a brief particle storm takes the strip, busy or not.
            try:
                width = self.query_one("#live", Static).size.width or 40
            except NoMatches:
                width = 40
            storm = ambient.burst_markup(width, time.monotonic() - self._burst)
            if storm is None:
                self._burst = None
            else:
                self._set_live(storm)
                return
        if not self._busy:
            fun = self.agent.config.fun
            idle = time.monotonic() - self._idle_since
            mood_on = effects and fun.mood != "none"
            if (
                mood_on
                and fun.mood_takeover_seconds > 0
                and idle > fun.mood_takeover_seconds
                and len(self.screen_stack) == 1  # never take over a menu/dream/picker
            ):
                # The mood takes the whole stage (weather over the still-visible
                # workspace). Waking resumes the strip mood, not another takeover.
                from .overlay import MoodOverlay

                self.push_screen(MoodOverlay(fun.mood), self._on_takeover_wake)
                return
            if mood_on and idle > fun.mood_idle_seconds:
                try:
                    width = self.query_one("#live", Static).size.width or 40
                except NoMatches:
                    width = 40
                self._set_live(ambient.mood_markup(fun.mood, width, self._spin))
            elif self._live_text:
                self._set_live("")
            return
        frame = self._SPINNER[self._spin % len(self._SPINNER)]
        hue = ambient.aurora_color(self._spin // 3) if effects else "cyan"
        ember = ""
        if effects and self._ember is not None:
            color, born = self._ember
            glyph = ambient.ember_glyph(time.monotonic() - born)
            if glyph is None:
                self._ember = None
            else:
                ember = f"[{color}]{glyph}[/] "
        if self._stream:
            # Streaming the reply — show it building with a blinking cursor.
            self._set_live(f"[dim]{escape(self._stream)}[/dim][{hue}]▌[/]")
        else:
            self._set_live(f"{ember}[{hue}]{frame}[/] [dim]{escape(self._status)}…[/dim]")

    def _keep_mood_alive(self) -> None:
        """Rewind the idle clock so the strip mood plays now (not in 45s)."""
        self._idle_since = time.monotonic() - self.agent.config.fun.mood_idle_seconds - 1

    def _on_takeover_wake(self, _result: None) -> None:
        """Back from the full-screen mood: keep the strip weather going."""
        self._keep_mood_alive()
        self.query_one(Input).focus()

    def _set_live(self, markup: str) -> None:
        self._live_text = markup
        try:
            self.query_one("#live", Static).update(markup)
        except NoMatches:
            pass  # widget gone (app is shutting down) — the spinner timer can race teardown

    # ── turn vitals ───────────────────────────────────────────────────────────
    def _turn_stats(self, t0: float, first_delta: float | None, n_deltas: int) -> str:
        """A dim one-liner under each reply: elapsed · ~tok/s · context fill."""
        now = time.monotonic()
        parts = [f"⏱ {now - t0:.1f}s"]
        if first_delta is not None and n_deltas >= 5 and now - first_delta > 0.2:
            parts.append(f"~{n_deltas / (now - first_delta):.0f} tok/s")
        parts.append(f"ctx {_context_fill(self.agent):.0%}")
        return " · ".join(parts)

    # ── widget shortcuts ─────────────────────────────────────────────────────
    def _conversation(self) -> RichLog:
        return self.query_one("#conversation", RichLog)

    def _activity(self) -> RichLog:
        return self.query_one("#activity", RichLog)

    def action_show_tools(self) -> None:
        self.query_one(TabbedContent).active = "tab-tools"

    # ── copy to clipboard (the TUI captures the mouse, so drag-select can't) ──
    def action_copy_reply(self) -> None:
        self._copy(self._last_reply, "last reply")

    def action_copy_code(self) -> None:
        """Copy the last fenced code block from the model's last reply."""
        blocks = _CODE_FENCE_RE.findall(self._last_reply or "")
        if not blocks:
            self.notify("No code block in the last reply.", severity="warning")
            return
        self._copy(blocks[-1].rstrip() + "\n", "last code block")

    def _transcript(self) -> str:
        lines = []
        for m in self.agent.messages:
            if m.role == "user":
                lines.append(f"> {m.content}")
            elif m.role == "assistant" and m.content:
                lines.append(m.content)
        return "\n\n".join(lines)

    def _copy(self, text: str, label: str) -> None:
        # Status chatter belongs in toasts, not the transcript.
        if not text.strip():
            self.notify(f"Nothing to copy ({label}).", severity="warning")
            return
        if clipboard_write(text):
            self.notify(f"Copied {label} ({len(text)} chars).")
            return
        try:  # fall back to the terminal's clipboard via OSC 52 (works over SSH)
            self.copy_to_clipboard(text)
            self.notify(f"Copied {label} via the terminal ({len(text)} chars).")
        except Exception:
            self.notify("Couldn't access the clipboard.", severity="error")

    # ── command palette (Ctrl+P) — every menu action, fuzzy-searchable ────────
    def get_system_commands(self, screen: Screen) -> Iterator[SystemCommand]:
        yield from super().get_system_commands(screen)
        yield SystemCommand("Menu", "Open the main menu", self.action_open_menu)
        yield SystemCommand(
            "New conversation", "Clear the transcript and start fresh", self._new_conversation
        )
        yield SystemCommand(
            "Models",
            "Choose the active model",
            lambda: self.run_worker(self._open_model_picker, thread=True, exclusive=True),
        )
        yield SystemCommand("Pick theme", "Restyle the app (live preview)", self._open_theme_picker)
        yield SystemCommand(
            "Pick mood", "Idle ambience: rain, snow, aurora, ocean, …", self._open_mood_picker
        )
        yield SystemCommand(
            "Copy last reply", "Copy the model's last reply", self.action_copy_reply
        )
        yield SystemCommand(
            "Copy last code block", "Copy the last fenced code block", self.action_copy_code
        )
        yield SystemCommand(
            "Copy transcript",
            "Copy the whole conversation",
            lambda: self._copy(self._transcript(), "transcript"),
        )
        yield SystemCommand(
            "Attach image",
            "Attach an image for a vision model",
            lambda: self.push_screen(AttachImageScreen(), self._on_attach_image),
        )
        yield SystemCommand(
            "Daydream", "Let the model wander and free-associate 💭", self._start_daydream
        )

    # ── menu ─────────────────────────────────────────────────────────────────
    def action_open_menu(self) -> None:
        self.push_screen(
            MenuScreen(effects=self.agent.config.fun.effects), self._on_menu_choice
        )

    def _on_menu_choice(self, choice: str | None) -> None:
        """Run the action chosen in the modal menu."""
        if choice in (None, "chat"):
            self.query_one(Input).focus()
        elif choice == "quit":
            self.exit()
        elif choice == "tools":
            self.query_one(TabbedContent).active = "tab-tools"
        elif choice == "new_chat":
            self._new_conversation()
        elif choice == "models":
            self.run_worker(self._open_model_picker, thread=True, exclusive=True)
        elif choice == "features":
            self.push_screen(FeaturesScreen(), self._on_feature_choice)
        elif choice == "gui_toggle":
            self._toggle_gui()
        elif choice == "browser_toggle":
            self._toggle_browser()
        elif choice == "attach":
            self.push_screen(AttachImageScreen(), self._on_attach_image)
        elif choice == "copy_reply":
            self.action_copy_reply()
        elif choice == "copy_transcript":
            self._copy(self._transcript(), "transcript")
        elif choice == "finetune":
            self._menu_finetune()
        elif choice == "config":
            self._menu_config()
        elif choice == "memory":
            self._menu_memory()
        elif choice == "knowledge":
            self._menu_knowledge()
        elif choice == "daydream":
            self._start_daydream()
        elif choice == "theme":
            self._open_theme_picker()
        elif choice == "mood":
            self._open_mood_picker()
        elif choice == "help":
            self._menu_help()

    def _open_model_picker(self) -> None:
        """Fetch models (worker thread), then show the picker on the UI thread."""
        infos: dict[str, dict] = {}
        try:
            infos = {i["name"]: i for i in self.agent.provider.list_models_info()}
            models = list(infos)
        except Exception:
            try:  # metadata is a nicety — fall back to bare names
                models = self.agent.provider.list_models()
            except Exception as exc:  # network/backend down
                self.call_from_thread(
                    self.notify, f"Could not list models: {exc}", severity="error"
                )
                return
        if not models:
            self.call_from_thread(
                self.notify, "No models available. Is Ollama running?", severity="warning"
            )
            return
        self.call_from_thread(
            self.push_screen,
            ModelScreen(models, self.agent.model, infos=infos),
            self._on_model_choice,
        )

    def _on_model_choice(self, name: str | None) -> None:
        if not name:
            self.query_one(Input).focus()
            return
        self.agent.model = name
        # Rebuild tools for the new model (GUI tools are vision-gated) and refresh
        # the system prompt so the model knows what it now has.
        self._rebuild_registry()
        # Persist as the default so it sticks across sessions (until changed).
        from ..config import update_local_config

        try:
            update_local_config({"default_model": name})
            self.notify(f"Model set to {name} (saved as default).")
        except Exception as exc:  # pragma: no cover - defensive
            self.notify(f"Model set to {name} (not saved: {exc}).", severity="warning")
        self.query_one(Input).focus()

    # ── mood picking (idle-strip ambience; persisted like the theme) ──────────
    def _open_mood_picker(self) -> None:
        self.push_screen(MoodScreen(self.agent.config.fun.mood), self._on_mood_choice)

    def _set_mood(self, name: str) -> None:
        from . import ambient

        if name not in ambient.MOODS:
            self.notify(
                f"Unknown mood: {name}. Try {', '.join(ambient.MOODS)}.", severity="warning"
            )
            return
        self.agent.config.fun.mood = name
        from ..config import update_local_config

        try:
            update_local_config({"fun": {"mood": name}})
            self.notify(f"Mood set to {name} (saved as default).")
        except Exception as exc:  # pragma: no cover - defensive
            self.notify(f"Mood set to {name} (not saved: {exc}).", severity="warning")
        # Let the new mood take the strip right away instead of waiting out the
        # idle delay — picking rain should mean it starts raining.
        self._keep_mood_alive()

    def _on_mood_choice(self, name: str | None) -> None:
        if name:
            self._set_mood(name)
        self.query_one(Input).focus()

    # ── theme picking (live-preview modal; persisted like the model choice) ───
    def _open_theme_picker(self) -> None:
        names = sorted(self.available_themes)
        current = self.theme or self.agent.config.theme
        self.push_screen(ThemeScreen(names, current), self._on_theme_choice)

    def _on_theme_choice(self, name: str | None) -> None:
        if not name:
            self.query_one(Input).focus()
            return
        try:
            self.theme = name
        except Exception:
            self.notify(f"Unknown theme: {name}", severity="error")
            return
        self.agent.config.theme = name
        from ..config import update_local_config

        try:
            update_local_config({"theme": name})
            self.notify(f"Theme set to {name} (saved as default).")
        except Exception as exc:  # pragma: no cover - defensive
            self.notify(f"Theme set to {name} (not saved: {exc}).", severity="warning")
        self.query_one(Input).focus()

    def _on_attach_image(self, source: str | None) -> None:
        """Load an image (file path, or "" = clipboard) and queue it for the next turn."""
        if source is None:
            self.query_one(Input).focus()
            return
        try:
            b64, label = (clipboard_image_b64(), "clipboard") if source == "" \
                else (image_path_to_b64(source), Path(source).name)
        except ValueError as exc:
            self.notify(str(exc), severity="error")
            return
        self._pending_images.append(b64)
        self.notify(
            f"🖼 Attached {label} ({len(self._pending_images)} pending) — "
            "send a message; use a vision-capable model."
        )
        self.query_one(Input).focus()

    def _rebuild_registry(self) -> None:
        """Rebuild tools for the current model/config and tell the model about them."""
        self.agent.registry = default_registry(
            self.agent.provider, self.agent.config, model=self.agent.model, memory=self.agent.memory
        )
        self.agent.rebuild_system_prompt()
        self.query_one(ToolsPanel).render_for(self.agent, self._tool_counts)
        self.sub_title = self._subtitle()

    def _toggle_gui(self) -> None:
        import importlib.util

        from ..config import update_local_config

        new = not self.agent.config.gui.enabled
        self.agent.config.gui.enabled = new
        try:
            update_local_config({"gui": {"enabled": new}})
        except Exception:
            pass
        self._rebuild_registry()
        if not new:
            self.notify("Computer-use (GUI) is now OFF.")
            return
        if any(t.name == "screenshot" for t in self.agent.registry.active()):
            self.notify(
                "Computer-use (GUI) is now ON — screenshot/gui_click/gui_type/gui_key/gui_move "
                "are active. (macOS: grant Screen Recording + Accessibility.)",
                timeout=8,
            )
        elif importlib.util.find_spec("pyautogui") is None:
            self.notify(
                "GUI turned on, but pyautogui isn't installed — "
                "Install features → GUI computer-use first.",
                severity="warning",
                timeout=8,
            )
        else:
            self.notify(
                "GUI turned on, but the current model isn't vision+tools capable. "
                "Pick a vision model (e.g. gemma3/4, llama3.2-vision) in Models.",
                severity="warning",
                timeout=8,
            )

    def _toggle_browser(self) -> None:
        import importlib.util

        from ..config import update_local_config

        new = not self.agent.config.browser.enabled
        self.agent.config.browser.enabled = new
        try:
            update_local_config({"browser": {"enabled": new}})
        except Exception:
            pass
        self._rebuild_registry()
        if not new:
            self.notify("Hidden browser is now OFF.")
        elif any(t.name == "browser_open" for t in self.agent.registry.active()):
            self.notify(
                "Hidden browser is now ON — browser_open/screenshot/click/type/key "
                "are active (runs off-screen).",
                timeout=8,
            )
        elif importlib.util.find_spec("playwright") is None:
            self.notify(
                "Browser turned on, but Playwright isn't installed — "
                "Install features → Hidden browser first.",
                severity="warning",
                timeout=8,
            )
        else:
            self.notify(
                "Browser turned on, but the current model isn't vision+tools capable. "
                "Pick a vision model in Models.",
                severity="warning",
                timeout=8,
            )

    def _on_feature_choice(self, fid: str | None) -> None:
        if not fid:
            self.query_one(Input).focus()
            return
        feat = next((f for f in INSTALLABLE_FEATURES if f[0] == fid), None)
        if feat is None:
            return
        _, label, packages, mods = feat
        if feature_installed(mods):
            self.notify(f"{label} is already installed.")
            return
        self.run_worker(lambda: self._install_feature(label, packages, mods), thread=True)

    def _install_feature(self, label: str, packages: list[str], mods: tuple[str, ...]) -> None:
        """Install an extra's packages into the running env (worker thread).

        Output streams live: each line goes to the Activity tab and the most
        recent line drives the spinner status, so progress is visible.
        """
        import importlib

        activity = self._activity()
        self._status = f"Installing {label}"
        self._busy = True
        # Bring progress to the foreground.
        self.call_from_thread(setattr, self.query_one(TabbedContent), "active", "tab-activity")
        self.call_from_thread(
            self.notify,
            f"Installing {label}… watch the Activity tab; this can take a few minutes.",
        )

        def on_line(line: str) -> None:
            # Live status on the spinner + full detail in the Activity log.
            self._status = f"{label}: {line[:70]}"
            self.call_from_thread(activity.write, f"[dim]{escape(line)}[/dim]")

        try:
            rc = run_streaming(pip_install_cmd(packages), on_line)
            # Playwright also needs its browser binary downloaded separately.
            if rc == 0 and "playwright" in mods:
                import sys

                self._status = f"{label}: downloading Chromium"
                pw_cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
                rc = run_streaming(pw_cmd, on_line)
        except Exception as exc:  # pragma: no cover - subprocess env issues
            self.call_from_thread(self.notify, f"Install failed: {exc}", severity="error")
            return
        finally:
            self._busy = False
            self._stream = ""

        if rc == 0:
            importlib.invalidate_caches()  # let find_spec see the new packages
            ok = feature_installed(mods)
            if ok:
                self.call_from_thread(self.notify, f"✓ Installed {label} — ready to use now.")
            else:
                self.call_from_thread(
                    self.notify,
                    f"Installed {label}; restart oshell to pick it up.",
                    severity="warning",
                )
            self.call_from_thread(
                self.query_one(ToolsPanel).render_for, self.agent, self._tool_counts
            )
        else:
            self.call_from_thread(
                self.notify,
                f"Install of {label} failed (exit {rc}) — see the Activity tab.",
                severity="error",
                timeout=10,
            )

    def _menu_finetune(self) -> None:
        from ..finetune import FineTuneManager, detect_hardware

        hw = detect_hardware()
        lines = [f"[b]Fine-tuning[/b]  backend: {hw.platform} → {hw.framework}"]
        try:
            jobs = FineTuneManager(self.agent.config).list_jobs()
            lines += [f"  • {j.id}  [{j.status}]  {j.base_model}" for j in jobs] or ["  (no jobs)"]
        except Exception as exc:
            lines.append(f"  [red]{exc}[/red]")
        lines.append("[dim]Manage jobs from the terminal: oshell finetune …[/dim]")
        self._conversation().write("\n".join(lines))

    def _menu_config(self) -> None:
        c = self.agent.config
        caps = ", ".join(f"{x.name.split(' ')[0]}{'✓' if x.available else '✗'}"
                         for x in optional_features(c))
        ctx = _fmt_tokens(self.agent.effective_context())
        ctx += " (auto — set context_length to override)" if not c.context_length else ""
        self._conversation().write(
            "[b]Settings[/b]\n"
            f"  model: {self.agent.model}   provider: {c.provider.name} ({c.provider.host})\n"
            f"  temperature: {c.temperature}   max tool rounds: {c.max_tool_iterations}\n"
            f"  context window: {ctx}\n"
            f"  capabilities: {caps}\n"
            "[dim]Full config (secrets redacted): run `oshell config`.[/dim]"
        )

    def _save_session(self) -> None:
        scfg = self.agent.config.session
        if not scfg.persist:
            return
        from .. import session as session_mod

        try:
            session_mod.save_session(self.agent.messages, scfg.path, scfg.max_messages)
        except Exception:  # pragma: no cover - never let persistence break a turn
            pass

    def _new_conversation(self) -> None:
        """Start fresh: clear the transcript, the saved session, and the screen."""
        from .. import session as session_mod

        system = self.agent.messages[0] if self.agent.messages else None
        self.agent.messages = [system] if system else []
        self.agent.pinned = {0}
        self.agent.excluded = set()
        self._last_reply = ""
        try:
            session_mod.clear_session(self.agent.config.session.path)
        except Exception:
            pass
        self._conversation().clear()
        self._conversation().write("[dim]— new conversation —[/dim]")
        self._show_welcome()
        self.query_one(ContextInspector).refresh_view(self.agent)

    def _menu_memory(self) -> None:
        mem = self.agent.memory
        if mem is None:
            self._conversation().write("[dim]Memory is disabled.[/dim]")
            return
        items = mem.all()
        if not items:
            self._conversation().write(
                "[b]Memory[/b] is empty. The assistant will remember durable facts as you "
                "chat (shown as 📝). Say 'forget X' to remove one."
            )
            return
        lines = [f"[b]Memory[/b] — {len(items)} fact(s) (say 'forget X' or 'forget all'):"]
        lines += [f"  • {escape(m['text'])}" for m in items[-40:]]
        self._conversation().write("\n".join(lines))

    def _menu_knowledge(self) -> None:
        self._conversation().write(
            "[b]Knowledge base[/b] (local vectors)\n"
            "  Just talk to the model — it has tools:\n"
            "   • [green]add_knowledge[/green]: \"remember that …\"\n"
            "   • [green]search_knowledge[/green]: \"what did I save about …?\"\n"
            "[dim]Needs the [rag] extra; stored under ~/.oshell/knowledge.[/dim]"
        )

    def _menu_help(self) -> None:
        self._conversation().write(
            "[b]Help[/b]\n"
            "  The model drives: type a request and it calls tools as needed.\n"
            "  Commands:  /clear (new conversation) · /daydream · /mood [name] · /menu · /help.\n"
            "  Keys:  Esc menu · Ctrl+P command palette · Ctrl+T tools · Ctrl+C quit.\n"
            "  Copy:  Ctrl+Y last reply · Ctrl+B last code block · menu copies the transcript.\n"
            "  Select text with the mouse: hold [b]Option[/b] (macOS/iTerm2) or "
            "[b]Shift[/b] (many terminals) while dragging — the app captures normal drags.\n"
            "  Tabs:  Tools (roster + usage) · Context (pin/exclude + fill) · Activity (log)."
        )

    # ── paste / input handling ────────────────────────────────────────────────
    def on_chat_input_multiline_pasted(self, event: ChatInput.MultilinePasted) -> None:
        """Buffer a multi-line paste; it's sent with the next message."""
        self._pending_paste += (("\n" + event.text) if self._pending_paste else event.text)
        n = self._pending_paste.count("\n") + 1
        self.notify(f"📋 Pasted {n} lines — type a message (or just press Enter) to send it.")

    # ── slash commands ────────────────────────────────────────────────────────
    def _handle_slash_command(self, typed: str) -> bool:
        """Handle a ``/command`` typed at the prompt.

        Returns ``True`` if the input was a (recognized or unknown) slash
        command and should not be sent to the model.
        """
        parts = typed[1:].split(maxsplit=1)
        cmd, arg = parts[0].lower(), (parts[1].strip() if len(parts) > 1 else "")
        if cmd in ("clear", "new"):
            self._new_conversation()
            return True
        if cmd == "help":
            self._menu_help()
            self._conversation().write(
                "[dim]Commands: /clear (new conversation) · /daydream 💭 · /mood [name] · "
                "/help · /menu[/dim]"
            )
            return True
        if cmd == "mood":
            if arg:
                self._set_mood(arg.lower())
            else:
                self._open_mood_picker()
            return True
        if cmd == "menu":
            self.action_open_menu()
            return True
        if cmd in ("daydream", "dream"):
            self._start_daydream()
            return True
        self.notify(
            f"Unknown command /{cmd}. Try /clear, /daydream, /mood, /help, or /menu.",
            severity="warning",
        )
        return True

    # ── daydreams 💭 ───────────────────────────────────────────────────────────
    def _start_daydream(self) -> None:
        """Let the model wander: a short, useless, delightful free-association.

        With ambient effects on, the dream takes the whole stage: a full-screen
        starfield (oshell/tui/dream.py) that the text streams into, dismissed by
        any key. With effects off, it streams in the live strip as before. Either
        way the dream lands in the transcript and never touches model context.
        """
        if not self.agent.config.fun.daydreams:
            self.notify("Daydreams are disabled.", severity="warning")
            return
        if self._busy:
            return
        self._busy = True
        self._stream = ""
        self._status = "Daydreaming"
        screen = None
        if self.agent.config.fun.effects:
            from .. import fun
            from . import ambient
            from .dream import DreamScreen

            # The sky takes a mood from the session — rain after a stormy
            # debugging stretch, snow in December, otherwise clear — unless the
            # user picked a rainy/snowy mood themselves, which the dream honors.
            picked = self.agent.config.fun.mood
            if picked in ("rain", "snow"):
                weather = picked
            else:
                topics = fun.recent_topics(self.agent.messages)
                weather = ambient.sky_mood(topics, time.localtime().tm_mon)
            screen = DreamScreen(weather=weather, density=self.agent.config.fun.sky_density)
            self.push_screen(screen, lambda _res: self.query_one(Input).focus())
        self.run_worker(lambda: self._daydream_worker(screen), thread=True, exclusive=True)

    def _daydream_worker(self, screen=None) -> None:
        from .. import fun

        convo = self._conversation()

        def to_screen(*args) -> None:
            """Feed the dream screen, tolerating the user waking up early."""
            if screen is not None:
                try:
                    self.call_from_thread(*args)
                except Exception:
                    pass  # screen already dismissed — the transcript still gets the dream

        try:
            motif = fun.pick_motif()
            messages = fun.build_daydream_messages(self.agent.messages, motif)
            text = ""
            for piece in fun.daydream(self.agent.provider, self.agent.model, messages):
                text += piece
                self._stream = text  # live-strip fallback (effects off)
                if screen is not None:
                    to_screen(screen.feed, text)
            if screen is not None:
                to_screen(screen.finish)
            dream = escape(text.strip()) or "…(its mind wandered off the edge of the screen)"
            self.call_from_thread(
                convo.write, f"[magenta]💭[/magenta] [italic dim]{dream}[/italic dim]"
            )
        except Exception as exc:
            self.call_from_thread(
                convo.write, f"[red]the daydream slipped away: {escape(str(exc))}[/red]"
            )
        finally:
            self._busy = False
            self._stream = ""
            # Waking from a dream shouldn't cancel the ambience — the shell is
            # still idle, so the mood keeps playing in the strip.
            fun_cfg = self.agent.config.fun
            if fun_cfg.effects and fun_cfg.mood != "none":
                self._keep_mood_alive()
            else:
                self._idle_since = time.monotonic()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        typed = event.value.strip()
        event.input.value = ""
        self._idle_since = time.monotonic()  # typing dispels the fireflies
        if self._busy:  # ignore submits while a turn is running
            return
        if typed.startswith("/") and not self._pending_paste:
            if self._handle_slash_command(typed):
                return
        if self._pending_paste:
            pasted, self._pending_paste = self._pending_paste, ""
            text = f"{pasted}\n\n{typed}" if typed else pasted
            n = pasted.count(chr(10)) + 1
            echo = (
                f"{escape(typed)} [dim](+{n} pasted lines)[/dim]"
                if typed
                else f"[dim](pasted {n} lines)[/dim]"
            )
        else:
            text = typed
            echo = escape(typed)
        images, self._pending_images = self._pending_images, []
        if images:
            echo += f" [dim](+{len(images)} image{'s' if len(images) > 1 else ''})[/dim]"
        if not text and not images:
            return
        if not text:
            text = "Describe / analyze the attached image."
        # A dim, timestamped rule gives the transcript a visual rhythm — the eye
        # can find where each exchange starts.
        self._conversation().write(
            Rule(time.strftime("%H:%M"), style="dim", align="right"), expand=True
        )
        self._conversation().write(f"[bold green]›[/] {echo}")
        # Engage the live indicator before the (possibly slow) first token.
        self._stream = ""
        self._status = "Thinking"
        self._busy = True
        self.run_worker(lambda: self._worker(text, images), thread=True, exclusive=True)

    def _worker(self, text: str, images: list[str] | None = None) -> None:
        convo, activity = self._conversation(), self._activity()
        used_gui = False  # did this turn drive the desktop GUI?
        used_memory = False  # did this turn change long-term memory?
        # Turn vitals: elapsed time and a streaming-rate estimate. Ollama sends
        # roughly one token per streamed chunk, so the delta count ≈ tokens.
        t0 = time.monotonic()
        first_delta: float | None = None
        n_deltas = 0
        try:
            for event in self.agent.send(text, images=images):
                if isinstance(event, TextDelta):
                    if first_delta is None:
                        first_delta = time.monotonic()
                    n_deltas += 1
                    self._stream += event.text  # the spinner timer renders this live
                elif isinstance(event, ToolStarted):
                    if event.name == "screenshot" or event.name.startswith("gui_"):
                        used_gui = True
                    if event.name in ("remember", "forget"):
                        used_memory = True
                    self._status = f"Running {event.name}"
                    self._stream = ""  # back to spinner while the tool runs
                    if event.name == "remember":  # nicer, visible memory capture
                        fact = escape(str(event.arguments.get("text", "")))
                        line = f"[magenta]📝 remembered:[/magenta] {fact}"
                        self.call_from_thread(convo.write, line)
                    else:
                        args = _compact_args(event.arguments)
                        # Show the real call INLINE so the user can trust (or catch) it.
                        self.call_from_thread(
                            convo.write, f"[cyan]🔧 {event.name}[/cyan][dim]({escape(args)})[/dim]"
                        )
                    act = f"[dim]⚙ {event.name}({event.arguments})[/dim]"
                    self.call_from_thread(activity.write, act)
                elif isinstance(event, ToolFinished):
                    self._status = "Thinking"
                    self._tool_counts[event.name] += 1  # heat for the Tools panel
                    if self.agent.config.fun.effects:  # a spark fades in the live bar
                        from . import ambient

                        self._ember = (ambient.ember_color_for(event.name), time.monotonic())
                    if event.name != "remember":  # already shown as "📝 remembered: …"
                        summary = _summarize_result(event.result)
                        self.call_from_thread(convo.write, f"[dim]   ↳ {escape(summary)}[/dim]")
                    self.call_from_thread(
                        activity.write, f"[dim]  ↳ {escape(event.result[:200])}[/dim]"
                    )
                elif isinstance(event, TurnComplete):
                    if event.text:
                        self._last_reply = event.text  # for Ctrl+Y / menu copy
                        # Commit the finished reply as rendered Markdown (headers,
                        # lists, syntax-highlighted code blocks).
                        self.call_from_thread(self._write_reply, event.text)
                    else:
                        self.call_from_thread(convo.write, "[dim](no text)[/dim]")
                    stats = self._turn_stats(t0, first_delta, n_deltas)
                    self.call_from_thread(convo.write, f"[dim]   {stats}[/dim]")
                elif isinstance(event, LimitReached):
                    if self.agent.config.fun.effects:  # sparks scatter in the strip
                        self._burst = time.monotonic()
                    self.call_from_thread(
                        convo.write,
                        f"[yellow]Reached the {event.iterations}-round tool limit — "
                        "wrapping up with what I have.[/yellow]",
                    )
        except Exception as exc:  # surface backend errors instead of a silent hang
            self.call_from_thread(convo.write, f"[red]Error: {exc}[/red]")
        finally:
            # Stop the indicator and refresh the context view (guard teardown race).
            self._busy = False
            self._stream = ""
            self._idle_since = time.monotonic()  # fireflies count from the turn's end
            if used_memory:
                # Re-inject updated memory so later turns reflect what was just saved.
                self.agent.rebuild_system_prompt()
            self._save_session()
            try:
                inspector = self.query_one(ContextInspector)
                self.call_from_thread(inspector.refresh_view, self.agent)
                panel = self.query_one(ToolsPanel)
                self.call_from_thread(panel.render_for, self.agent, self._tool_counts)
            except NoMatches:
                pass
            # After a turn that drove the desktop GUI, tell the user it's done and
            # bring their terminal back to the front (it likely lost focus).
            if used_gui:
                gcfg = self.agent.config.gui
                if gcfg.notify_on_finish:
                    desktop.notify("Ollama Shell", "Finished controlling the screen.")
                if gcfg.refocus_terminal:
                    desktop.focus_terminal()


def image_path_to_b64(path: str) -> str:
    """Read an image file and return base64 (raises ValueError on problems)."""
    import base64

    p = Path(path).expanduser()
    if not p.is_file():
        raise ValueError(f"no such file: {path}")
    if p.stat().st_size > 20_000_000:
        raise ValueError("image too large (>20 MB)")
    return base64.b64encode(p.read_bytes()).decode()


def clipboard_image_b64() -> str:
    """Grab an image from the system clipboard as base64 PNG (needs Pillow)."""
    import base64
    import io

    try:
        from PIL import ImageGrab  # type: ignore
    except ImportError as exc:
        raise ValueError(
            "clipboard images need Pillow — install the 'vision' feature from the menu"
        ) from exc
    try:
        img = ImageGrab.grabclipboard()
    except Exception as exc:  # Linux without xclip/wl-paste, etc.
        raise ValueError(f"could not read clipboard image: {exc}") from exc
    if img is None or isinstance(img, list):  # list => file paths copied, not pixels
        raise ValueError("no image on the clipboard (copy an image first)")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def run_streaming(cmd: list[str], on_line, timeout: float = 1800) -> int:
    """Run ``cmd``, calling ``on_line(line)`` for each output line as it arrives.

    stdout+stderr are merged and line-buffered so progress is visible live rather
    than only at the end. Returns the process exit code.
    """
    import subprocess

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip("\n")
            if line.strip():
                on_line(line)
        return proc.wait(timeout=timeout)
    finally:
        if proc.poll() is None:  # pragma: no cover - cleanup on error/timeout
            proc.kill()


def clipboard_write(text: str) -> bool:
    """Write text to the OS clipboard via the platform tool. Returns success.

    Used because a Textual app captures the mouse, so the terminal's native
    drag-to-select-and-copy doesn't work inside the window.
    """
    import os
    import shutil
    import subprocess

    cmd: list[str] | None = None
    if shutil.which("pbcopy"):  # macOS
        cmd = ["pbcopy"]
    elif shutil.which("wl-copy"):  # Wayland
        cmd = ["wl-copy"]
    elif shutil.which("xclip"):  # X11
        cmd = ["xclip", "-selection", "clipboard"]
    elif shutil.which("xsel"):
        cmd = ["xsel", "--clipboard", "--input"]
    elif os.name == "nt":  # Windows
        cmd = ["clip"]
    if cmd is None:
        return False
    try:
        subprocess.run(cmd, input=text, text=True, check=True, timeout=5)
        return True
    except Exception:
        return False


def pip_install_cmd(packages: list[str]) -> list[str]:
    """Build the install command for the *current* interpreter's environment.

    Prefer `uv pip install --python <this-python>` (works even when the env has
    no pip, e.g. uv tool venvs); fall back to `python -m pip`.
    """
    import shutil
    import sys

    if shutil.which("uv"):
        return ["uv", "pip", "install", "--python", sys.executable, *packages]
    return [sys.executable, "-m", "pip", "install", *packages]


def _compact_args(args: dict) -> str:
    """One-line, truncated rendering of tool-call arguments."""
    parts = []
    for k, v in (args or {}).items():
        s = str(v).replace("\n", " ")
        parts.append(f"{k}={s[:50]}{'…' if len(s) > 50 else ''}")
    return ", ".join(parts)


def _summarize_result(result: str) -> str:
    """A short, honest one-line summary of a tool result for inline display.

    Surfaces empty/error results plainly so the user can tell when a tool found
    nothing — and the model is just talking.
    """
    # Plain text only — the caller escapes this before rendering, so any Rich
    # markup tags here would be shown literally rather than styled.
    r = (result or "").strip()
    if not r or r == "(no results)":
        return "no results"
    if r.startswith("[error]"):
        return r[:120]
    first = r.replace("\n", " ")
    n = len(r)
    return f"{n} chars · {first[:90]}{'…' if len(first) > 90 else ''}"


def run_tui(model: str | None = None) -> None:
    from ..memory import MemoryStore

    config = Config.load()
    provider = get_provider(config)
    m = model or config.default_model
    memory = MemoryStore(config.memory.path)
    registry = default_registry(provider, config, model=m, memory=memory)
    agent = Agent(provider, registry, config, model=m, memory=memory)
    OllamaShellTUI(agent).run()
