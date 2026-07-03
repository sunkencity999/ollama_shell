"""The Dream screen — /daydream takes the whole stage.

A full-screen modal night sky: ~90 twinkling stars, the occasional comet, and
the dream itself streaming into the centre as the model composes it. Any key
wakes the shell and drops you back exactly where you were. The dream is still
written to the transcript afterwards (ephemeral to the model's context, as
always) so it isn't lost when the sky fades.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Static

from .ambient import StarfieldModel


class DreamScreen(ModalScreen[None]):
    """Night sky + streaming dream. Dismisses on any key."""

    CSS = """
    DreamScreen { align: center middle; background: $background; }
    #sky { width: 100%; height: 100%; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.model = StarfieldModel()
        self._text = ""  # the dream so far (fed from the worker thread)
        self._done = False

    def compose(self) -> ComposeResult:
        yield Static("", id="sky")

    def on_mount(self) -> None:
        # 10fps only while the sky is on stage; the timer dies with the screen.
        self.set_interval(0.1, self._frame)

    # ── fed by the daydream worker (via call_from_thread) ────────────────────
    def feed(self, text: str) -> None:
        self._text = text

    def finish(self) -> None:
        self._done = True

    # ── render loop ───────────────────────────────────────────────────────────
    def _frame(self) -> None:
        self.model.step()
        size = self.size
        try:
            self.query_one("#sky", Static).update(
                self.model.render(size.width, size.height, self._text, self._done)
            )
        except Exception:
            pass  # never let the sky take down the session

    def on_key(self, event: Key) -> None:
        # Any key wakes the shell. (Ctrl+C still quits at the app level.)
        event.stop()
        self.dismiss(None)
