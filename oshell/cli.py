"""Command-line entrypoint for the reimagined shell (``oshell``).

Subcommands:
    oshell chat            interactive agent chat (default; --resume ID|last)
    oshell resume [ID]     pick up where you left off (most recent session)
    oshell sessions        list saved sessions (rm to delete)
    oshell ask "..."       one-shot question; piped stdin becomes context
    oshell do "..."        propose a shell command, confirm, run it
    oshell models          list/pull/delete models on the backend
    oshell doctor          health-check the whole rig
    oshell init zsh        print shell integration (Ctrl+G widget & more)
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

from .agent import (
    Agent,
    Compacted,
    LimitReached,
    TextDelta,
    ToolFinished,
    ToolStarted,
    TurnComplete,
)
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


def _cli_approver(call) -> bool:
    """Confirm a sensitive tool call at the prompt (approvals: ask)."""
    from rich.markup import escape

    args = ", ".join(f"{k}={v!r}" for k, v in call.arguments.items())
    console.print(
        Panel(
            escape(f"{call.name}({args})"),
            title="[yellow]the model wants to run this[/yellow]",
            border_style="yellow",
            expand=False,
        )
    )
    try:
        return typer.confirm("Allow it?", default=False)
    except (typer.Abort, EOFError):  # non-interactive stdin → fail safe
        console.print("[dim]denied (no interactive confirmation available)[/dim]")
        return False


def _build_agent(config: Config, model: str | None, interactive: bool = True) -> Agent:
    from .memory import MemoryStore

    provider = get_provider(config)
    m = model or config.default_model
    memory = MemoryStore(config.memory.path)
    registry = default_registry(provider, config, model=m, memory=memory)
    return Agent(
        provider,
        registry,
        config,
        model=m,
        memory=memory,
        approver=_cli_approver if interactive else None,
    )


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
        elif isinstance(event, Compacted):
            console.print(
                f"[dim]✂ compacted {event.dropped} older messages into a "
                f"{event.summary_chars}-char summary to free context[/dim]"
            )
        elif isinstance(event, TurnComplete):
            console.print()
        elif isinstance(event, LimitReached):
            console.print(
                f"\n[yellow]Reached the {event.iterations}-round tool limit — "
                "wrapping up with what I have.[/yellow]"
            )


SLASH_HELP = """\
[bold]Commands[/bold]
  /help            show this help
  /models          list available models
  /pull NAME       download a model (live progress)
  /rm NAME         delete a model from the backend
  /route [on|off]  automatic model routing (fast/deep/vision per message)
  /approvals [M]   tool approvals: auto | ask | read-only
  /compact         summarize older turns to free context (auto at 85%)
  /undo            restore the last file the model overwrote/created
  /context         show pinned / excluded message indices
  /pin N           pin message N (keep in context)
  /exclude N       drop message N from context
  /tools           list active tools
  /commands        list your custom commands (~/.oshell/commands/*.md)
  /daydream        let the model wander and free-associate 💭
  /exit, /quit     leave

Any ~/.oshell/commands/NAME.md is also a command: /NAME [args]
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
    elif cmd == "/pull" and len(parts) == 2:
        try:
            _pull_with_progress(agent.provider, parts[1])
        except Exception as exc:
            console.print(f"[red]{exc}[/red]")
    elif cmd == "/rm" and len(parts) == 2:
        name = parts[1]
        if name == agent.model:
            console.print("[yellow]That's the active model — switch first, then delete.[/yellow]")
            return True
        if typer.confirm(f"Delete {name} from the backend?"):
            try:
                agent.provider.delete_model(name)
                console.print(f"[green]✓[/green] deleted {name}")
            except Exception as exc:
                console.print(f"[red]{exc}[/red]")
    elif cmd == "/tools":
        for t in agent.registry.active():
            tag = "" if t.local_only else " [yellow](network)[/yellow]"
            console.print(f"  [bold]{t.name}[/bold]{tag} — {t.description}")
    elif cmd == "/context":
        console.print(f"pinned={sorted(agent.pinned)}  excluded={sorted(agent.excluded)}")
    elif cmd in ("/daydream", "/dream"):
        from . import fun

        if not agent.config.fun.daydreams:
            console.print("[dim]Daydreams are disabled.[/dim]")
            return True
        messages = fun.build_daydream_messages(agent.messages, fun.pick_motif())
        console.print("[magenta]💭[/magenta] ", end="")
        for piece in fun.daydream(agent.provider, agent.model, messages):
            console.print(f"[italic dim]{piece}[/italic dim]", end="")
        console.print()
    elif cmd in ("/pin", "/exclude") and len(parts) == 2 and parts[1].isdigit():
        idx = int(parts[1])
        try:
            (agent.pin if cmd == "/pin" else agent.exclude)(idx)
            console.print(f"[green]ok[/green] {cmd} {idx}")
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
    elif cmd == "/route":
        rcfg = agent.config.routing
        if len(parts) == 2 and parts[1] in ("on", "off"):
            rcfg.enabled = parts[1] == "on"
            from .config import update_local_config

            try:
                update_local_config({"routing": {"enabled": rcfg.enabled}})
            except Exception:  # pragma: no cover - defensive
                pass
        state = "[green]on[/green]" if rcfg.enabled else "[dim]off[/dim]"
        slots = (
            f"fast={rcfg.fast_model or '—'}  deep={rcfg.deep_model or '—'}  "
            f"vision={rcfg.vision_model or '—'}"
        )
        console.print(f"routing {state}  {slots}")
        if rcfg.enabled and not any((rcfg.fast_model, rcfg.deep_model, rcfg.vision_model)):
            console.print(
                "[yellow]No routing models configured — set routing.fast_model / "
                "deep_model / vision_model in config.[/yellow]"
            )
    elif cmd == "/approvals":
        modes = ("auto", "ask", "read-only")
        if len(parts) == 2 and parts[1] in modes:
            agent.config.approvals = parts[1]
            from .config import update_local_config

            try:
                update_local_config({"approvals": parts[1]})
            except Exception:  # pragma: no cover - defensive
                pass
        elif len(parts) == 2:
            console.print(f"[red]unknown mode:[/red] {parts[1]}  (try {', '.join(modes)})")
            return True
        mode = agent.config.approvals
        notes = {
            "auto": "everything runs without asking",
            "ask": "sensitive tools (shell, GUI) confirm with you first",
            "read-only": "sensitive tools are hidden from the model",
        }
        console.print(f"approvals: [bold]{mode}[/bold] — {notes.get(mode, '')}")
    elif cmd == "/compact":
        info = agent.compact()
        if info:
            console.print(
                f"[green]✂[/green] compacted {info.dropped} messages "
                f"into a {info.summary_chars}-char summary "
                f"(context now {agent.context_fill():.0%} full)"
            )
        else:
            console.print("[dim]Nothing to compact yet.[/dim]")
    elif cmd == "/undo":
        from . import checkpoints

        try:
            console.print(f"[green]↩[/green] {checkpoints.undo_last()}")
        except FileNotFoundError as exc:
            console.print(f"[dim]{exc}[/dim]")
        except Exception as exc:
            console.print(f"[red]undo failed: {exc}[/red]")
    elif cmd == "/commands":
        from . import commands as custom

        found = custom.list_commands()
        if not found:
            console.print(
                f"[dim]No custom commands yet — drop a .md file in {custom.DEFAULT_DIR} "
                "and it becomes /<name>.[/dim]"
            )
        for name, path in found.items():
            console.print(f"  [bold]/{name}[/bold]  [dim]{path}[/dim]")
    else:
        from . import commands as custom

        rendered = custom.render(cmd[1:], line[len(cmd) :].strip())
        if rendered is not None:
            _render_turn(agent, rendered)
            return True
        console.print(f"[red]unknown command:[/red] {line}  (try /help)")
    return True


def _autosave(agent: Agent, sid: str) -> None:
    """Persist the running conversation to the named-session store (best-effort)."""
    if not agent.config.session.persist:
        return
    if not any(m.role == "user" for m in agent.messages):
        return  # nothing worth keeping yet
    from . import sessions as sessions_mod

    try:
        sessions_mod.save(
            agent.messages,
            sid=sid,
            model=agent.model,
            directory=agent.config.session.dir,
            max_messages=agent.config.session.max_messages,
        )
    except OSError:  # pragma: no cover - disk full / permissions
        pass


def _maybe_route(agent: Agent, text: str, has_images: bool = False) -> None:
    """Switch models for this message when routing says so, with a visible note."""
    from .routing import pick_model

    routed = pick_model(text, has_images, agent.config.routing, agent.model)
    if routed:
        agent.model = routed[0]
        console.print(f"[dim]→ {routed[0]} ({routed[1]})[/dim]")


@app.command()
def chat(
    model: str = typer.Option(None, "--model", "-m", help="Override the default model"),
    resume: str = typer.Option(
        None,
        "--resume",
        "-r",
        help="Resume a saved session: an id (or unique prefix), or 'last'",
    ),
) -> None:
    """Interactive agent chat (this is the default command)."""
    from . import sessions as sessions_mod

    config = Config.load()
    sid = sessions_mod.new_id()
    resumed = ""
    prior: list = []
    if resume:
        try:
            target = sessions_mod.latest_id(config.session.dir) if resume == "last" else resume
            if target is None:
                raise FileNotFoundError("no saved sessions yet")
            meta, prior = sessions_mod.load(target, config.session.dir)
            sid = meta["id"]  # keep appending to the same session
            if not model and meta.get("model"):
                model = meta["model"]  # come back to the model you left with
            resumed = f" · resumed [bold]{meta['id']}[/] ({len(prior)} messages)"
        except (FileNotFoundError, ValueError) as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from None

    agent = _build_agent(config, model)
    agent.messages.extend(prior)

    console.print(
        Panel.fit(
            f"[bold cyan]Ollama Shell[/] · model [bold]{agent.model}[/]{resumed}",
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
            _autosave(agent, sid)  # custom commands can add turns
            continue
        _maybe_route(agent, line)
        _render_turn(agent, line)
        _autosave(agent, sid)


@app.command()
def resume(
    session_id: str = typer.Argument(None, help="Session id or unique prefix (default: last)"),
    model: str = typer.Option(None, "--model", "-m"),
) -> None:
    """Pick up where you left off — the most recent session, or SESSION_ID."""
    chat(model=model, resume=session_id or "last")


_PIPE_LIMIT = 12_000  # chars of piped stdin to keep (the tail — errors live there)


@app.command()
def ask(
    prompt: str,
    model: str = typer.Option(None, "--model", "-m"),
    json_out: bool = typer.Option(
        False, "--json", help="Emit {answer, model, tools} as JSON (for scripts/CI)"
    ),
) -> None:
    """One-shot question. Piped stdin becomes context: cat err.log | oshell ask "why?" """
    config = Config.load()
    # JSON mode is for machines: no approver (sensitive tools fail safe under
    # "ask"), no rich rendering, structured output only.
    agent = _build_agent(config, model, interactive=not json_out)
    if not sys.stdin.isatty():
        piped = sys.stdin.read().strip()
        if piped:
            clipped = piped[-_PIPE_LIMIT:]
            note = (
                f"[first {len(piped) - _PIPE_LIMIT} chars truncated]\n"
                if len(piped) > _PIPE_LIMIT
                else ""
            )
            prompt = f"{prompt}\n\nPiped input:\n```\n{note}{clipped}\n```"
    if json_out:
        import json as _json

        from .routing import pick_model

        routed = pick_model(prompt, False, config.routing, agent.model)
        if routed:
            agent.model = routed[0]
        answer, tools_used = "", []
        for event in agent.send(prompt):
            if isinstance(event, ToolStarted):
                tools_used.append({"name": event.name, "arguments": event.arguments})
            elif isinstance(event, ToolFinished) and tools_used:
                tools_used[-1]["result_preview"] = event.result[:400]
            elif isinstance(event, TurnComplete):
                answer = event.text
        print(_json.dumps({"answer": answer, "model": agent.model, "tools": tools_used}))
        return
    _maybe_route(agent, prompt)
    _render_turn(agent, prompt)


models_app = typer.Typer(help="List and manage models on the configured backend.")
app.add_typer(models_app, name="models")


def _pull_with_progress(provider, name: str) -> None:
    """Stream a model download to the console as a live progress bar."""
    from rich.progress import (
        BarColumn,
        DownloadColumn,
        Progress,
        TextColumn,
        TransferSpeedColumn,
    )

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(name, total=None)
        for step in provider.pull_model(name):
            # Bookkeeping steps ("verifying sha256", "success") carry no byte
            # counts — keep the last layer's numbers on screen instead of
            # resetting the bar.
            kwargs: dict = {"description": step.status or name}
            if step.total is not None:
                kwargs["total"] = step.total
            if step.completed is not None:
                kwargs["completed"] = step.completed
            progress.update(task, **kwargs)
    console.print(f"[green]✓[/green] pulled {name}")


@models_app.callback(invoke_without_command=True)
def models(ctx: typer.Context) -> None:
    """List models available on the configured backend."""
    if ctx.invoked_subcommand is not None:
        return
    config = Config.load()
    provider = get_provider(config)
    table = Table(title=f"Models on {config.provider.name} ({config.provider.host})")
    table.add_column("name")
    table.add_column("params")
    table.add_column("quant")
    table.add_column("disk")
    for info in provider.list_models_info():
        table.add_row(
            info["name"],
            info.get("size", ""),
            info.get("quant", ""),
            info.get("disk", ""),
        )
    console.print(table)


@models_app.command("pull")
def models_pull(name: str) -> None:
    """Download a model (e.g. `oshell models pull qwen3:8b`)."""
    provider = get_provider(Config.load())
    try:
        _pull_with_progress(provider, name)
    except Exception as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from None


@models_app.command("rm")
def models_rm(
    name: str,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
) -> None:
    """Delete a model from the backend (frees its disk space)."""
    provider = get_provider(Config.load())
    if not yes and not typer.confirm(f"Delete {name} from the backend?"):
        raise typer.Exit()
    try:
        provider.delete_model(name)
    except Exception as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from None
    console.print(f"[green]✓[/green] deleted {name}")


sessions_app = typer.Typer(help="List and manage saved chat sessions.")
app.add_typer(sessions_app, name="sessions")


@sessions_app.callback(invoke_without_command=True)
def sessions(ctx: typer.Context) -> None:
    """List saved sessions (newest first)."""
    if ctx.invoked_subcommand is not None:
        return
    from . import sessions as sessions_mod

    config = Config.load()
    found = sessions_mod.list_sessions(config.session.dir)
    if not found:
        console.print("[dim]No saved sessions yet — chat once and it'll be here.[/dim]")
        return
    table = Table(title=f"Sessions ({config.session.dir})")
    table.add_column("id")
    table.add_column("title")
    table.add_column("model")
    table.add_column("updated")
    table.add_column("msgs", justify="right")
    for s in found:
        table.add_row(s["id"], s["title"], s["model"], s["updated"], str(s["messages"]))
    console.print(table)
    console.print("[dim]Resume one: oshell resume <id>   (or just: oshell resume)[/dim]")


@sessions_app.command("rm")
def sessions_rm(session_id: str) -> None:
    """Delete a saved session."""
    from . import sessions as sessions_mod

    try:
        sessions_mod.delete(session_id, Config.load().session.dir)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from None
    console.print(f"[green]✓[/green] deleted {session_id}")


_DO_SYSTEM = (
    "You translate a user's task into EXACTLY ONE shell command for {os} ({shell}). "
    "Output ONLY the command — no backticks, no prose, no explanations. Prefer safe, "
    "non-destructive commands; never invent destructive flags the task didn't ask for. "
    "If the task is impossible or too dangerous for one command, output exactly: "
    "CANNOT: <one-line reason>"
)
_DO_HISTORY = "~/.oshell/do_history.jsonl"


def _do_examples(limit: int = 5) -> str:
    """Recent successful task→command pairs, as few-shot context for `oshell do`."""
    import json as _json
    from pathlib import Path

    path = Path(_DO_HISTORY).expanduser()
    if not path.is_file():
        return ""
    good = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = _json.loads(line)
        except _json.JSONDecodeError:  # pragma: no cover - defensive
            continue
        if entry.get("rc") == 0:
            good.append(f"task: {entry['task']}\ncommand: {entry['command']}")
    if not good:
        return ""
    return "\n\nCommands that worked for this user before:\n" + "\n".join(good[-limit:])


def _record_do(task: str, command: str, rc: int) -> None:
    import json as _json
    import time
    from pathlib import Path

    path = Path(_DO_HISTORY).expanduser()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"ts": time.strftime("%Y-%m-%d %H:%M"), "task": task, "command": command, "rc": rc}
        with path.open("a", encoding="utf-8") as f:
            f.write(_json.dumps(entry) + "\n")
    except OSError:  # pragma: no cover - defensive
        pass


@app.command()
def do(
    task: str,
    model: str = typer.Option(None, "--model", "-m", help="Override the model"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Run without confirming (bold move)"),
) -> None:
    """Turn TASK into a shell command: propose → confirm (y/e/n) → run."""
    import os
    import platform
    import subprocess

    from .providers.base import Message

    config = Config.load()
    provider = get_provider(config)
    m = model or config.routing.deep_model or config.default_model

    cwd = os.getcwd()
    try:
        entries = ", ".join(sorted(os.listdir(cwd))[:40])
    except OSError:  # pragma: no cover - defensive
        entries = ""
    system = _DO_SYSTEM.format(
        os=platform.system(), shell=os.environ.get("SHELL", "/bin/sh")
    ) + _do_examples()
    user = f"Working directory: {cwd}\nDirectory contents: {entries}\n\nTask: {task}"

    with console.status(f"[dim]thinking ({m})…[/dim]"):
        reply = "".join(
            c.content
            for c in provider.chat(
                [Message(role="system", content=system), Message(role="user", content=user)],
                model=m,
                stream=False,
                temperature=0.2,
            )
        )
    command = reply.strip().strip("`").removeprefix("bash\n").removeprefix("sh\n").strip()
    if not command:
        console.print("[red]The model returned nothing usable.[/red]")
        raise typer.Exit(code=1)
    if command.upper().startswith("CANNOT:"):
        console.print(f"[yellow]{command[7:].strip()}[/yellow]")
        raise typer.Exit(code=1)
    if "\n" in command:
        command = command.splitlines()[0].strip()  # one command means one command

    console.print(Panel(command, title="proposed", border_style="cyan", expand=False))
    if not yes:
        choice = typer.prompt("Run it? [y]es / [e]dit / [n]o", default="n").lower()
        if choice.startswith("e"):
            command = typer.prompt("command", default=command)
        elif not choice.startswith("y"):
            console.print("[dim]cancelled[/dim]")
            raise typer.Exit()
    rc = subprocess.run(command, shell=True).returncode
    _record_do(task, command, rc)
    if rc == 0:
        console.print(
            "[green]✓ done[/green] [dim](remembered — future suggestions learn from it)[/dim]"
        )
    else:
        console.print(f"[red]exit {rc}[/red]")
        raise typer.Exit(code=rc)


_ZSH_SNIPPET = r"""# oshell shell integration — add to ~/.zshrc:  eval "$(oshell init zsh)"

# Ctrl+G: summon oshell with whatever is on your command line as the question.
# Empty line -> opens interactive chat.
_oshell_ask_widget() {
  local q="$BUFFER"
  BUFFER=""
  zle -I
  if [[ -n "$q" ]]; then
    oshell ask "$q" </dev/tty
  else
    oshell </dev/tty
  fi
  zle reset-prompt
}
zle -N _oshell_ask_widget
bindkey '^G' _oshell_ask_widget

# Unknown command? Point at the assistant instead of a dead end.
command_not_found_handler() {
  echo "zsh: command not found: $1" >&2
  echo "  ↳ try: oshell do \"$*\"" >&2
  return 127
}
"""


@app.command()
def init(shell: str = typer.Argument("zsh", help="Shell to integrate (zsh)")) -> None:
    """Print shell integration: eval "$(oshell init zsh)" in your ~/.zshrc."""
    if shell != "zsh":
        console.print(f"[red]Only zsh is supported so far (got: {shell}).[/red]")
        raise typer.Exit(code=1)
    print(_ZSH_SNIPPET)


@app.command()
def setup() -> None:
    """First-run wizard: size models to this machine, configure routing."""
    from .setup import run_wizard

    raise typer.Exit(code=run_wizard(console))


@app.command()
def doctor() -> None:
    """Health-check the rig: backend, models, routing, sessions, features."""
    from pathlib import Path

    from rich.markup import escape

    from . import commands as custom
    from . import sessions as sessions_mod
    from .capabilities import optional_features

    cfg = Config.load()
    provider = get_provider(cfg)
    table = Table(title="oshell doctor")
    table.add_column("check")
    table.add_column("status")
    ok, warn, bad = "[green]✓[/green]", "[yellow]![/yellow]", "[red]✗[/red]"
    healthy = True

    if provider.health():
        table.add_row(f"{ok} backend", f"{cfg.provider.name} at {cfg.provider.host}")
        names = provider.list_models()
        if names:
            table.add_row(f"{ok} models", f"{len(names)} installed")
        else:
            table.add_row(f"{warn} models", "none installed — try: oshell models pull qwen3:8b")
        if cfg.default_model in names:
            table.add_row(f"{ok} default model", cfg.default_model)
        else:
            table.add_row(
                f"{warn} default model",
                f"{cfg.default_model} is not installed"
                + (f" — closest: {names[0]}" if names else ""),
            )
    else:
        healthy = False
        table.add_row(f"{bad} backend", f"{cfg.provider.host} unreachable — is Ollama running?")

    approvals_note = {
        "auto": "everything runs unprompted",
        "ask": "sensitive tools confirm first",
        "read-only": "sensitive tools hidden",
    }.get(cfg.approvals, "unknown mode!")
    mark = ok if cfg.approvals in ("auto", "ask", "read-only") else warn
    table.add_row(f"{mark} approvals", f"{cfg.approvals} — {approvals_note}")

    rcfg = cfg.routing
    if rcfg.enabled:
        slots = [s for s in (rcfg.fast_model, rcfg.deep_model, rcfg.vision_model) if s]
        mark = ok if slots else warn
        table.add_row(f"{mark} routing", f"on ({len(slots)}/3 slots configured)")
    else:
        table.add_row(f"{ok} routing", "off (enable with /route on)")

    n_sessions = len(sessions_mod.list_sessions(cfg.session.dir))
    table.add_row(f"{ok} sessions", f"{n_sessions} saved in {cfg.session.dir}")
    n_cmds = len(custom.list_commands())
    table.add_row(f"{ok} custom commands", f"{n_cmds} in {custom.DEFAULT_DIR}")
    mem_path = Path(cfg.memory.path).expanduser()
    table.add_row(
        f"{ok} memory",
        f"{cfg.memory.path}" + ("" if mem_path.exists() else " (empty — will be created)"),
    )
    console.print(table)

    feats = Table(title="Optional capabilities")
    feats.add_column("feature")
    feats.add_column("status")
    for cap in optional_features(cfg):
        mark = "[green]✓[/green]" if cap.available else "[dim]✗[/dim]"
        feats.add_row(f"{mark} {escape(cap.name)}", escape(cap.detail))
    console.print(feats)
    if not healthy:
        raise typer.Exit(code=1)


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
        chat(model=None, resume=None)


def main() -> None:  # console-script friendly
    app()


if __name__ == "__main__":
    sys.exit(app())
