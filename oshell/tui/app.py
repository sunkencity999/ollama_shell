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
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Input, RichLog, Static, TabbedContent, TabPane

from ..agent import Agent, LimitReached, TextDelta, ToolFinished, ToolStarted, TurnComplete
from ..capabilities import optional_features
from ..config import Config
from ..providers import get_provider
from ..tools import default_registry
from .menu import MenuScreen


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
    #conversation { width: 2fr; border: round $accent; padding: 0 1; }
    #sidebar { width: 1fr; }
    #tools, #context { padding: 0 1; }
    #activity { padding: 0 1; }
    Input { dock: bottom; }
    """
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("f2", "open_menu", "Menu"),
        ("ctrl+t", "show_tools", "Tools"),
    ]

    def __init__(self, agent: Agent, show_clock: bool = True, show_menu_on_start: bool = True):
        super().__init__()
        self.agent = agent
        # The header clock is live (changes every second); tests/snapshots turn
        # it off so renders are deterministic.
        self._show_clock = show_clock
        # Old-school: greet with the menu. Tests/snapshots disable it.
        self._show_menu_on_start = show_menu_on_start

    def compose(self) -> ComposeResult:
        yield Header(show_clock=self._show_clock)
        with Horizontal(id="body"):
            yield RichLog(id="conversation", wrap=True, markup=True, highlight=True)
            with TabbedContent(id="sidebar", initial="tab-tools"):
                with TabPane("Tools", id="tab-tools"):
                    yield ToolsPanel(id="tools")
                with TabPane("Context", id="tab-context"):
                    yield ContextInspector(id="context")
                with TabPane("Activity", id="tab-activity"):
                    yield RichLog(id="activity", wrap=True, markup=True)
        yield Input(placeholder="Message the model…  (F2 menu · Ctrl+T tools · Ctrl+C quit)")
        yield Footer()

    def on_mount(self) -> None:
        net = [t.name for t in self.agent.registry.active() if not t.local_only]
        n = len(self.agent.registry)
        self.title = "Ollama Shell"
        self.sub_title = (
            f"{self.agent.model} · {self.agent.provider.name} · {n} tools · "
            + ("network: " + ", ".join(net) if net else "fully local")
        )
        self.query_one(ToolsPanel).render_for(self.agent)
        self.query_one(ContextInspector).refresh_view(self.agent)
        banner = (
            "[green]Local-first.[/] Model runs on this machine. "
            + (f"Network-capable tools: {', '.join(net)}." if net else "No networked tools active.")
        )
        self._conversation().write(banner)
        self._conversation().write("[dim]Press F2 for the menu.[/dim]")
        if self._show_menu_on_start:
            self.action_open_menu()

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
            self.run_worker(self._menu_models, thread=True, exclusive=True)
        elif choice == "finetune":
            self._menu_finetune()
        elif choice == "config":
            self._menu_config()
        elif choice == "knowledge":
            self._menu_knowledge()
        elif choice == "help":
            self._menu_help()

    def _menu_models(self) -> None:
        convo = self._conversation()
        try:
            models = self.agent.provider.list_models()
            body = "\n".join(f"  • {m}" for m in models) or "  (none)"
        except Exception as exc:  # network/backend down
            body = f"  [red]could not list models: {exc}[/red]"
        self.call_from_thread(convo.write, f"[b]Models[/b] ({self.agent.provider.name}):\n{body}")

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
        if not text:
            return
        self._conversation().write(f"[bold green]›[/] {text}")
        self.run_worker(lambda: self._worker(text), thread=True, exclusive=True)

    def _worker(self, text: str) -> None:
        convo, activity = self._conversation(), self._activity()
        buffer: list[str] = []
        for event in self.agent.send(text):
            if isinstance(event, TextDelta):
                buffer.append(event.text)
            elif isinstance(event, ToolStarted):
                line = f"[dim]⚙ {event.name}({event.arguments})[/dim]"
                self.call_from_thread(activity.write, line)
            elif isinstance(event, ToolFinished):
                preview = event.result.replace("\n", " ")[:80]
                self.call_from_thread(activity.write, f"[dim]  ↳ {preview}[/dim]")
            elif isinstance(event, TurnComplete):
                self.call_from_thread(convo.write, "".join(buffer) or "[dim](no text)[/dim]")
            elif isinstance(event, LimitReached):
                self.call_from_thread(
                    convo.write, f"[red]Stopped after {event.iterations} tool rounds.[/red]"
                )
        self.call_from_thread(self.query_one(ContextInspector).refresh_view, self.agent)


def run_tui(model: str | None = None) -> None:
    config = Config.load()
    provider = get_provider(config)
    registry = default_registry(provider, config)
    agent = Agent(provider, registry, config, model=model)
    OllamaShellTUI(agent).run()
