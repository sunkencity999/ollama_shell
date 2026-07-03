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

import time
from pathlib import Path

from rich.markup import escape
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.message import Message
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
    feature_installed,
)


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
    """Static roster: active tools (local/network) + optional-feature status.

    The rendered text is also kept on ``self.text`` so it can be inspected
    without reaching into Textual's lazily-realized render internals.
    """

    text: str = ""

    def render_for(self, agent: Agent) -> None:
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
            body.append("\n  ")
            body.append(tag, style=style)
            body.append(" ")
            body.append(t.name, style="bold")
            plain.append(f"  {tag} {t.name}")
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
    """Shows every message and whether it's pinned / excluded / in-context."""

    text: str = ""

    def refresh_view(self, agent: Agent) -> None:
        body = Text()
        body.append("Context", style="bold")
        body.append("  📌 pinned  🚫 excluded")
        plain: list[str] = ["Context  📌 pinned  🚫 excluded"]
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

    _SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=self._show_clock)
        with Horizontal(id="body"):
            with Vertical(id="convo-pane"):
                yield RichLog(id="conversation", wrap=True, markup=True, highlight=True)
                # Live region: spinner/status while working, streamed reply as it builds.
                yield Static("", id="live")
            with TabbedContent(id="sidebar", initial="tab-tools"):
                with TabPane("Tools", id="tab-tools"):
                    yield ToolsPanel(id="tools")
                with TabPane("Context", id="tab-context"):
                    yield ContextInspector(id="context")
                with TabPane("Activity", id="tab-activity"):
                    yield RichLog(id="activity", wrap=True, markup=True)
        yield ChatInput(placeholder="Message the model…  (Esc menu · Ctrl+T tools · Ctrl+C quit)")
        yield Footer()

    def _subtitle(self) -> str:
        net = [t.name for t in self.agent.registry.active() if not t.local_only]
        n = len(self.agent.registry)
        return (
            f"{self.agent.model} · {self.agent.provider.name} · {n} tools · "
            + ("network: " + ", ".join(net) if net else "fully local")
        )

    def on_mount(self) -> None:
        net = [t.name for t in self.agent.registry.active() if not t.local_only]
        self.title = "Ollama Shell"
        self.sub_title = self._subtitle()
        self.query_one(ToolsPanel).render_for(self.agent)
        self.query_one(ContextInspector).refresh_view(self.agent)
        banner = (
            "[green]Local-first.[/] Model runs on this machine. "
            + (f"Network-capable tools: {', '.join(net)}." if net else "No networked tools active.")
        )
        self._conversation().write(banner)
        if any(t.sensitive for t in self.agent.registry.active()):
            self._conversation().write(
                "[yellow]⚠ Autonomous shell:[/] the model can run commands on this machine "
                "(run_command) without asking. Each command is shown inline."
            )
        self._conversation().write(
            "[dim]Press Esc for the menu · Ctrl+Y copies the last reply "
            "(Option/Shift+drag to select text).[/dim]"
        )
        self._maybe_resume_session()
        # Drives the live spinner / streaming preview.
        self.set_interval(0.1, self._tick)
        if self._show_menu_on_start:
            self.action_open_menu()

    def _maybe_resume_session(self) -> None:
        """Load and render the previous conversation, if any."""
        scfg = self.agent.config.session
        if not scfg.persist:
            return
        from .. import session as session_mod

        prior = session_mod.load_session(scfg.path)
        if not prior:
            return
        self.agent.messages.extend(prior)  # keep [system] + restored turns
        convo = self._conversation()
        convo.write(f"[dim]— resumed {len(prior)} earlier messages —[/dim]")
        for m in prior:
            if m.role == "user":
                convo.write(f"[bold green]›[/] {escape(m.content)}")
            elif m.role == "assistant" and m.content:
                convo.write(escape(m.content))
                self._last_reply = m.content
        self.query_one(ContextInspector).refresh_view(self.agent)

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
        if not self._busy:
            if effects and (time.monotonic() - self._idle_since) > ambient.IDLE_FIREFLIES_AFTER:
                try:
                    width = self.query_one("#live", Static).size.width or 40
                except NoMatches:
                    width = 40
                self._set_live(ambient.fireflies_markup(width, self._spin))
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

    def _set_live(self, markup: str) -> None:
        self._live_text = markup
        try:
            self.query_one("#live", Static).update(markup)
        except NoMatches:
            pass  # widget gone (app is shutting down) — the spinner timer can race teardown

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

    def _transcript(self) -> str:
        lines = []
        for m in self.agent.messages:
            if m.role == "user":
                lines.append(f"> {m.content}")
            elif m.role == "assistant" and m.content:
                lines.append(m.content)
        return "\n\n".join(lines)

    def _copy(self, text: str, label: str) -> None:
        convo = self._conversation()
        if not text.strip():
            convo.write(f"[dim]nothing to copy ({label})[/dim]")
            return
        if clipboard_write(text):
            convo.write(f"[green]copied {label}[/green] [dim]({len(text)} chars)[/dim]")
            return
        try:  # fall back to the terminal's clipboard via OSC 52 (works over SSH)
            self.copy_to_clipboard(text)
            convo.write(f"[green]copied {label}[/green] [dim](via terminal · {len(text)}c)[/dim]")
        except Exception:
            convo.write("[red]couldn't access the clipboard[/red]")

    # ── menu ─────────────────────────────────────────────────────────────────
    def action_open_menu(self) -> None:
        self.push_screen(MenuScreen(), self._on_menu_choice)

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
        elif choice == "help":
            self._menu_help()

    def _open_model_picker(self) -> None:
        """Fetch models (worker thread), then show the picker on the UI thread."""
        convo = self._conversation()
        try:
            models = self.agent.provider.list_models()
        except Exception as exc:  # network/backend down
            self.call_from_thread(convo.write, f"[red]Could not list models: {exc}[/red]")
            return
        if not models:
            msg = "[yellow]No models available. Is Ollama running?[/yellow]"
            self.call_from_thread(convo.write, msg)
            return
        self.call_from_thread(
            self.push_screen, ModelScreen(models, self.agent.model), self._on_model_choice
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
            note = "[dim](saved as default)[/dim]"
        except Exception as exc:  # pragma: no cover - defensive
            note = f"[dim](not saved: {exc})[/dim]"
        self._conversation().write(f"[green]Model set to[/green] [bold]{name}[/bold] {note}")
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
            self._conversation().write(f"[red]{escape(str(exc))}[/red]")
            return
        self._pending_images.append(b64)
        self._conversation().write(
            f"[dim]🖼 attached {escape(label)} ({len(self._pending_images)} pending) — "
            "send a message; use a vision-capable model.[/dim]"
        )
        self.query_one(Input).focus()

    def _rebuild_registry(self) -> None:
        """Rebuild tools for the current model/config and tell the model about them."""
        self.agent.registry = default_registry(
            self.agent.provider, self.agent.config, model=self.agent.model, memory=self.agent.memory
        )
        self.agent.rebuild_system_prompt()
        self.query_one(ToolsPanel).render_for(self.agent)
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
        convo = self._conversation()
        if not new:
            convo.write("[yellow]Computer-use (GUI) is now OFF.[/yellow]")
            return
        if any(t.name == "screenshot" for t in self.agent.registry.active()):
            convo.write(
                "[green]Computer-use (GUI) is now ON[/green] — screenshot/gui_click/gui_type/"
                "gui_key/gui_move are active. (macOS: grant Screen Recording + Accessibility.)"
            )
        elif importlib.util.find_spec("pyautogui") is None:
            convo.write(
                "[yellow]GUI turned on, but pyautogui isn't installed[/yellow] — "
                "Install features → GUI computer-use first."
            )
        else:
            convo.write(
                "[yellow]GUI turned on, but the current model isn't vision+tools capable.[/yellow] "
                "Pick a vision model (e.g. gemma3/4, llama3.2-vision) in Models."
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
        convo = self._conversation()
        if not new:
            convo.write("[yellow]Hidden browser is now OFF.[/yellow]")
        elif any(t.name == "browser_open" for t in self.agent.registry.active()):
            convo.write(
                "[green]Hidden browser is now ON[/green] — browser_open/screenshot/click/"
                "type/key are active (runs off-screen)."
            )
        elif importlib.util.find_spec("playwright") is None:
            convo.write(
                "[yellow]Browser turned on, but Playwright isn't installed[/yellow] — "
                "Install features → Hidden browser first."
            )
        else:
            convo.write(
                "[yellow]Browser turned on, but the current model isn't vision+tools "
                "capable.[/yellow] Pick a vision model in Models."
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
            self._conversation().write(f"[dim]{label} is already installed.[/dim]")
            return
        self.run_worker(lambda: self._install_feature(label, packages, mods), thread=True)

    def _install_feature(self, label: str, packages: list[str], mods: tuple[str, ...]) -> None:
        """Install an extra's packages into the running env (worker thread).

        Output streams live: each line goes to the Activity tab and the most
        recent line drives the spinner status, so progress is visible.
        """
        import importlib

        convo, activity = self._conversation(), self._activity()
        self._status = f"Installing {label}"
        self._busy = True
        # Bring progress to the foreground.
        self.call_from_thread(setattr, self.query_one(TabbedContent), "active", "tab-activity")
        self.call_from_thread(
            convo.write,
            f"[cyan]Installing {label}…[/cyan] [dim]{escape(' '.join(packages))} "
            "(watch the Activity tab; this can take a few minutes)[/dim]",
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
            self.call_from_thread(convo.write, f"[red]Install failed: {exc}[/red]")
            return
        finally:
            self._busy = False
            self._stream = ""

        if rc == 0:
            importlib.invalidate_caches()  # let find_spec see the new packages
            ok = feature_installed(mods)
            msg = (
                f"[green]✓ Installed {label} — ready to use now.[/green]"
                if ok
                else f"[yellow]Installed {label}; restart oshell to pick it up.[/yellow]"
            )
            self.call_from_thread(convo.write, msg)
            self.call_from_thread(self.query_one(ToolsPanel).render_for, self.agent)
        else:
            self.call_from_thread(
                convo.write,
                f"[red]Install of {label} failed (exit {rc}) — see the Activity tab.[/red]",
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
        self._conversation().write(
            "[b]Settings[/b]\n"
            f"  model: {self.agent.model}   provider: {c.provider.name} ({c.provider.host})\n"
            f"  temperature: {c.temperature}   max tool rounds: {c.max_tool_iterations}\n"
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
            "  Commands:  /clear (new conversation) · /menu · /help.\n"
            "  Keys:  Esc menu · Ctrl+T tools · Ctrl+Y copy reply · Ctrl+C quit.\n"
            "  Copy: Ctrl+Y copies the last reply; the menu also copies the transcript.\n"
            "  Select text with the mouse: hold [b]Option[/b] (macOS/iTerm2) or "
            "[b]Shift[/b] (many terminals) while dragging — the app captures normal drags.\n"
            "  Tabs:  Tools (roster) · Context (pin/exclude) · Activity (tool log)."
        )

    # ── paste / input handling ────────────────────────────────────────────────
    def on_chat_input_multiline_pasted(self, event: ChatInput.MultilinePasted) -> None:
        """Buffer a multi-line paste; it's sent with the next message."""
        self._pending_paste += (("\n" + event.text) if self._pending_paste else event.text)
        n = self._pending_paste.count("\n") + 1
        self._conversation().write(
            f"[dim]📋 pasted {n} lines — type a message (or just press Enter) to send it.[/dim]"
        )

    # ── slash commands ────────────────────────────────────────────────────────
    def _handle_slash_command(self, typed: str) -> bool:
        """Handle a ``/command`` typed at the prompt.

        Returns ``True`` if the input was a (recognized or unknown) slash
        command and should not be sent to the model.
        """
        cmd = typed[1:].split(maxsplit=1)[0].lower()
        if cmd in ("clear", "new"):
            self._new_conversation()
            return True
        if cmd == "help":
            self._menu_help()
            self._conversation().write(
                "[dim]Commands: /clear (new conversation) · /daydream 💭 · /help · /menu[/dim]"
            )
            return True
        if cmd == "menu":
            self.action_open_menu()
            return True
        if cmd in ("daydream", "dream"):
            self._start_daydream()
            return True
        self._conversation().write(
            f"[dim]Unknown command [b]/{escape(cmd)}[/b]. "
            "Try /clear, /daydream, /help, or /menu.[/dim]"
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
            self._conversation().write("[dim]Daydreams are disabled.[/dim]")
            return
        if self._busy:
            return
        self._busy = True
        self._stream = ""
        self._status = "Daydreaming"
        screen = None
        if self.agent.config.fun.effects:
            from .dream import DreamScreen

            screen = DreamScreen()
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
        try:
            for event in self.agent.send(text, images=images):
                if isinstance(event, TextDelta):
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
                    # Escape: the model's reply may contain [..] that Rich would
                    # parse as markup (markdown links, arrays) and crash on.
                    final = escape(event.text) if event.text else "[dim](no text)[/dim]"
                    self.call_from_thread(convo.write, final)
                elif isinstance(event, LimitReached):
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
