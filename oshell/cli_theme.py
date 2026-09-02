"""``oshell theme …`` · ``oshell fetch`` · ``oshell screensaver`` — the rice.

Registered onto the main Typer app by :func:`register`. The theme group is
the Omarchy idea in CLI form: one palette file, one command, every surface.
"""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.text import Text

from . import themes
from .config import Config


def register(app: typer.Typer, console: Console) -> None:
    theme_app = typer.Typer(help="Themes: list, set, import, export (Omarchy colors.toml format).")
    app.add_typer(theme_app, name="theme")

    def _current_name() -> str:
        return Config.load().theme

    @theme_app.callback(invoke_without_command=True)
    def theme(ctx: typer.Context) -> None:
        """Show the current theme (or run a subcommand)."""
        if ctx.invoked_subcommand is not None:
            return
        name = _current_name()
        p = themes.get_palette(name)
        line = Text()
        line.append("theme ", style="oshell.muted")
        line.append(name, style="oshell.accent")
        if p is not None:
            line.append("  ")
            line.append_text(themes.swatch(p))
            line.append(f"  {p.mode} · {p.source}", style="oshell.muted")
        else:
            line.append("  (Textual built-in — no palette to export)", style="oshell.muted")
        console.print(line)
        console.print("[oshell.muted]oshell theme list · set NAME · import SRC · export FMT[/]")

    @theme_app.command("list")
    def theme_list() -> None:
        """Every theme: bundled (Omarchy's 22), yours (~/.oshell/themes), Textual's."""
        current = _current_name()
        table = Table(border_style="oshell.border.soft", title="themes", title_style="oshell.title")
        table.add_column("")
        table.add_column("name", style="oshell.accent")
        table.add_column("palette")
        table.add_column("mode", style="oshell.muted")
        table.add_column("source", style="oshell.muted")
        for name, p in themes.list_palettes().items():
            mark = "●" if name == current else " "
            table.add_row(
                mark,
                name,
                themes.swatch(p),
                p.mode,
                "bundled" if p.source == "builtin" else escape(p.source),
            )
        try:
            from textual.theme import BUILTIN_THEMES

            for name in sorted(BUILTIN_THEMES):
                if name in themes.list_palettes():
                    continue
                mark = "●" if name == current else " "
                table.add_row(mark, name, Text("(textual)", style="oshell.muted"), "", "textual")
        except ImportError:
            pass
        console.print(table)
        console.print(
            "[oshell.muted]oshell theme set NAME · drop any Omarchy theme in ~/.oshell/themes/ · "
            "oshell theme import URL[/]"
        )

    @theme_app.command("set")
    def theme_set(name: str) -> None:
        """Make NAME the theme everywhere: TUI, CLI, ~/.oshell/current/* exports."""
        try:
            p = themes.apply_theme(name)
        except ValueError as exc:
            console.print(f"[oshell.err]{exc}[/]")
            raise typer.Exit(code=1) from None
        if p is None:
            console.print(
                f"[oshell.ok]✓[/] theme → {name} [oshell.muted](Textual built-in; TUI only)[/]"
            )
            return
        fresh = Console(theme=themes.to_rich_theme(p), highlight=False)
        line = Text()
        line.append("✓ ", style="oshell.ok")
        line.append("theme → ", style="oshell.muted")
        line.append(p.name, style="oshell.accent")
        line.append("  ")
        line.append_text(themes.swatch(p))
        fresh.print(line)
        d = themes.current_dir()
        fresh.print(
            f"[oshell.muted]exports refreshed in {d}/  "
            "(ghostty.conf · alacritty.toml · kitty.conf · wezterm.lua · btop.theme · "
            "colors.sh)[/]"
        )
        fresh.print(
            "[oshell.muted]terminal follows along? e.g.  "
            'echo "config-file = ~/.oshell/current/ghostty.conf" >> ~/.config/ghostty/config[/]'
        )

    @theme_app.command("show")
    def theme_show(name: str = typer.Argument(None)) -> None:
        """Print a theme's colors.toml (default: the current theme)."""
        p = themes.get_palette(name or _current_name())
        if p is None:
            console.print(f"[oshell.err]no palette for {name or _current_name()}[/]")
            raise typer.Exit(code=1)
        sys.stdout.write(p.to_toml())

    @theme_app.command("export")
    def theme_export(
        fmt: str = typer.Argument(
            ..., help="ghostty | alacritty | kitty | wezterm | btop | sh | toml"
        ),
        name: str = typer.Option(None, "--theme", "-t", help="A theme other than the current one"),
    ) -> None:
        """Print a terminal/shell config snippet for the theme (pipe or redirect it)."""
        p = themes.get_palette(name or _current_name())
        if p is None:
            console.print(f"[oshell.err]no palette for {name or _current_name()}[/]")
            raise typer.Exit(code=1)
        try:
            sys.stdout.write(themes.export(p, fmt))
        except ValueError as exc:
            console.print(f"[oshell.err]{exc}[/]")
            raise typer.Exit(code=1) from None

    @theme_app.command("import")
    def theme_import(
        src: str = typer.Argument(..., help="colors.toml, a theme dir, or a GitHub URL"),
        name: str = typer.Option(None, "--name", "-n", help="Name to save it under"),
        activate: bool = typer.Option(False, "--set", help="Also make it the current theme"),
    ) -> None:
        """Bring an Omarchy theme in (any of the hundreds in the community)."""
        try:
            p = themes.import_theme(src, name)
        except (ValueError, FileNotFoundError) as exc:
            console.print(f"[oshell.err]{exc}[/]")
            raise typer.Exit(code=1) from None
        line = Text()
        line.append("✓ ", style="oshell.ok")
        line.append(f"imported {p.name}  ", style="oshell.accent")
        line.append_text(themes.swatch(p))
        line.append(f"  → {p.source}", style="oshell.muted")
        console.print(line)
        if activate:
            themes.apply_theme(p.name)
            console.print(f"[oshell.ok]✓[/] theme → {p.name}")
        else:
            console.print(f"[oshell.muted]oshell theme set {p.name}[/]")

    @app.command()
    def fetch(
        no_probe: bool = typer.Option(False, "--no-probe", help="Skip contacting the backend"),
    ) -> None:
        """A neofetch for your assistant: logo, rig, model, machine memory, theme."""
        from .fetch import print_fetch

        cfg = Config.load()
        p = themes.get_palette(cfg.theme) or themes.get_palette(themes.DEFAULT_THEME)
        assert p is not None
        c = Console(theme=themes.to_rich_theme(p))
        from .fetch import render

        c.print(render(cfg, p, cfg.theme, width=c.width, probe_backend=not no_probe))
        _ = print_fetch  # re-exported for callers who want the simple form

    @app.command()
    def screensaver(
        mood: str = typer.Option(
            None, "--mood", help="rain, snow, aurora, ocean, starfield, embers, matrix, fireflies"
        ),
    ) -> None:
        """Weather over the wordmark, full-terminal, until you press a key."""
        from . import screensaver as saver

        cfg = Config.load()
        p = themes.get_palette(cfg.theme) or themes.get_palette(themes.DEFAULT_THEME)
        assert p is not None
        chosen = mood or cfg.fun.mood
        if chosen == "none":
            chosen = "starfield"
        saver.run(Console(theme=themes.to_rich_theme(p)), p, chosen)
