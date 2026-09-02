"""The keybindings overlay — Omarchy's Super+K, for the workspace.

One modal, every key and slash command, grouped. Data-driven so the help text
can never drift from what the app actually binds: the app passes its own
``BINDINGS`` in, and this screen adds the slash commands it knows about.
"""

from __future__ import annotations

from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

SLASH_COMMANDS: list[tuple[str, str]] = [
    ("/theme [name]", "switch theme (no name: picker)"),
    ("/mood [name]", "idle ambience: rain, snow, aurora, ocean, …"),
    ("/screensaver", "play the mood over the workspace now"),
    ("/keys", "this overlay"),
    ("/clear", "new conversation"),
    ("/daydream", "let the model wander 💭"),
    ("/route [on|off]", "automatic model routing"),
    ("/approvals [mode]", "auto · ask · read-only"),
    ("/compact", "summarize older turns to free context"),
    ("/undo", "restore the last file the model changed"),
    ("/menu", "the main menu"),
    ("/NAME [args]", "your ~/.oshell/commands/NAME.md"),
]

_KEY_LABELS = {
    "escape": "Esc",
    "ctrl+p": "Ctrl+P",
    "ctrl+t": "Ctrl+T",
    "ctrl+y": "Ctrl+Y",
    "ctrl+b": "Ctrl+B",
    "ctrl+c": "Ctrl+C",
    "ctrl+g": "Ctrl+G",
    "f1": "F1",
    "f2": "F2",
    "ctrl+o": "Ctrl+O",
}


def keys_table(bindings: list[Binding], extra: list[tuple[str, str]] | None = None) -> Table:
    """Two-column table: keys (from the app's bindings) then slash commands."""
    table = Table.grid(padding=(0, 3))
    table.add_column(style="bold", justify="right")
    table.add_column()
    table.add_row(Text("Keys", style="bold underline"), "")
    seen: set[str] = set()
    rows = [(b.key, b.description) for b in bindings if b.description]
    rows.append(("ctrl+p", "Command palette (every action, fuzzy)"))
    for key, desc in rows:
        if key in seen:
            continue
        seen.add(key)
        table.add_row(_KEY_LABELS.get(key, key), desc)
    table.add_row("Option/Shift+drag", "Select text (the app owns the mouse)")
    table.add_row("", "")
    table.add_row(Text("Slash commands", style="bold underline"), "")
    for cmd, desc in extra or SLASH_COMMANDS:
        table.add_row(cmd, desc)
    return table


class KeysScreen(ModalScreen[None]):
    """Every key and command, one Esc away."""

    CSS = """
    KeysScreen { align: center middle; }
    #keys-box {
        width: 78; height: auto; max-height: 90%; padding: 1 2;
        border: round $accent; background: $surface;
    }
    #keys-title { padding-bottom: 1; }
    """
    # No BINDINGS of its own: on_key closes on anything, and a Screen keeps
    # its binding map in ``self._bindings`` — don't shadow it.

    def __init__(self, bindings: list[Binding]) -> None:
        super().__init__()
        self._key_rows = bindings

    def compose(self) -> ComposeResult:
        with Vertical(id="keys-box"):
            yield Static("[b]Keybindings[/b]\n[dim]Esc closes · F1 toggles[/dim]", id="keys-title")
            yield Static(keys_table(self._key_rows), id="keys-table")

    def on_key(self, event) -> None:
        # Any key closes — it's a cheat sheet, not a form.
        if event.key not in ("up", "down", "pageup", "pagedown"):
            event.stop()
            self.dismiss(None)
