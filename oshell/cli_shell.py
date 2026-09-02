"""The shell-as-conversation commands: ``do`` · ``explain`` · ``code`` · ``fix``
· ``roles`` · ``init``.

These are the sgpt lineage (see :mod:`oshell.shellops` for the logic). They
are registered onto the main Typer app by :func:`register`, keeping ``cli.py``
a thin renderer while this file owns the *interaction*: the
run / edit / describe / chat / no loop that makes proposing a command safe
enough to be fast.
"""

from __future__ import annotations

import subprocess
import sys

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from . import roles as roles_mod
from . import shellinit, shellops
from .config import Config
from .providers import get_provider

_PIPE_LIMIT = 12_000  # chars of piped stdin to keep (the tail — errors live there)


def _piped_stdin() -> str:
    if sys.stdin.isatty():
        return ""
    data = sys.stdin.read().strip()
    return data[-_PIPE_LIMIT:]


def _pick_model(config: Config, override: str | None) -> str:
    # Command generation is precision work: prefer the routing "deep" slot.
    return override or config.routing.deep_model or config.default_model


def _run_and_record(console: Console, task: str, command: str) -> int:
    from .tools.system import shell_invocation

    # POSIX: /bin/sh -c; Windows: PowerShell (or cmd if configured) — the same
    # rule the run_command tool uses, so what the model proposed runs where it said.
    args, use_shell = shell_invocation(command, windows_shell=Config.load().shell.windows_shell)
    rc = subprocess.run(args, shell=use_shell).returncode
    shellops.record_do(task, command, rc)
    shellops.record_last_command(command, rc)
    if rc == 0:
        console.print(
            "[oshell.ok]✓ done[/] [oshell.muted](remembered — future proposals learn from it)[/]"
        )
    else:
        console.print(f"[oshell.err]exit {rc}[/]  [oshell.muted]→ oshell fix[/]")
    return rc


def _confirm_loop(
    console: Console,
    provider,
    model: str,
    task: str,
    command: str,
    *,
    allow_chat: bool = True,
) -> str | None:
    """The sgpt flow, grown up: run / edit / describe / chat / no.

    Returns the command to run, or None if the user backed out.
    """
    while True:
        warn = ""
        if shellops.is_destructive(command):
            warn = "  [oshell.err]⚠ destructive pattern[/]"
        console.print(
            Panel(
                f"[oshell.cmd]{escape(command)}[/]",
                title=f"[oshell.accent]proposed[/]{warn}",
                border_style="oshell.border",
                expand=False,
                padding=(0, 2),
            )
        )
        keys = "[oshell.accent]r[/]un · [oshell.accent]e[/]dit · [oshell.accent]d[/]escribe"
        if allow_chat:
            keys += " · [oshell.accent]c[/]hat"
        keys += " · [oshell.accent]n[/]o"
        console.print(f"  {keys}", end="")
        try:
            choice = typer.prompt("", default="n", show_default=False, prompt_suffix=" ❯ ").lower()
        except (typer.Abort, EOFError):
            console.print("\n[oshell.muted]cancelled[/]")
            return None
        if choice.startswith("r") or choice.startswith("y"):
            return command
        if choice.startswith("e"):
            command = typer.prompt("command", default=command)
            continue
        if choice.startswith("d"):
            with console.status("[oshell.muted]describing…[/]"):
                desc = shellops.describe_command(provider, model, command)
            console.print(Panel(Markdown(desc), border_style="oshell.border.soft", expand=False))
            continue
        if choice.startswith("c") and allow_chat:
            from .cli import _build_agent, _render_turn

            agent = _build_agent(Config.load(), model)
            console.print(
                "[oshell.muted]Chatting about it — say what to change (Ctrl+D to stop).[/]"
            )
            _render_turn(
                agent,
                f'For the task "{task}" you proposed this command:\n\n'
                f"    {command}\n\nBriefly say what it does and what you'd change, if anything.",
            )
            while True:
                try:
                    line = console.input("[oshell.prompt]❯[/] ").strip()
                except (EOFError, KeyboardInterrupt):
                    console.print()
                    break
                if not line:
                    break
                _render_turn(agent, line)
            revised = typer.prompt("command", default=command)
            command = revised
            continue
        console.print("[oshell.muted]cancelled[/]")
        return None


