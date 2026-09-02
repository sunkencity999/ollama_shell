"""A Waybar for the workspace — the one-line status bar across the top.

Omarchy's bar puts the things you glance at in one thin strip: workspace,
what's running, vitals, clock. Ours: the model and backend, the tool roster
and privacy posture, the context gauge, the last turn's tokens/second, the
approvals mode, the mood, and a clock — each in the theme's colors, with Nerd
Font glyphs when the terminal likely has them and plain Unicode when not.

The bar is rebuilt from a small ``BarState`` the app updates (a once-a-second
timer plus event-driven refreshes), so rendering is pure and testable.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from rich.text import Text
from textual.widgets import Static

# Glyph sets: Nerd Font (FontAwesome range, present in every Nerd Font) vs plain.
_NERD = {
    "logo": "",  # terminal
    "tools": "",  # wrench
    "local": "",  # shield
    "net": "",  # globe
    "ctx": "",  # microchip
    "tps": "",  # bolt
    "ask": "",  # eye
    "auto": "",  # play
    "ro": "",  # lock
    "clock": "",  # clock
    "mood": "",  # moon
    "busy": "",  # spinner
}
_PLAIN = {
    "logo": "❯",
    "tools": "⚙",
    "local": "●",
    "net": "◐",
    "ctx": "▣",
    "tps": "⚡",
    "ask": "◉",
    "auto": "▶",
    "ro": "🔒",
    "clock": "◔",
    "mood": "☾",
    "busy": "…",
}

_HEX = __import__("re").compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")
_NERD_TERMS = {"ghostty", "wezterm", "kitty", "alacritty", "iterm.app", "rio", "foot"}


def nerd_font_enabled(setting: str = "auto") -> bool:
    """Resolve the ``ui.nerd_font`` setting: on | off | auto (env sniff)."""
    s = (setting or "auto").lower()
    if s in ("on", "true", "yes"):
        return True
    if s in ("off", "false", "no"):
        return False
    if os.environ.get("OSHELL_NERD_FONT", "").lower() in ("1", "true", "on"):
        return True
    term = (os.environ.get("TERM_PROGRAM") or "").lower()
    if term in _NERD_TERMS or os.environ.get("KITTY_WINDOW_ID") or os.environ.get("WEZTERM_PANE"):
        return True
    return False


@dataclass
class BarState:
    model: str = ""
    provider: str = ""
    n_tools: int = 0
    n_net: int = 0
    ctx_fill: float = 0.0
    tok_s: float | None = None
    approvals: str = "auto"
    mood: str = "fireflies"
    theme: str = ""
    busy: bool = False
    status: str = ""  # what the model is doing when busy
    workspaces: tuple[str, ...] = ("chat", "tools", "context", "activity")
    workspace: int = 0  # index into workspaces (the focused tile / sidebar tab)


def gauge(fill: float, cells: int = 5) -> str:
    fill = max(0.0, min(1.0, fill))
    on = round(fill * cells)
    return "▰" * on + "▱" * (cells - on)


def render_bar(
    state: BarState, width: int, colors: dict[str, str], nerd: bool, clock: bool
) -> Text:
    """Compose the bar for ``width`` columns. ``colors`` are theme variables."""
    g = _NERD if nerd else _PLAIN
    accent = colors.get("primary", "#7aa2f7")
    pop = colors.get("accent", "#ff9e64")
    fg = colors.get("foreground", "#c0caf5")
    bg = colors.get("background", "#1a1b26")
    muted = colors.get("text-muted", colors.get("foreground-muted", "#565f89"))
    ok = colors.get("success", "#9ece6a")
    warn = colors.get("warning", "#e0af68")
    err = colors.get("error", "#f7768e")
    sep = Text(" │ ", style=muted)

    t = Text(no_wrap=True, overflow="ellipsis")
    # Workspace tag: an accent block with the wordmark, Waybar-style.
    t.append(f" {g['logo']} oshell ", style=f"bold {bg} on {accent}")
    # Workspaces, Waybar-style: numbered, the active one lit. Clickable — each
    # number carries an @click action the app handles (app.workspace(n)).
    from rich.style import Style

    for i, _name in enumerate(state.workspaces):
        active = i == state.workspace
        st = Style.parse(f"bold {fg} on {colors.get('surface', '#24283b')}" if active else muted)
        st += Style(meta={"@click": f"app.workspace({i})"})
        t.append(f" {i + 1} ", style=st)
    t.append(" ")
    if state.busy:
        t.append(f"{g['busy']} {state.status or 'thinking'}", style=f"italic {pop}")
    else:
        t.append(state.model or "—", style=f"bold {fg}")
        if state.provider:
            t.append(f" · {state.provider}", style=muted)
    t.append_text(sep)
    t.append(f"{g['tools']} {state.n_tools}", style=fg)
    t.append(" ")
    if state.n_net:
        t.append(f"{g['net']} {state.n_net} net", style=warn)
    else:
        t.append(f"{g['local']} local", style=ok)
    t.append_text(sep)
    ctx_style = err if state.ctx_fill > 0.85 else (warn if state.ctx_fill > 0.6 else fg)
    t.append(f"{g['ctx']} {gauge(state.ctx_fill)} {state.ctx_fill:.0%}", style=ctx_style)
    if state.tok_s:
        t.append_text(sep)
        t.append(f"{g['tps']} {state.tok_s:.0f} tok/s", style=fg)
    t.append_text(sep)
    a = state.approvals
    a_glyph = g["ask"] if a == "ask" else (g["ro"] if a == "read-only" else g["auto"])
    a_style = warn if a == "ask" else (muted if a == "read-only" else ok)
    t.append(f"{a_glyph} {a}", style=a_style)

    def right_side(show_mood: bool, show_theme: bool) -> Text:
        right = Text(no_wrap=True)
        if show_mood and state.mood and state.mood != "none":
            right.append(f"{g['mood']} {state.mood}", style=muted)
        if show_theme and state.theme:
            if right.plain:
                right.append_text(sep)
            right.append(state.theme, style=muted)
        if clock:
            if right.plain:
                right.append_text(sep)
            right.append(f"{g['clock']} {time.strftime('%H:%M')}", style=fg)
        right.append(" ")
        return right

    # Right-aligned block: shed the mood, then the theme, before giving up.
    for show_mood, show_theme in ((True, True), (False, True), (False, False)):
        right = right_side(show_mood, show_theme)
        pad = width - t.cell_len - right.cell_len
        if pad > 0:
            t.append(" " * pad)
            t.append_text(right)
            break
    else:
        if width > 0:
            t.truncate(max(width, 1), overflow="ellipsis")
    return t


class StatusBar(Static):
    """The bar widget: docked top, one row, repainted from ``BarState``."""

    DEFAULT_CSS = """
    StatusBar {
        dock: top; height: 1; width: 100%;
        background: $surface; color: $foreground;
    }
    """

    def __init__(self, nerd: bool = False, clock: bool = True) -> None:
        super().__init__("", id="statusbar")
        self.state = BarState()
        self.nerd = nerd
        self.clock = clock
        self.text = ""  # plain rendering, for tests

    def repaint(self) -> None:
        width = self.size.width or 100
        try:
            # Only real colors: Textual's variables also hold CSS-only values
            # like "auto 60%" that Rich can't parse, and 8-digit hex with alpha
            # (Rich wants 6) — keep the RGB part of those.
            colors = {
                k: v[:7]
                for k, v in self.app.theme_variables.items()
                if isinstance(v, str) and _HEX.match(v)
            }
        except Exception:  # pragma: no cover - before the app is ready
            colors = {}
        bar = render_bar(self.state, width, colors, self.nerd, self.clock)
        self.text = bar.plain
        self.update(bar)
