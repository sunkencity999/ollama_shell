"""Command-line entrypoint for the reimagined shell (``oshell``).

Subcommands:
    oshell chat            interactive agent chat (default)
    oshell ask "..."       one-shot question, prints the answer
    oshell models          list models on the configured backend
    oshell config          show the resolved configuration
    oshell tui             launch the Textual workspace (needs [tui] extra)

Design notes: the CLI is a *thin* renderer over ``Agent`` events. It owns no
chat logic — that lives in :mod:`oshell.agent`.
"""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agent import Agent, LimitReached, TextDelta, ToolFinished, ToolStarted, TurnComplete
from .config import Config
from .providers import get_provider
from .tools import default_registry

app = typer.Typer(
    help="Ollama Shell — a local-first, agentic shell for Ollama.",
    add_completion=False,
)
console = Console()

# Local LoRA fine-tuning lives in its own subcommand group: `oshell finetune ...`
from .finetune.cli import finetune_app  # noqa: E402 - after app exists, before commands

app.add_typer(finetune_app, name="finetune")


def _build_agent(config: Config, model: str | None) -> Agent:
    provider = get_provider(config)
    registry = default_registry(provider, config)
    return Agent(provider, registry, config, model=model)


def _privacy_banner(agent: Agent) -> Panel:
    """Make the local-first guarantee explicit and auditable."""
    networked = [t.name for t in agent.registry.active() if not t.local_only]
    if networked:
        body = (
            "[bold green]Local-first[/]: the model runs on this machine.\n"
            f"[yellow]Network-capable tools active[/]: {', '.join(networked)} "
            "(only run when the model calls them)."
        )
    else:
        body = "[bold green]Fully local[/]: no active tool reaches the network."
    return Panel(body, title="privacy", border_style="green", expand=False)


def _render_turn(agent: Agent, text: str) -> None:
    """Stream one turn to the console, rendering tool activity inline."""
    streaming = False
    for event in agent.send(text):
        if isinstance(event, TextDelta):
            console.print(event.text, end="")
            streaming = True
        elif isinstance(event, ToolStarted):
            if streaming:
                console.print()
                streaming = False
            console.print(f"[dim]⚙ {event.name}({event.arguments})[/dim]")
        elif isinstance(event, ToolFinished):
            preview = event.result.replace("\n", " ")[:120]
            console.print(f"[dim]  ↳ {preview}[/dim]")
        elif isinstance(event, TurnComplete):
            console.print()
        elif isinstance(event, LimitReached):
            console.print(f"\n[red]Stopped after {event.iterations} tool rounds.[/red]")


SLASH_HELP = """\
[bold]Commands[/bold]
  /help            show this help
  /models          list available models
  /context         show pinned / excluded message indices
  /pin N           pin message N (keep in context)
  /exclude N       drop message N from context
  /tools           list active tools
  /exit, /quit     leave
"""


def _handle_slash(agent: Agent, line: str) -> bool:
    """Return True if the line was a handled command."""
    parts = line.split()
    cmd = parts[0]
    if cmd in ("/exit", "/quit"):
        raise typer.Exit()
    if cmd == "/help":
        console.print(Panel(SLASH_HELP, border_style="cyan", expand=False))
    elif cmd == "/models":
        console.print("\n".join(agent.provider.list_models()))
    elif cmd == "/tools":
        for t in agent.registry.active():
            tag = "" if t.local_only else " [yellow](network)[/yellow]"
            console.print(f"  [bold]{t.name}[/bold]{tag} — {t.description}")
    elif cmd == "/context":
        console.print(f"pinned={sorted(agent.pinned)}  excluded={sorted(agent.excluded)}")
    elif cmd in ("/pin", "/exclude") and len(parts) == 2 and parts[1].isdigit():
        idx = int(parts[1])
        try:
            (agent.pin if cmd == "/pin" else agent.exclude)(idx)
            console.print(f"[green]ok[/green] {cmd} {idx}")
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
    else:
        console.print(f"[red]unknown command:[/red] {line}  (try /help)")
    return True


@app.command()
def chat(
    model: str = typer.Option(None, "--model", "-m", help="Override the default model"),
) -> None:
    """Interactive agent chat (this is the default command)."""
    config = Config.load()
    agent = _build_agent(config, model)
    console.print(
        Panel.fit(
            f"[bold cyan]Ollama Shell[/] · model [bold]{agent.model}[/]",
            border_style="cyan",
        )
    )
    console.print(_privacy_banner(agent))
    console.print("[dim]Type a message, or /help for commands.[/dim]\n")

    while True:
        try:
            line = console.input("[bold green]›[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye[/dim]")
            break
        if not line:
            continue
        if line.startswith("/"):
            try:
                _handle_slash(agent, line)
            except typer.Exit:
                console.print("[dim]bye[/dim]")
                break
            continue
        _render_turn(agent, line)


@app.command()
def ask(prompt: str, model: str = typer.Option(None, "--model", "-m")) -> None:
    """One-shot: ask a single question and print the answer."""
    config = Config.load()
    agent = _build_agent(config, model)
    _render_turn(agent, prompt)


@app.command()
def models() -> None:
    """List models available on the configured backend."""
    config = Config.load()
    provider = get_provider(config)
    table = Table(title=f"Models on {config.provider.name} ({config.provider.host})")
    table.add_column("name")
    for name in provider.list_models():
        table.add_row(name)
    console.print(table)


_SECRET_HINT = ("token", "key", "secret", "password", "api_key")


def _redact(obj):
    """Recursively mask secret-looking values so `config` never prints creds."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(v, str) and v and any(h in k.lower() for h in _SECRET_HINT):
                out[k] = f"***redacted ({len(v)} chars)***"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    return obj


@app.command()
def config() -> None:
    """Show the resolved configuration (secrets redacted) and available capabilities."""
    cfg = Config.load()
    console.print_json(data=_redact(cfg.model_dump()))

    from rich.markup import escape

    from .capabilities import optional_features

    table = Table(title="Optional capabilities")
    table.add_column("feature")
    table.add_column("status")
    for cap in optional_features(cfg):
        mark = "[green]✓[/green]" if cap.available else "[dim]✗[/dim]"
        # escape: detail may contain "[web]" etc., which Rich would treat as markup
        table.add_row(f"{mark} {escape(cap.name)}", escape(cap.detail))
    console.print(table)


@app.command()
def tui(model: str = typer.Option(None, "--model", "-m")) -> None:
    """Launch the Textual workspace (requires: pip install 'ollama-shell[tui]')."""
    try:
        from .tui.app import run_tui
    except ImportError:
        console.print("[red]TUI needs the 'tui' extra:[/red] pip install 'ollama-shell[tui]'")
        raise typer.Exit(code=1) from None
    run_tui(model=model)


@app.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:
    """Run ``chat`` when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        chat(model=None)


def main() -> None:  # console-script friendly
    app()


if __name__ == "__main__":
    sys.exit(app())
