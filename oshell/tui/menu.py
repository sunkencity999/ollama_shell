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

# (id, label, description) grouped into titled sections. Numbering runs
# continuously across sections (order here defines it).
MENU_SECTIONS: list[tuple[str, list[tuple[str, str, str]]]] = [
    (
        "Conversation",
        [
            ("chat", "Chat", "Talk to the model (close this menu)"),
            ("new_chat", "New conversation", "Clear the transcript and start fresh"),
            ("copy_reply", "Copy last reply", "Copy the model's last reply"),
            ("copy_transcript", "Copy transcript", "Copy the whole conversation"),
            ("attach", "Attach image", "Attach an image for a vision model"),
        ],
    ),
    (
        "Model & capabilities",
        [
            ("models", "Models", "Choose the active model"),
            ("tools", "Tools", "Show available tools & capabilities"),
            ("features", "Install features", "Add optional capabilities (rag, docs, …)"),
            ("gui_toggle", "Computer-use (GUI)", "Desktop control on/off (vision model)"),
            ("browser_toggle", "Computer-use (browser)", "Hidden browser on/off (vision model)"),
            ("finetune", "Fine-tuning", "Detect training backend and list jobs"),
        ],
    ),
    (
        "Workspace",
        [
            ("memory", "Memory", "View what the assistant remembers"),
            ("knowledge", "Knowledge base", "How to store & recall local notes"),
            ("daydream", "Daydream", "Let the model wander and free-associate 💭"),
            ("theme", "Theme", "Restyle the app (live preview)"),
        ],
    ),
    (
        "System",
        [
            ("config", "Settings", "Show resolved configuration"),
            ("help", "Help", "Keys and how the agent works"),
            ("quit", "Quit", "Exit Ollama Shell"),
        ],
    ),
]

# Flat view (id, label, description) — numbering source of truth.
MENU_ITEMS: list[tuple[str, str, str]] = [it for _t, items in MENU_SECTIONS for it in items]

_LABEL_COL = 24  # label column width, so descriptions align vertically


