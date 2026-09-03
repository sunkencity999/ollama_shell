"""The mood takeover — weather falling on top of the live workspace.

After the shell has been idle a while (``fun.mood_takeover_seconds``), the
chosen mood stops being a one-line strip and takes the whole stage: a
translucent screen whose only widgets are one-cell "flecks", one per particle.
Terminal compositing paints whole widget cells, so a full-screen canvas would
hide the app — but a screen's *uncovered* cells show the screen below. By
covering almost nothing, the rain really does fall between your messages: the
workspace stays readable underneath, lightly dimmed. Any key or click wakes
the shell (and is swallowed, screensaver-style).
"""

from __future__ import annotations

import re

from textual.app import ComposeResult
from textual.events import Key, MouseDown
from textual.screen import ModalScreen
from textual.widgets import Static

from . import ambient

_MAX_FLECKS = 160  # matches the cap in ambient.mood_points
_HEX = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")
_WAKE_HINT = "( any key wakes the shell )"


class _Fleck(Static):
    """A single weather particle: one cell, absolutely positioned."""

    DEFAULT_CSS = """
    _Fleck { position: absolute; width: 1; height: 1; background: transparent; }
    """


class _Logo(Static):
    """The OSHELL wordmark, adrift over the weather (screensaver mode)."""

    DEFAULT_CSS = """
    _Logo { position: absolute; width: auto; height: auto; background: transparent; }
    """


class MoodOverlay(ModalScreen[None]):
    """The chosen mood, played across the whole (still visible) workspace.

    With ``logo=True`` (the explicit screensaver) the wordmark drifts across
    the weather in the theme's hues, Omarchy-screensaver style; the idle
    takeover leaves it off so the workspace stays legible underneath.
    """

    CSS = """
    MoodOverlay { background: $background 25%; }
    MoodOverlay.dimmer { background: $background 60%; }
    #wake-hint {
        position: absolute; width: auto; height: 1;
        background: transparent; color: $text-muted;
    }
    """

    def __init__(self, mood: str, logo: bool = False, on_wake=None) -> None:
        super().__init__(classes="dimmer" if logo else "")
        self.mood = mood
        self.logo = logo
        self._tick = 0
        # Called synchronously *before* dismiss so the app can rewind its idle
        # clock in the same frame — otherwise a tick can land between the pop
        # and the dismiss callback and take the stage right back.
        self._on_wake = on_wake

    def _wake(self) -> None:
        if self._on_wake is not None:
            try:
                self._on_wake()
            except Exception:
                pass
        self.dismiss(None)

    def compose(self) -> ComposeResult:
        for _ in range(_MAX_FLECKS):
            fleck = _Fleck("")
            fleck.display = False
            yield fleck
        if self.logo:
            yield _Logo("", id="logo")
        yield Static(_WAKE_HINT, id="wake-hint")

    def on_mount(self) -> None:
        self._flecks = list(self.query(_Fleck))
        self._frame()
        self.set_interval(0.1, self._frame)  # dies with the screen

    def _paint_logo(self, w: int, h: int) -> None:
        import math

        from ..fetch import LOGO, logo_text
        from ..themes import Palette

        lw, lh = len(LOGO[0]), len(LOGO)
        logo = self.query_one("#logo", _Logo)
        if lw + 2 > w or lh + 4 > h:
            logo.display = False
            return
        logo.display = True
        v = self.app.theme_variables

        def color(key: str, default: str) -> str:
            # Theme variables may be 8-digit hex (alpha) or CSS-only ("auto 60%");
            # Rich wants plain #rrggbb.
            val = v.get(key, "")
            return val[:7] if _HEX.match(val or "") else default

        # Borrow the live theme's colors for the gradient (works for Textual
        # built-ins too, which have no Palette of their own).
        p = Palette(
            name="live",
            accent=color("primary", "#7aa2f7"),
            blue=color("secondary", "#7aa2f7"),
            magenta=color("accent", "#bb9af7"),
            bright_magenta=color("primary-lighten-1", "#bb9af7"),
            cyan=color("success", "#449dab"),
            bright_cyan=color("secondary-lighten-1", color("warning", "#0db9d7")),
        )
        cx = (w - lw) / 2 + (w - lw) / 2.4 * math.sin(self._tick / 90)
        cy = (h - lh) / 2 + (h - lh) / 2.6 * math.cos(self._tick / 130)
        logo.styles.offset = (int(cx), int(cy))
        logo.update(logo_text(p, tick=self._tick // 12))

    def _frame(self) -> None:
        """Advance one animation frame: move/refresh the fleck pool."""
        self._tick += 1
        w = self.size.width or 80
        h = self.size.height or 24
        if self.logo:
            try:
                self._paint_logo(w, h)
            except Exception:
                pass
        try:
            points = ambient.mood_points(self.mood, w, h, self._tick)
            for fleck, (x, y, glyph, style) in zip(self._flecks, points, strict=False):
                fleck.styles.offset = (x, y)
                fleck.update(f"[{style}]{glyph}[/]")
                fleck.display = True
            for fleck in self._flecks[len(points):]:
                if fleck.display:
                    fleck.display = False
            # Top-right, under the header — the one spot that's reliably empty.
            hint = self.query_one("#wake-hint", Static)
            hint.styles.offset = (max(w - len(_WAKE_HINT) - 2, 0), 1)
        except Exception:
            pass  # never let the weather take down the session

    # ── waking up (the wake event is swallowed, screensaver-style) ────────────
    def on_key(self, event: Key) -> None:
        event.stop()
        self._wake()

    def on_mouse_down(self, event: MouseDown) -> None:
        event.stop()
        self._wake()
