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
        for cap in optional_features():
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
    BINDINGS = [("ctrl+c", "quit", "Quit"), ("ctrl+t", "show_tools", "Tools")]

    def __init__(self, agent: Agent):
        super().__init__()
        self.agent = agent

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            yield RichLog(id="conversation", wrap=True, markup=True, highlight=True)
            with TabbedContent(id="sidebar", initial="tab-tools"):
                with TabPane("Tools", id="tab-tools"):
                    yield ToolsPanel(id="tools")
                with TabPane("Context", id="tab-context"):
                    yield ContextInspector(id="context")
                with TabPane("Activity", id="tab-activity"):
                    yield RichLog(id="activity", wrap=True, markup=True)
        yield Input(placeholder="Message the model…  (Ctrl+C quit · Ctrl+T tools)")
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

    # ── widget shortcuts ─────────────────────────────────────────────────────
    def _conversation(self) -> RichLog:
        return self.query_one("#conversation", RichLog)

    def _activity(self) -> RichLog:
        return self.query_one("#activity", RichLog)

    def action_show_tools(self) -> None:
        self.query_one(TabbedContent).active = "tab-tools"

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
