"""Old-school, keyboard-driven main menu for the TUI.

A nod to the v0.1 numbered command table: a modal list of the app's functions
that you drive with the arrow keys + Enter, or by pressing the option's number,
or Esc to drop back to chat. Selecting an item returns its id to the app, which
runs the matching action.
"""

from __future__ import annotations

import importlib.util

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

# (id, label, description) — order defines the numbering.
MENU_ITEMS: list[tuple[str, str, str]] = [
    ("chat", "Chat", "Talk to the model (close this menu)"),
    ("models", "Models", "Choose the active model"),
    ("tools", "Tools", "Show available tools & capabilities"),
    ("copy_reply", "Copy last reply", "Copy the model's last reply to the clipboard"),
    ("copy_transcript", "Copy transcript", "Copy the whole conversation to the clipboard"),
    ("attach", "Attach image", "Attach an image for a vision model"),
    ("features", "Install features", "Add optional capabilities (rag, docs, vision, finetune)"),
    ("gui_toggle", "Computer-use (GUI)", "Turn desktop GUI control on/off (needs a vision model)"),
    ("browser_toggle", "Computer-use (browser)", "Turn the hidden browser on/off (vision model)"),
    ("memory", "Memory", "View what the assistant remembers (or clear it)"),
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


# (extra id, label, pip package specs, import-probe module names)
INSTALLABLE_FEATURES: list[tuple[str, str, list[str], tuple[str, ...]]] = [
    (
        "rag",
        "Knowledge base (RAG)",
        ["chromadb>=0.4.18", "sentence-transformers>=2.2.2"],
        ("chromadb", "sentence_transformers"),
    ),
    (
        "docs",
        "Document export (docx/xlsx/pdf)",
        ["python-docx>=1.0.0", "openpyxl>=3.1.0", "weasyprint>=60.1", "PyPDF2>=3.0.0"],
        ("docx", "openpyxl"),
    ),
    ("vision", "Image analysis", ["Pillow>=10.0.0"], ("PIL",)),
    ("finetune", "Fine-tuning (MLX, Apple Silicon)", ["mlx-lm>=0.20.0"], ("mlx_lm",)),
    (
        "gui",
        "GUI computer-use (pyautogui)",
        ["pyautogui>=0.9.54", "Pillow>=10.0.0"],
        ("pyautogui",),
    ),
    ("browser", "Hidden browser (Playwright)", ["playwright>=1.40"], ("playwright",)),
]


def feature_installed(modules: tuple[str, ...]) -> bool:
    return all(importlib.util.find_spec(m) is not None for m in modules)


class AttachImageScreen(ModalScreen[str]):
    """Prompt for an image to attach. Returns a path, "" (grab clipboard), or None."""

    CSS = """
    AttachImageScreen { align: center middle; }
    #menu-box {
        width: 72; height: auto; padding: 1 2;
        border: round $accent; background: $surface;
    }
    #menu-title { padding-bottom: 1; }
    """
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-box"):
            yield Static(
                "[b]Attach image[/b]\n"
                "[dim]Enter a file path (drag a file into the terminal to paste it), "
                "or leave blank + Enter to grab from the clipboard. Esc cancels.[/dim]",
                id="menu-title",
            )
            yield Input(placeholder="/path/to/image.png", id="attach-path")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip())  # "" -> clipboard

    def action_cancel(self) -> None:
        self.dismiss(None)


class FeaturesScreen(ModalScreen[str]):
    """Pick an optional feature to install into the running environment."""

    CSS = """
    FeaturesScreen { align: center middle; }
    #menu-box {
        width: 70; height: auto; padding: 1 2;
        border: round $accent; background: $surface;
    }
    #menu-title { padding-bottom: 1; }
    #menu-list { height: auto; }
    """
    BINDINGS = [Binding("escape", "cancel", "Back")]

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-box"):
            yield Static(
                "[b]Install features[/b]\n"
                "[dim]↑/↓ + Enter or a number; Esc to cancel. "
                "Installs into this app's environment.[/dim]",
                id="menu-title",
            )
            opts = []
            for i, (fid, label, _pkgs, mods) in enumerate(INSTALLABLE_FEATURES):
                tag = "  [green](installed)[/green]" if feature_installed(mods) else ""
                opts.append(Option(f" {i + 1}.  {label}{tag}", id=fid))
            yield OptionList(*opts, id="menu-list")

    def on_mount(self) -> None:
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def on_key(self, event) -> None:
        if event.character and event.character.isdigit():
            n = int(event.character)
            if 1 <= n <= len(INSTALLABLE_FEATURES):
                event.stop()
                self.dismiss(INSTALLABLE_FEATURES[n - 1][0])

    def action_cancel(self) -> None:
        self.dismiss(None)
