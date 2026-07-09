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

from textual.app import ComposeResult
from textual.events import Key, MouseDown
from textual.screen import ModalScreen
from textual.widgets import Static

from . import ambient

_MAX_FLECKS = 160  # matches the cap in ambient.mood_points
_WAKE_HINT = "( any key wakes the shell )"


class _Fleck(Static):
    """A single weather particle: one cell, absolutely positioned."""

    DEFAULT_CSS = """
    _Fleck { position: absolute; width: 1; height: 1; background: transparent; }
    """


class MoodOverlay(ModalScreen[None]):
    """The chosen mood, played across the whole (still visible) workspace."""

    CSS = """
    MoodOverlay { background: $background 25%; }
    #wake-hint {
        position: absolute; width: auto; height: 1;
        background: transparent; color: $text-muted;
    }
    """

    def __init__(self, mood: str) -> None:
        super().__init__()
        self.mood = mood
        self._tick = 0

    def compose(self) -> ComposeResult:
        for _ in range(_MAX_FLECKS):
            fleck = _Fleck("")
            fleck.display = False
            yield fleck
        yield Static(_WAKE_HINT, id="wake-hint")

    def on_mount(self) -> None:
        self._flecks = list(self.query(_Fleck))
        self._frame()
        self.set_interval(0.1, self._frame)  # dies with the screen

    def _frame(self) -> None:
        """Advance one animation frame: move/refresh the fleck pool."""
        self._tick += 1
        w = self.size.width or 80
        h = self.size.height or 24
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
        self.dismiss(None)

    def on_mouse_down(self, event: MouseDown) -> None:
        event.stop()
        self.dismiss(None)
