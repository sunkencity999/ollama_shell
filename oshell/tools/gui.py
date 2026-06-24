"""GUI computer-use tools (opt-in, vision-gated).

The model takes a ``screenshot`` (returned as an image it can see), reasons about
what's on screen, then issues ``gui_click`` / ``gui_type`` / ``gui_key`` /
``gui_move`` actions, screenshotting again to verify. All are ``sensitive`` —
they control the whole desktop.

Prefer the terminal (``run_command``) for anything achievable in a shell; these
tools are for genuine desktop-GUI tasks only.
"""

from __future__ import annotations

from typing import Any

from ..gui import GuiUnavailable, get_controller
from .base import Tool, ToolError, ToolResult


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


class _SharedController:
    """Holds one desktop Controller, created on first use."""

    def __init__(self) -> None:
        self._ctl = None

    def get(self):
        if self._ctl is None:
            self._ctl = get_controller()  # may raise GuiUnavailable
        return self._ctl


class _GuiTool(Tool):
    local_only = True  # local machine; nothing leaves it
    sensitive = True  # controls the desktop

    def __init__(self, shared: _SharedController):
        self._shared = shared

    def _controller(self):
        try:
            return self._shared.get()
        except GuiUnavailable as exc:
            raise ToolError(str(exc)) from exc


class ScreenshotTool(_GuiTool):
    name = "screenshot"
    description = (
        "Capture the current screen and return it as an image to look at. Take a "
        "screenshot before acting and again after, to see the result of an action."
    )
    parameters = {"type": "object", "properties": {}}

    def run(self, **_: Any) -> ToolResult:
        ctl = self._controller()
        try:
            w, h = ctl.screen_size()
            b64 = ctl.screenshot_b64()
        except GuiUnavailable as exc:  # e.g. macOS Screen Recording not granted
            raise ToolError(str(exc)) from exc
        return ToolResult(text=f"screenshot captured ({w}x{h})", images=[b64])


class ClickTool(_GuiTool):
    name = "gui_click"
    description = "Click the mouse at screen coordinates (x, y). button: left|right|middle."
    parameters = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "X pixel"},
            "y": {"type": "integer", "description": "Y pixel"},
            "button": {"type": "string", "description": "left (default), right, or middle"},
            "clicks": {"type": "integer", "description": "click count (default 1; 2 = double)"},
        },
        "required": ["x", "y"],
    }

    def run(self, x: Any = 0, y: Any = 0, button: str = "left", clicks: Any = 1, **_: Any) -> str:
        self._controller().click(_int(x), _int(y), button=button, clicks=_int(clicks, 1))
        return f"clicked {button} at ({_int(x)}, {_int(y)})"


class MoveTool(_GuiTool):
    name = "gui_move"
    description = "Move the mouse cursor to screen coordinates (x, y)."
    parameters = {
        "type": "object",
        "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
        "required": ["x", "y"],
    }

    def run(self, x: Any = 0, y: Any = 0, **_: Any) -> str:
        self._controller().move(_int(x), _int(y))
        return f"moved to ({_int(x)}, {_int(y)})"


class TypeTextTool(_GuiTool):
    name = "gui_type"
    description = "Type text via the keyboard at the current focus."
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to type"}},
        "required": ["text"],
    }

    def run(self, text: str = "", **_: Any) -> str:
        self._controller().type_text(text)
        return f"typed {len(text)} chars"


class PressKeyTool(_GuiTool):
    name = "gui_key"
    description = "Press a key or chord, e.g. 'enter', 'tab', 'cmd+space', 'ctrl+c'."
    parameters = {
        "type": "object",
        "properties": {"key": {"type": "string", "description": "Key or chord"}},
        "required": ["key"],
    }

    def run(self, key: str = "", **_: Any) -> str:
        if not key.strip():
            raise ToolError("key must not be empty")
        self._controller().press_key(key)
        return f"pressed {key}"


def gui_tools(shared: _SharedController | None = None) -> list[Tool]:
    shared = shared or _SharedController()
    return [
        ScreenshotTool(shared),
        ClickTool(shared),
        MoveTool(shared),
        TypeTextTool(shared),
        PressKeyTool(shared),
    ]
