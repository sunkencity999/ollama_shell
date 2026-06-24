"""Hidden browser computer-use (Playwright).

A dedicated, optionally-headless Chromium the model drives — navigate, screenshot
(fed back so a vision model can see the page), click, type — so web tasks happen
off-screen instead of hijacking the user's desktop. Opt-in; needs the ``[browser]``
extra (``playwright`` + ``playwright install chromium``).
"""

from __future__ import annotations

from .controller import BrowserController, BrowserUnavailable

__all__ = ["BrowserController", "BrowserUnavailable"]
