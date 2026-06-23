"""Old-school, keyboard-driven main menu for the TUI.

A nod to the v0.1 numbered command table: a modal list of the app's functions
that you drive with the arrow keys + Enter, or by pressing the option's number,
or Esc to drop back to chat. Selecting an item returns its id to the app, which
runs the matching action.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

# (id, label, description) — order defines the numbering.
MENU_ITEMS: list[tuple[str, str, str]] = [
    ("chat", "Chat", "Talk to the model (close this menu)"),
    ("models", "Models", "Choose the active model"),
    ("tools", "Tools", "Show available tools & capabilities"),
    ("knowledge", "Knowledge base", "How to store & recall local notes"),
    ("finetune", "Fine-tuning", "Detect training backend and list jobs"),
    ("config", "Settings", "Show resolved configuration (secrets redacted)"),
    ("help", "Help", "Keys and how the agent works"),
    ("quit", "Quit", "Exit Ollama Shell"),
]


class MenuScreen(ModalScreen[str]):
    """Modal menu; dismisses with the chosen item id (or 'chat' on Esc)."""

    CSS = """
    MenuScreen { align: center middle; }
    #menu-box {
        width: 64; height: auto; padding: 1 2;
        border: round $accent; background: $surface;
    }
    #menu-title { padding-bottom: 1; }
    #menu-list { height: auto; }
    """
    BINDINGS = [Binding("escape", "to_chat", "Back to chat")]

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-box"):
            yield Static(
                "[b]Ollama Shell — Menu[/b]\n"
                "[dim]↑/↓ + Enter, press a number, or Esc for chat[/dim]",
                id="menu-title",
            )
            yield OptionList(
                *[
                    Option(f" {i + 1}.  {label}   [dim]{desc}[/dim]", id=cid)
                    for i, (cid, label, desc) in enumerate(MENU_ITEMS)
                ],
                id="menu-list",
            )

    def on_mount(self) -> None:
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def on_key(self, event) -> None:
        # Press a digit to pick that numbered item (classic command-menu feel).
        if event.character and event.character.isdigit():
            n = int(event.character)
            if 1 <= n <= len(MENU_ITEMS):
                event.stop()
                self.dismiss(MENU_ITEMS[n - 1][0])

    def action_to_chat(self) -> None:
        self.dismiss("chat")


class ModelScreen(ModalScreen[str]):
    """Pick the active model from those available on the backend.

    Dismisses with the chosen model name, or ``None`` on Esc/cancel.
    """

    CSS = """
    ModelScreen { align: center middle; }
    #menu-box {
        width: 72; height: auto; max-height: 80%; padding: 1 2;
        border: round $accent; background: $surface;
    }
    #menu-title { padding-bottom: 1; }
    #menu-list { height: auto; max-height: 24; }
    """
    BINDINGS = [Binding("escape", "cancel", "Back")]

    def __init__(self, models: list[str], current: str | None = None):
        super().__init__()
        self._models = models
        self._current = current

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-box"):
            yield Static(
                "[b]Select a model[/b]\n"
                "[dim]↑/↓ + Enter, a number (1–9), or Esc to cancel[/dim]",
                id="menu-title",
            )
            options = []
            for i, m in enumerate(self._models):
                tag = "  [green](current)[/green]" if m == self._current else ""
                label = f" {i + 1}." if i < 9 else "   "
                options.append(Option(f"{label}  {m}{tag}", id=m))
            yield OptionList(*options, id="menu-list")

    def on_mount(self) -> None:
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def on_key(self, event) -> None:
        if event.character and event.character.isdigit():
            n = int(event.character)
            if 1 <= n <= min(9, len(self._models)):
                event.stop()
                self.dismiss(self._models[n - 1])

    def action_cancel(self) -> None:
        self.dismiss(None)
