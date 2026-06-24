"""GUI computer-use: control the desktop (screenshots + mouse/keyboard).

Opt-in and vision-model-gated — the model must *see* screenshots to act. A thin
``Controller`` abstraction keeps the agent/tools independent of the backend:
pyautogui is the default (macOS/Windows/X11 Linux), with a clean seam to add
native backends (Wayland ``grim``/``ydotool``, macOS ``screencapture``/``cliclick``)
later without touching the tools.
"""

from __future__ import annotations

from .controller import Controller, GuiUnavailable, PyAutoGuiBackend, get_controller

__all__ = ["Controller", "GuiUnavailable", "PyAutoGuiBackend", "get_controller"]
