"""Desktop control backends.

``Controller`` is the interface the GUI tools call; ``PyAutoGuiBackend`` is the
default cross-platform implementation. New backends (Wayland, macOS-native) only
need to implement these few methods — tools and the agent loop stay unchanged.
"""

from __future__ import annotations

import base64
import io
from abc import ABC, abstractmethod


class GuiUnavailable(RuntimeError):
    """GUI control isn't available (missing deps, no display, or no permission)."""


class Controller(ABC):
    """Minimal desktop-control surface."""

    name: str = "base"

    @abstractmethod
    def screen_size(self) -> tuple[int, int]:
        """(width, height) of the primary screen, in logical pixels."""

    @abstractmethod
    def screenshot_png(self) -> bytes:
        """Capture the screen as PNG bytes."""

    @abstractmethod
    def move(self, x: int, y: int) -> None: ...

    @abstractmethod
    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None: ...

    @abstractmethod
    def type_text(self, text: str) -> None: ...

    @abstractmethod
    def press_key(self, key: str) -> None:
        """Press a key or chord, e.g. 'enter', 'cmd+space', 'ctrl+c'."""

    def screenshot_b64(self) -> str:
        return base64.b64encode(self.screenshot_png()).decode()


class PyAutoGuiBackend(Controller):
    """Cross-platform backend via pyautogui (macOS/Windows/X11 Linux)."""

    name = "pyautogui"

    def __init__(self) -> None:
        try:
            import pyautogui  # type: ignore
        except ImportError as exc:
            raise GuiUnavailable(
                "GUI control needs the 'gui' feature (pyautogui) — install it from the menu"
            ) from exc
        except Exception as exc:  # e.g. no DISPLAY on headless Linux
            raise GuiUnavailable(f"GUI control unavailable: {exc}") from exc
        pyautogui.FAILSAFE = True  # slam mouse to a corner to abort
        self._g = pyautogui

    def screen_size(self) -> tuple[int, int]:
        size = self._g.size()
        return int(size[0]), int(size[1])

    def screenshot_png(self) -> bytes:
        img = self._g.screenshot()  # PIL Image
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def move(self, x: int, y: int) -> None:
        self._g.moveTo(x, y)

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        self._g.click(x=x, y=y, button=button, clicks=clicks)

    def type_text(self, text: str) -> None:
        self._g.typewrite(text, interval=0.01)

    def press_key(self, key: str) -> None:
        keys = [k.strip() for k in key.replace("+", " ").split()]
        if len(keys) > 1:
            self._g.hotkey(*keys)
        else:
            self._g.press(keys[0])


def get_controller() -> Controller:
    """Return a desktop controller. Seam for native backends (Wayland/macOS)."""
    # Future: detect Wayland (XDG_SESSION_TYPE=wayland) -> WaylandBackend, etc.
    return PyAutoGuiBackend()
