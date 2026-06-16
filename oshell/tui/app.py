"""A Textual workspace for Ollama Shell.

This realizes the "TUI workspace, not a line-by-line REPL" idea: three live
panes — the conversation, a **context inspector** (the pin/exclude feature made
visible), and a **tool-activity log** — instead of invisible slash commands.

The agent loop is synchronous and streaming, so we run each turn in a worker
*thread* and marshal events back onto the UI thread via ``call_from_thread``.
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from ..agent import Agent, LimitReached, TextDelta, ToolFinished, ToolStarted, TurnComplete
from ..config import Config
from ..providers import get_provider
from ..tools import default_registry


class ContextInspector(Static):
    """Shows every message and whether it's pinned / excluded / in-context."""

    def refresh_view(self, agent: Agent) -> None:
        lines = ["[b]Context[/b]"]
        for i, msg in enumerate(agent.messages):
            mark = "📌" if i in agent.pinned else ("🚫" if i in agent.excluded else "  ")
            raw = msg.content or f"<{len(msg.tool_calls)} tool call(s)>"
            preview = raw[:28].replace("\n", " ")
            lines.append(f"{mark} [dim]{i:>2}[/dim] [cyan]{msg.role[:4]}[/cyan] {preview}")
        self.update("\n".join(lines))


class OllamaShellTUI(App):
    """The top-level Textual application."""

    CSS = """
    #body { height: 1fr; }
    #conversation { width: 2fr; border: round $accent; padding: 0 1; }
    #sidebar { width: 1fr; }
    #context { height: 1fr; border: round $secondary; padding: 0 1; }
    #toollog { height: 1fr; border: round $warning; padding: 0 1; }
    Input { dock: bottom; }
    """
    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def __init__(self, agent: Agent):
        super().__init__()
        self.agent = agent

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            yield RichLog(id="conversation", wrap=True, markup=True, highlight=True)
            with Vertical(id="sidebar"):
                yield ContextInspector(id="context")
                yield RichLog(id="toollog", wrap=True, markup=True)
        yield Input(placeholder="Message the model…  (Ctrl+C to quit)")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Ollama Shell"
        self.sub_title = f"{self.agent.model}  ·  local-first"
        self._inspector().refresh_view(self.agent)
        networked = [t.name for t in self.agent.registry.active() if not t.local_only]
        banner = (
            f"[green]Local-first.[/] Network tools: {', '.join(networked)}"
            if networked
            else "[green]Fully local — no networked tools active.[/]"
        )
        self._conversation().write(banner)

    # ── widget shortcuts ─────────────────────────────────────────────────────
    def _conversation(self) -> RichLog:
        return self.query_one("#conversation", RichLog)

    def _toollog(self) -> RichLog:
        return self.query_one("#toollog", RichLog)

    def _inspector(self) -> ContextInspector:
        return self.query_one("#context", ContextInspector)

    # ── input handling ───────────────────────────────────────────────────────
    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        if not text:
            return
        self._conversation().write(f"[bold green]›[/] {text}")
        self._run_turn(text)

    def _run_turn(self, text: str) -> None:
        """Kick off the agent in a thread; events come back via call_from_thread."""
        self.run_worker(lambda: self._worker(text), thread=True, exclusive=True)

    def _worker(self, text: str) -> None:
        convo, tools = self._conversation(), self._toollog()
        buffer: list[str] = []
        for event in self.agent.send(text):
            if isinstance(event, TextDelta):
                buffer.append(event.text)
            elif isinstance(event, ToolStarted):
                self.call_from_thread(tools.write, f"[dim]⚙ {event.name}({event.arguments})[/dim]")
            elif isinstance(event, ToolFinished):
                preview = event.result.replace("\n", " ")[:80]
                self.call_from_thread(tools.write, f"[dim]  ↳ {preview}[/dim]")
            elif isinstance(event, TurnComplete):
                self.call_from_thread(convo.write, "".join(buffer) or "[dim](no text)[/dim]")
            elif isinstance(event, LimitReached):
                self.call_from_thread(
                    convo.write, f"[red]Stopped after {event.iterations} tool rounds.[/red]"
                )
        self.call_from_thread(self._inspector().refresh_view, self.agent)


def run_tui(model: str | None = None) -> None:
    config = Config.load()
    provider = get_provider(config)
    registry = default_registry(provider, config)
    agent = Agent(provider, registry, config, model=model)
    OllamaShellTUI(agent).run()
