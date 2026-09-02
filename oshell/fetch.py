"""``oshell fetch`` — a neofetch for your assistant.

Logo on the left in the theme's colors, the facts that matter on the right:
what you're running on, which model answers, whether the machine-memory
daemons are up, how many sessions and memories have accumulated. Pure
diagnostics dressed up — because a beautiful system is a motivating system.
"""

from __future__ import annotations

import os
import platform
import time
from pathlib import Path

from rich.console import Console, Group
from rich.table import Table
from rich.text import Text

from .config import Config
from .themes import Palette, swatch

# "OSHELL" in the ANSI Shadow figlet font — six rows.
LOGO = [
    " ██████╗ ███████╗██╗  ██╗███████╗██╗     ██╗     ",
    "██╔═══██╗██╔════╝██║  ██║██╔════╝██║     ██║     ",
    "██║   ██║███████╗███████║█████╗  ██║     ██║     ",
    "██║   ██║╚════██║██╔══██║██╔══╝  ██║     ██║     ",
    "╚██████╔╝███████║██║  ██║███████╗███████╗███████╗",
    " ╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝",
]

# A compact glyph mark for narrow terminals.
MARK = [
    "   ▄▄▄▄   ",
    " ▄█▀  ▀█▄ ",
    " ██  ▄▄██ ",
    " ▀█▄  ▄█▀ ",
    "   ▀▀▀▀   ",
]


def logo_text(p: Palette, rows: list[str] | None = None, tick: int = 0) -> Text:
    """The logo with a vertical gradient through the palette's chroma."""
    rows = rows or LOGO
    ramp = [p.accent, p.blue, p.magenta, p.bright_magenta, p.cyan, p.bright_cyan]
    out = Text()
    for i, row in enumerate(rows):
        color = ramp[(i + tick) % len(ramp)]
        out.append(row, style=f"bold {color}")
        if i < len(rows) - 1:
            out.append("\n")
    return out


def _uptime() -> str:
    try:
        if platform.system() == "Windows":
            import ctypes

            up = ctypes.windll.kernel32.GetTickCount64() / 1000.0  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            import subprocess

            raw = subprocess.run(
                ["sysctl", "-n", "kern.boottime"], capture_output=True, text=True, timeout=2
            ).stdout
            secs = int(raw.split("sec = ")[1].split(",")[0])
            up = time.time() - secs
        else:
            with open("/proc/uptime", encoding="utf-8") as f:
                up = float(f.read().split()[0])
    except Exception:
        return "?"
    d, rem = divmod(int(up), 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    return (f"{d}d " if d else "") + f"{h}h {m}m"


def _count(path: str, pattern: str = "*") -> int:
    p = Path(path).expanduser()
    return len(list(p.glob(pattern))) if p.is_dir() else 0


def _memories(path: str) -> int:
    import json

    p = Path(path).expanduser()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    if isinstance(data, dict):
        data = data.get("memories") or data.get("items") or list(data.values())
    return len(data) if isinstance(data, list) else 0


def gather_facts(cfg: Config, theme_name: str, probe_backend: bool = True) -> list[tuple[str, str]]:
    """The right-hand column, as (label, value) pairs."""
    from .roles import host_os, shell_name
    from .tools.system import _total_ram_gb

    facts: list[tuple[str, str]] = [
        ("os", host_os()),
        ("host", platform.node().split(".")[0] or "?"),
        ("shell", shell_name()),
        ("term", os.environ.get("TERM_PROGRAM") or os.environ.get("TERM") or "?"),
        ("uptime", _uptime()),
        ("cpu", f"{os.cpu_count()} cores · {platform.machine()}"),
        ("ram", f"{_total_ram_gb() or '?'} GB"),
        ("theme", theme_name),
        ("model", cfg.default_model),
    ]
    if probe_backend:
        try:
            from .providers import get_provider

            prov = get_provider(cfg)
            up = prov.health()
            n = len(prov.list_models()) if up else 0
            facts.append(
                ("backend", f"{cfg.provider.name} · {'up' if up else 'down'} · {n} models")
            )
        except Exception:
            facts.append(("backend", f"{cfg.provider.name} · unreachable"))
    else:
        facts.append(("backend", cfg.provider.name))
    mounted = [
        n for n, s in cfg.mcp_servers.items() if s.enabled and Path(s.command).expanduser().exists()
    ]
    facts.append(("machine memory", ", ".join(mounted) if mounted else "none (see ./install.sh)"))
    facts.append(("sessions", str(_count(cfg.session.dir, "*.json"))))
    facts.append(("memories", str(_memories(cfg.memory.path))))
    facts.append(("approvals", cfg.approvals))
    facts.append(("mood", cfg.fun.mood))
    return facts


def render(cfg: Config, p: Palette, theme_name: str, width: int = 100, probe_backend: bool = True):
    """The fetch card as a Rich renderable."""
    facts = gather_facts(cfg, theme_name, probe_backend=probe_backend)
    right = Text()
    right.append(f"{os.environ.get('USER', 'you')}@oshell\n", style=f"bold {p.accent}")
    right.append("─" * 24 + "\n", style=p.muted)
    for label, value in facts:
        right.append(f"{label:<15}", style=f"bold {p.blue}")
        right.append(f"{value}\n", style=p.foreground)
    right.append("\n")
    right.append_text(swatch(p))
    rows = LOGO if width >= 96 else MARK
    grid = Table.grid(padding=(0, 4))
    grid.add_column()
    grid.add_column()
    grid.add_row(logo_text(p, rows), right)
    return Group(Text(""), grid, Text(""))


def print_fetch(console: Console, cfg: Config, p: Palette, theme_name: str) -> None:
    console.print(render(cfg, p, theme_name, width=console.width))
