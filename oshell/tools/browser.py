"""Hidden-browser tools: drive a dedicated (headless) Chromium off-screen.

Preferred over the desktop GUI tools for anything on the web — it doesn't hijack
the user's screen and needs no Screen Recording permission. The model opens a
URL, screenshots the page (fed back as an image), and clicks/types by viewport
coordinates. All share one persistent BrowserController.
"""

from __future__ import annotations

import base64
from typing import Any

from ..browser import BrowserController, BrowserUnavailable
from ..config import BrowserConfig
from .base import Tool, ToolError, ToolResult


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


class _SharedBrowser:
    """Holds one BrowserController, created on first use from config."""

    def __init__(self, config: BrowserConfig | None = None):
        self._config = config or BrowserConfig()
        self._ctl: BrowserController | None = None

    def get(self) -> BrowserController:
        if self._ctl is None:
            self._ctl = BrowserController(
                headless=self._config.headless,
                width=self._config.width,
                height=self._config.height,
            )
        return self._ctl

    @property
    def timeout(self) -> float:
        return self._config.timeout


class _BrowserTool(Tool):
    local_only = False  # drives a browser over the network

    def __init__(self, shared: _SharedBrowser):
        self._shared = shared

    def _ctl(self) -> BrowserController:
        return self._shared.get()

    def _guard(self, fn):
        try:
            return fn()
        except BrowserUnavailable as exc:
            raise ToolError(str(exc)) from exc


class BrowserOpenTool(_BrowserTool):
    name = "browser_open"
    description = (
        "Open a URL in the hidden browser (off-screen). Use this for web tasks "
        "instead of the desktop GUI. Returns the page title; follow with "
        "browser_screenshot to see the page."
    )
    parameters = {
        "type": "object",
        "properties": {"url": {"type": "string", "description": "Absolute http(s) URL"}},
        "required": ["url"],
    }

    def run(self, url: str = "", **_: Any) -> str:
        if not url.startswith(("http://", "https://")):
            raise ToolError("url must be an absolute http(s) URL")
        return self._guard(lambda: self._ctl().open(url, self._shared.timeout))


class BrowserScreenshotTool(_BrowserTool):
    name = "browser_screenshot"
    description = "Screenshot the current page in the hidden browser and return it as an image."
    parameters = {"type": "object", "properties": {}}

    def run(self, **_: Any) -> ToolResult:
        png = self._guard(lambda: self._ctl().screenshot_png(self._shared.timeout))
        b64 = base64.b64encode(png).decode()
        url = self._guard(lambda: self._ctl().current_url())
        return ToolResult(text=f"page screenshot ({url})", images=[b64])


class BrowserClickTool(_BrowserTool):
    name = "browser_click"
    description = "Click in the hidden browser page at viewport coordinates (x, y)."
    parameters = {
        "type": "object",
        "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
        "required": ["x", "y"],
    }

    def run(self, x: Any = 0, y: Any = 0, **_: Any) -> str:
        return self._guard(lambda: self._ctl().click(_int(x), _int(y), self._shared.timeout))


class BrowserTypeTool(_BrowserTool):
    name = "browser_type"
    description = "Type text into the focused element in the hidden browser."
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def run(self, text: str = "", **_: Any) -> str:
        return self._guard(lambda: self._ctl().type_text(text, self._shared.timeout))


class BrowserKeyTool(_BrowserTool):
    name = "browser_key"
    description = "Press a key in the hidden browser, e.g. 'Enter', 'Tab', 'ArrowDown'."
    parameters = {
        "type": "object",
        "properties": {"key": {"type": "string"}},
        "required": ["key"],
    }

    def run(self, key: str = "", **_: Any) -> str:
        if not key.strip():
            raise ToolError("key must not be empty")
        return self._guard(lambda: self._ctl().press_key(key, self._shared.timeout))


def browser_tools(shared: _SharedBrowser | None = None) -> list[Tool]:
    shared = shared or _SharedBrowser()
    return [
        BrowserOpenTool(shared),
        BrowserScreenshotTool(shared),
        BrowserClickTool(shared),
        BrowserTypeTool(shared),
        BrowserKeyTool(shared),
    ]
