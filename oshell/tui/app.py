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

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static, TabbedContent, TabPane

from ..agent import Agent, LimitReached, TextDelta, ToolFinished, ToolStarted, TurnComplete
from ..capabilities import optional_features
from ..config import Config
from ..providers import get_provider
from ..tools import default_registry
from .menu import MenuScreen, ModelScreen


class ToolsPanel(Static):
    """Static roster: active tools (local/network) + optional-feature status.

    The rendered text is also kept on ``self.text`` so it can be inspected
    without reaching into Textual's lazily-realized render internals.
    """

    text: str = ""

    def render_for(self, agent: Agent) -> None:
        lines = ["[b]Active tools[/b]"]
        for t in agent.registry.active():
            tag = "[green]local[/green]" if t.local_only else "[yellow]net[/yellow]"
            lines.append(f"  {tag} [bold]{t.name}[/bold]")
        lines.append("")
        lines.append("[b]Optional features[/b]")
        for cap in optional_features(agent.config):
            mark = "[green]✓[/green]" if cap.available else "[dim]✗[/dim]"
            # escape: detail may contain "[web]" etc. that Rich would eat as markup
            lines.append(f"  {mark} {cap.name} [dim]({escape(cap.detail)})[/dim]")
        self.text = "\n".join(lines)
        self.update(self.text)


class ContextInspector(Static):
    """Shows every message and whether it's pinned / excluded / in-context."""

    text: str = ""

    def refresh_view(self, agent: Agent) -> None:
        lines = ["[b]Context[/b]  📌 pinned  🚫 excluded"]
        for i, msg in enumerate(agent.messages):
            mark = "📌" if i in agent.pinned else ("🚫" if i in agent.excluded else "  ")
            raw = msg.content or f"<{len(msg.tool_calls)} tool call(s)>"
            preview = raw[:28].replace("\n", " ")
            lines.append(f"{mark} [dim]{i:>2}[/dim] [cyan]{msg.role[:4]}[/cyan] {preview}")
        self.text = "\n".join(lines)
        self.update(self.text)


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
        yield Input(placeholder="Message the model…  (Esc menu · Ctrl+T tools · Ctrl+C quit)")
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
        self._conversation().write("[dim]Press Esc for the menu.[/dim]")
        # Drives the live spinner / streaming preview.
        self.set_interval(0.1, self._tick)
        if self._show_menu_on_start:
            self.action_open_menu()

    def _tick(self) -> None:
        """Render the live region: spinner+status while working, or streamed text."""
        if not self._busy:
            if self._live_text:
                self._set_live("")
            return
        self._spin = (self._spin + 1) % len(self._SPINNER)
        frame = self._SPINNER[self._spin]
        if self._stream:
            # Streaming the reply — show it building with a blinking cursor.
            self._set_live(f"[dim]{escape(self._stream)}[/dim][cyan]▌[/cyan]")
        else:
            self._set_live(f"[cyan]{frame}[/cyan] [dim]{escape(self._status)}…[/dim]")

    def _set_live(self, markup: str) -> None:
        self._live_text = markup
        self.query_one("#live", Static).update(markup)

    # ── widget shortcuts ─────────────────────────────────────────────────────
    def _conversation(self) -> RichLog:
        return self.query_one("#conversation", RichLog)

    def _activity(self) -> RichLog:
        return self.query_one("#activity", RichLog)

    def action_show_tools(self) -> None:
        self.query_one(TabbedContent).active = "tab-tools"

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
        elif choice == "models":
            self.run_worker(self._open_model_picker, thread=True, exclusive=True)
        elif choice == "finetune":
            self._menu_finetune()
        elif choice == "config":
            self._menu_config()
        elif choice == "knowledge":
            self._menu_knowledge()
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
        self.sub_title = self._subtitle()  # header reflects the new model
        self._conversation().write(f"[green]Model set to[/green] [bold]{name}[/bold]")
        self.query_one(Input).focus()

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
            "  Keys:  F2 menu · Ctrl+T tools · Ctrl+C quit · Tab/↑↓ navigate.\n"
            "  Tabs:  Tools (roster) · Context (pin/exclude) · Activity (tool log)."
        )

    # ── input handling ───────────────────────────────────────────────────────
    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        if not text or self._busy:  # ignore submits while a turn is running
            return
        self._conversation().write(f"[bold green]›[/] {text}")
        # Engage the live indicator before the (possibly slow) first token.
        self._stream = ""
        self._status = "Thinking"
        self._busy = True
        self.run_worker(lambda: self._worker(text), thread=True, exclusive=True)

    def _worker(self, text: str) -> None:
        convo, activity = self._conversation(), self._activity()
        try:
            for event in self.agent.send(text):
                if isinstance(event, TextDelta):
                    self._stream += event.text  # the spinner timer renders this live
                elif isinstance(event, ToolStarted):
                    self._status = f"Running {event.name}"
                    self._stream = ""  # back to spinner while the tool runs
                    line = f"[dim]⚙ {event.name}({event.arguments})[/dim]"
                    self.call_from_thread(activity.write, line)
                elif isinstance(event, ToolFinished):
                    self._status = "Thinking"
                    preview = event.result.replace("\n", " ")[:80]
                    self.call_from_thread(activity.write, f"[dim]  ↳ {preview}[/dim]")
                elif isinstance(event, TurnComplete):
                    final = event.text or "[dim](no text)[/dim]"
                    self.call_from_thread(convo.write, final)
                elif isinstance(event, LimitReached):
                    self.call_from_thread(
                        convo.write, f"[red]Stopped after {event.iterations} tool rounds.[/red]"
                    )
        except Exception as exc:  # surface backend errors instead of a silent hang
            self.call_from_thread(convo.write, f"[red]Error: {exc}[/red]")
        finally:
            # Stop the indicator and refresh the context view.
            self._busy = False
            self._stream = ""
            self.call_from_thread(self.query_one(ContextInspector).refresh_view, self.agent)


def run_tui(model: str | None = None) -> None:
    config = Config.load()
    provider = get_provider(config)
    registry = default_registry(provider, config)
    agent = Agent(provider, registry, config, model=model)
    OllamaShellTUI(agent).run()