def register(app: typer.Typer, console: Console) -> None:
    """Attach the shell-conversation commands to ``app``."""

    @app.command()
    def do(
        task: str = typer.Argument(..., help="What you want done, in plain words"),
        model: str = typer.Option(None, "--model", "-m", help="Override the model"),
        yes: bool = typer.Option(False, "--yes", "-y", help="Run without confirming (bold move)"),
        print_only: bool = typer.Option(
            False, "--print", "-p", help="Print the proposed command only (for shell widgets)"
        ),
        role: str = typer.Option("shell", "--role", help="Role that writes the command"),
    ) -> None:
        """Turn TASK into a shell command: propose → run / edit / describe / chat / no.

        Piped stdin is context:  ls | oshell do "delete the .tmp ones"
        """
        config = Config.load()
        provider = get_provider(config)
        m = _pick_model(config, model)
        ctx = shellops.HostContext.gather(stdin=_piped_stdin())

        if print_only:
            command = shellops.propose_command(provider, m, task, ctx, shellops.do_examples(), role)
            if not command or command.startswith("CANNOT:"):
                print(command[7:].strip() if command else "no proposal", file=sys.stderr)
                raise typer.Exit(code=1)
            print(command)
            return

        with console.status(f"[oshell.muted]thinking ({m})…[/]"):
            command = shellops.propose_command(provider, m, task, ctx, shellops.do_examples(), role)
        if not command:
            console.print("[oshell.err]The model returned nothing usable.[/]")
            raise typer.Exit(code=1)
        if command.startswith("CANNOT:"):
            console.print(f"[oshell.warn]{escape(command[7:].strip())}[/]")
            raise typer.Exit(code=1)

        if yes and not shellops.is_destructive(command):
            console.print(f"[oshell.muted]$[/] [oshell.cmd]{escape(command)}[/]")
        else:
            chosen = _confirm_loop(console, provider, m, task, command)
            if chosen is None:
                raise typer.Exit()
            command = chosen
        rc = _run_and_record(console, task, command)
        if rc:
            raise typer.Exit(code=rc)

    @app.command()
    def explain(
        command: list[str] = typer.Argument(  # noqa: B008
            None, help="The command (default: the last one you ran)"
        ),
        model: str = typer.Option(None, "--model", "-m"),
    ) -> None:
        """Describe what a shell command does — flags, hazards, in ~80 words.

        With no argument, explains the last command you ran (needs `oshell init`).
        """
        config = Config.load()
        text = " ".join(command or []).strip()
        if not text:
            last = shellops.read_last_command()
            if last is None:
                console.print(
                    "[oshell.warn]No command given and none recorded.[/] "
                    '[oshell.muted]Add  eval "$(oshell init zsh)"  to your shell to track '
                    "the last one.[/]"
                )
                raise typer.Exit(code=1)
            text = last.command
            tag = "" if last.exit_code == 0 else f" [oshell.err](exit {last.exit_code})[/]"
            console.print(f"[oshell.muted]$[/] [oshell.cmd]{escape(text)}[/]{tag}")
        provider = get_provider(config)
        m = _pick_model(config, model)
        with console.status("[oshell.muted]reading it…[/]"):
            desc = shellops.describe_command(provider, m, text)
        console.print(Panel(Markdown(desc), border_style="oshell.border.soft", expand=False))

    @app.command()
    def code(
        prompt: str = typer.Argument(..., help="What to write"),
        lang: str = typer.Option(None, "--lang", "-l", help="Language (python, bash, sql…)"),
        model: str = typer.Option(None, "--model", "-m"),
    ) -> None:
        """Just the code — no fences, no prose. Redirect it:  oshell code "…" > x.py

        Piped stdin is input to work with:  cat data.csv | oshell code "parse this"
        """
        config = Config.load()
        provider = get_provider(config)
        m = _pick_model(config, model)
        stdin = _piped_stdin()
        if sys.stdout.isatty():
            with console.status(f"[oshell.muted]writing ({m})…[/]"):
                out = shellops.generate_code(provider, m, prompt, lang, stdin)
            from rich.syntax import Syntax

            console.print(
                Syntax(out.rstrip("\n"), lang or "text", theme="ansi_dark", word_wrap=True)
            )
        else:  # redirected: raw bytes, nothing else
            sys.stdout.write(shellops.generate_code(provider, m, prompt, lang, stdin))

    @app.command()
    def fix(
        model: str = typer.Option(None, "--model", "-m"),
        yes: bool = typer.Option(False, "--yes", "-y", help="Run the fix without confirming"),
    ) -> None:
        """Explain why the last command failed and propose a fix.

        Pipe the output in for a sharper diagnosis:  make 2>&1 | oshell fix
        (needs `oshell init` to know the last command; the pipe alone also works).
        """
        config = Config.load()
        output = _piped_stdin()
        last = shellops.read_last_command()
        if last is None and not output:
            console.print(
                "[oshell.warn]Nothing to fix yet.[/] [oshell.muted]Either pipe a failing command's "
                'output in (cmd 2>&1 | oshell fix) or add  eval "$(oshell init zsh)"  so the '
                "shell records the last command.[/]"
            )
            raise typer.Exit(code=1)
        command = last.command if last else "(unknown — see output)"
        rc = last.exit_code if last else None
        if last and last.exit_code == 0 and not output:
            console.print(
                f"[oshell.ok]The last command succeeded[/] [oshell.muted]({escape(command)})[/]"
            )
            return
        console.print(
            f"[oshell.muted]$[/] [oshell.cmd]{escape(command)}[/]"
            + (f"  [oshell.err]exit {rc}[/]" if rc not in (None, 0) else "")
        )
        provider = get_provider(config)
        m = _pick_model(config, model)
        with console.status(f"[oshell.muted]diagnosing ({m})…[/]"):
            diag = shellops.diagnose_failure(provider, m, command, rc, output)
        console.print(
            Panel(
                Markdown(diag.why),
                title="[oshell.accent]why[/]",
                border_style="oshell.border.soft",
                expand=False,
            )
        )
        if not diag.fix:
            console.print("[oshell.muted]No safe one-line fix to propose.[/]")
            return
        chosen = diag.fix
        if not (yes and not shellops.is_destructive(chosen)):
            picked = _confirm_loop(console, provider, m, f"fix: {command}", chosen)
            if picked is None:
                raise typer.Exit()
            chosen = picked
        code_ = _run_and_record(console, f"fix: {command}", chosen)
        if code_:
            raise typer.Exit(code=code_)

    roles_app = typer.Typer(help="Reusable system prompts (~/.oshell/roles/*.md).")
    app.add_typer(roles_app, name="roles")

    @roles_app.callback(invoke_without_command=True)
    def roles(ctx: typer.Context) -> None:
        """List roles: built-ins plus your ~/.oshell/roles/*.md (yours override)."""
        if ctx.invoked_subcommand is not None:
            return
        table = Table(title="roles", border_style="oshell.border.soft")
        table.add_column("name", style="oshell.accent")
        table.add_column("source")
        table.add_column("used by", style="oshell.muted")
        uses = {
            "shell": "oshell do",
            "describe": "oshell explain · \\[d]escribe",
            "code": "oshell code",
            "fix": "oshell fix",
            "default": "oshell ask (when no --role)",
        }
        for name, src in roles_mod.list_roles().items():
            table.add_row(name, escape(src), uses.get(name, "oshell ask --role " + name))
        console.print(table)
        console.print(
            f"[oshell.muted]New role:  oshell roles new NAME   → {roles_mod.DEFAULT_DIR}/NAME.md[/]"
        )

    @roles_app.command("new")
    def roles_new(name: str) -> None:
        """Scaffold ~/.oshell/roles/NAME.md and print its path."""
        try:
            path = roles_mod.create_role(name)
        except (ValueError, FileExistsError) as exc:
            console.print(f"[oshell.err]{exc}[/]")
            raise typer.Exit(code=1) from None
        console.print(
            f"[oshell.ok]✓[/] {path}  [oshell.muted](edit it, then: oshell ask --role {name} …)[/]"
        )

    @roles_app.command("show")
    def roles_show(name: str) -> None:
        """Print a role's prompt (placeholders filled for this machine)."""
        text = roles_mod.role_prompt(name)
        if text is None:
            console.print(f"[oshell.err]unknown role: {name}[/]")
            raise typer.Exit(code=1)
        console.print(
            Panel(
                escape(text),
                title=f"[oshell.accent]{name}[/]",
                border_style="oshell.border.soft",
                expand=False,
            )
        )

    @app.command()
    def init(
        shell: str = typer.Argument("zsh", help="zsh | bash | fish"),
        prompt: bool = typer.Option(False, "--prompt", help="Also install a small themed prompt"),
    ) -> None:
        """Print shell integration.  zsh: eval "$(oshell init zsh)"  fish: oshell init fish | source

        Ctrl+G asks about your line ('#…' lines become commands), the last
        command + exit status is recorded for `oshell fix`, and unknown commands
        point at `oshell do`.
        """
        try:
            print(shellinit.snippet(shell, prompt=prompt))
        except ValueError as exc:
            console.print(f"[oshell.err]{exc}[/]")
            raise typer.Exit(code=1) from None
