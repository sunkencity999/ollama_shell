"""``oshell screensaver`` — the mood, full-terminal, with the wordmark adrift.

Omarchy ships a screensaver that plays text effects over its logo; this is
ours for any terminal (no TUI needed): the configured mood's particles fall
across the whole screen while the OSHELL wordmark drifts slowly through the
theme's hues. Any key exits. It is also what ``oshell tui`` uses for the idle
takeover's logo, so the two feel like one thing.

Rendering is a plain Rich ``Live`` loop over a list of lines, which keeps it
cheap: a few hundred cells change per frame, nothing else.
"""

from __future__ import annotations

import math
import os
import select
import sys
import time

from rich.console import Console
from rich.live import Live
from rich.text import Text

from .fetch import LOGO
from .themes import Palette
from .tui import ambient


def frame(p: Palette, mood: str, width: int, height: int, tick: int) -> Text:
    """One frame: particles + the drifting logo, as a single Text."""
    width = max(width, 20)
    height = max(height, 8)
    grid: list[list[tuple[str, str] | None]] = [[None] * width for _ in range(height)]
    # Weather / mood particles from the TUI's ambient engine (same physics).
    if mood not in ("none", ""):
        for x, y, glyph, style in ambient.mood_points(mood, width, height, tick):
            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = (glyph, style)
    # The wordmark drifts on a slow Lissajous path and cycles its hue.
    lw = len(LOGO[0])
    lh = len(LOGO)
    if lw + 2 <= width and lh + 2 <= height:
        cx = (width - lw) / 2 + (width - lw) / 2.4 * math.sin(tick / 90)
        cy = (height - lh) / 2 + (height - lh) / 2.6 * math.cos(tick / 130)
        ox, oy = int(cx), int(cy)
        ramp = [p.accent, p.blue, p.magenta, p.bright_magenta, p.cyan, p.bright_cyan]
        for r, row in enumerate(LOGO):
            color = ramp[(r + tick // 12) % len(ramp)]
            for c, ch in enumerate(row):
                if ch != " " and 0 <= oy + r < height and 0 <= ox + c < width:
                    grid[oy + r][ox + c] = (ch, f"bold {color}")
    # Hint, bottom-right, so nobody thinks the terminal hung.
    hint = "any key wakes the shell"
    if width > len(hint) + 2:
        for i, ch in enumerate(hint):
            grid[height - 1][width - len(hint) - 1 + i] = (ch, p.dark_foreground)
    out = Text(no_wrap=True)
    for y, row in enumerate(grid):
        for cell in row:
            if cell is None:
                out.append(" ")
            else:
                out.append(cell[0], style=cell[1])
        if y < height - 1:
            out.append("\n")
    return out


def _key_pressed(timeout: float) -> bool:
    """True if a key is waiting on stdin (POSIX raw mode) or msvcrt (Windows)."""
    if os.name == "nt":  # pragma: no cover - Windows only
        import msvcrt

        time.sleep(timeout)
        if msvcrt.kbhit():
            msvcrt.getch()
            return True
        return False
    r, _, _ = select.select([sys.stdin], [], [], timeout)
    if r:
        os.read(sys.stdin.fileno(), 64)
        return True
    return False


def run(console: Console, p: Palette, mood: str = "fireflies", fps: float = 12.0) -> None:
    """Play until a key is pressed (or Ctrl+C)."""
    if not sys.stdin.isatty():
        console.print("[oshell.warn]The screensaver needs an interactive terminal.[/]")
        return
    raw = None
    if os.name != "nt":
        import termios
        import tty

        fd = sys.stdin.fileno()
        raw = termios.tcgetattr(fd)
        tty.setcbreak(fd)
    tick = 0
    try:
        with Live(console=console, screen=True, auto_refresh=False, transient=True) as live:
            while True:
                w, h = console.size
                live.update(frame(p, mood, w, h, tick), refresh=True)
                tick += 1
                if _key_pressed(1.0 / fps):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        if raw is not None:
            import termios

            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, raw)