class MenuScreen(ModalScreen[str]):
    """Modal menu; dismisses with the chosen item id (or 'chat' on Esc).

    Numbers work past 9: digits buffer briefly ("1" then "4" → 14). A lone
    digit that no second digit could extend selects immediately; an ambiguous
    one ("1" when 10–18 exist) moves the highlight and selects after a beat
    (or on Enter).
    """

    CSS = """
    MenuScreen { align: center middle; }
    #menu-box {
        width: 84; height: auto; max-height: 90%; padding: 1 2;
        border: round $accent; background: $surface;
    }
    #menu-title { padding-bottom: 1; }
    #menu-stars { color: $text-muted; }
    #menu-list { height: auto; }
    """
    BINDINGS = [Binding("escape", "to_chat", "Back to chat")]

    _DIGIT_GRACE = 0.9  # seconds to wait for a possible second digit

    def __init__(self, effects: bool = False) -> None:
        super().__init__()
        self._effects = effects
        self._typed = ""  # buffered digits
        self._digit_timer = None
        self._row_of_number: dict[int, int] = {}  # menu number -> OptionList index

    def compose(self) -> ComposeResult:
        from .ambient import constellation_line

        with Vertical(id="menu-box"):
            yield Static(
                "[b]Ollama Shell — Menu[/b]\n"
                "[dim]↑/↓ + Enter, press a number, or Esc for chat[/dim]",
                id="menu-title",
            )
            if self._effects:  # a few faint stars behind the menu
                yield Static(constellation_line(76), id="menu-stars")
            options: list[Option] = []
            n = 0
            for title, items in MENU_SECTIONS:
                options.append(Option(f"[dim]── {title} ──[/dim]", disabled=True))
                for cid, label, desc in items:
                    n += 1
                    self._row_of_number[n] = len(options)
                    options.append(
                        Option(f" {n:>2}.  {label:<{_LABEL_COL}}[dim]{desc}[/dim]", id=cid)
                    )
            yield OptionList(*options, id="menu-list")

    def on_mount(self) -> None:
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self._cancel_digit_timer()
        self.dismiss(event.option.id)

    # ── numbered selection (with two-digit buffering) ─────────────────────────
    def on_key(self, event) -> None:
        if not (event.character and event.character.isdigit()):
            return
        event.stop()
        self._typed += event.character
        n = int(self._typed)
        if not (1 <= n <= len(MENU_ITEMS)):
            self._typed = ""
            self._cancel_digit_timer()
            return
        # Immediate visual feedback: move the highlight to the matching row.
        row = self._row_of_number.get(n)
        if row is not None:
            self.query_one(OptionList).highlighted = row
        if n * 10 > len(MENU_ITEMS):  # no further digit could extend this number
            self._select_number(n)
        else:
            self._restart_digit_timer(n)

    def _select_number(self, n: int) -> None:
        self._cancel_digit_timer()
        self._typed = ""
        if 1 <= n <= len(MENU_ITEMS):
            self.dismiss(MENU_ITEMS[n - 1][0])

    def _restart_digit_timer(self, n: int) -> None:
        self._cancel_digit_timer()
        self._digit_timer = self.set_timer(self._DIGIT_GRACE, lambda: self._select_number(n))

    def _cancel_digit_timer(self) -> None:
        if self._digit_timer is not None:
            self._digit_timer.stop()
            self._digit_timer = None

    def action_to_chat(self) -> None:
        self._cancel_digit_timer()
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

    def __init__(
        self,
        models: list[str],
        current: str | None = None,
        infos: dict[str, dict] | None = None,
    ):
        super().__init__()
        self._models = models
        self._current = current
        self._infos = infos or {}  # name -> {size, quant} badges (best-effort)

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-box"):
            yield Static(
                "[b]Select a model[/b]\n"
                "[dim]↑/↓ + Enter, a number (1–9), or Esc to cancel[/dim]",
                id="menu-title",
            )
            options = []
            for i, m in enumerate(self._models):
                info = self._infos.get(m, {})
                badge = " · ".join(v for v in (info.get("size"), info.get("quant")) if v)
                tag = f"  [dim]{badge}[/dim]" if badge else ""
                if m == self._current:
                    tag += "  [green](current)[/green]"
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


class ThemeScreen(ModalScreen[str]):
    """Pick a color theme, previewed live as you move the highlight.

    Dismisses with the chosen theme name, or ``None`` on Esc (which also
    restores the theme that was active when the screen opened).
    """

    CSS = """
    ThemeScreen { align: center middle; }
    #menu-box {
        width: 56; height: auto; max-height: 80%; padding: 1 2;
        border: round $accent; background: $surface;
    }
    #menu-title { padding-bottom: 1; }
    #menu-list { height: auto; max-height: 24; }
    """
    BINDINGS = [Binding("escape", "cancel", "Back")]

    def __init__(self, themes: list[str], current: str):
        super().__init__()
        self._themes = themes
        self._original = current

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-box"):
            yield Static(
                "[b]Theme[/b]\n"
                "[dim]↑/↓ previews live · Enter keeps it · Esc restores[/dim]",
                id="menu-title",
            )
            options = []
            for i, t in enumerate(self._themes):
                tag = "  [green](current)[/green]" if t == self._original else ""
                label = f" {i + 1}." if i < 9 else "   "
                options.append(Option(f"{label}  {t}{tag}", id=t))
            yield OptionList(*options, id="menu-list")

    def on_mount(self) -> None:
        lst = self.query_one(OptionList)
        if self._original in self._themes:
            lst.highlighted = self._themes.index(self._original)
        lst.focus()

    def _preview(self, name: str | None) -> None:
        if name:
            try:
                self.app.theme = name
            except Exception:
                pass  # unknown theme name — keep whatever is active

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        self._preview(event.option.id)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def on_key(self, event) -> None:
        if event.character and event.character.isdigit():
            n = int(event.character)
            if 1 <= n <= min(9, len(self._themes)):
                event.stop()
                self.dismiss(self._themes[n - 1])

    def action_cancel(self) -> None:
        self._preview(self._original)  # put the original theme back
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
