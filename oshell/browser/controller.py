"""A persistent Playwright browser confined to one owner thread.

Playwright's *sync* objects are thread-affine, but the agent runs each turn in a
fresh worker thread — so we can't create the browser in one thread and use it in
another. This controller owns a single long-lived thread; every operation is a
closure marshalled to that thread via a queue and awaited. The browser therefore
persists across turns with no thread-affinity errors.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from typing import Any


class BrowserUnavailable(RuntimeError):
    """Playwright isn't installed, or its Chromium browser isn't available."""


_STOP = object()


class BrowserController:
    def __init__(self, headless: bool = True, width: int = 1280, height: int = 800):
        self._headless = headless
        self._size = {"width": width, "height": height}
        self._q: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._fatal: Exception | None = None  # set if the browser couldn't start
        self._lock = threading.Lock()

    # ── the owner thread ──────────────────────────────────────────────────────
    def _ensure(self) -> None:
        if self._thread is not None:
            return
        ready = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(ready,), daemon=True)
        self._thread.start()
        ready.wait(timeout=60)
        if self._fatal is not None:
            raise self._fatal

    def _run(self, ready: threading.Event) -> None:
        page = None
        pw = browser = None
        try:
            from playwright.sync_api import sync_playwright  # type: ignore

            pw = sync_playwright().start()
            browser = pw.chromium.launch(headless=self._headless)
            page = browser.new_page(viewport=self._size)
        except ImportError:
            self._fatal = BrowserUnavailable(
                "browser control needs the 'browser' extra: install it from the menu "
                "(Install features) or `./install.sh browser`"
            )
            ready.set()
            self._drain()
            return
        except Exception as exc:  # e.g. chromium not installed: `playwright install chromium`
            self._fatal = BrowserUnavailable(
                f"could not launch the browser: {exc}. Try `playwright install chromium`."
            )
            ready.set()
            self._drain()
            return
        ready.set()
        try:
            while True:
                item = self._q.get()
                if item is _STOP:
                    break
                fn, box, done = item
                try:
                    box["result"] = fn(page)
                except Exception as exc:  # report per-call errors to the caller
                    box["error"] = exc
                finally:
                    done.set()
        finally:
            try:
                if browser:
                    browser.close()
                if pw:
                    pw.stop()
            except Exception:
                pass

    def _drain(self) -> None:
        """After a fatal start error, fail any queued/future calls instead of hanging."""
        while True:
            item = self._q.get()
            if item is _STOP:
                return
            _fn, box, done = item
            box["error"] = self._fatal
            done.set()

    def _call(self, fn: Callable[[Any], Any], timeout: float = 60.0) -> Any:
        with self._lock:  # serialize; the owner thread handles one call at a time
            self._ensure()
            box: dict[str, Any] = {}
            done = threading.Event()
            self._q.put((fn, box, done))
            if not done.wait(timeout):
                raise BrowserUnavailable(f"browser operation timed out after {timeout:g}s")
            if "error" in box:
                raise box["error"]
            return box["result"]

    def close(self) -> None:
        if self._thread is not None:
            self._q.put(_STOP)
            self._thread = None

    # ── operations (each runs on the owner thread) ────────────────────────────
    def open(self, url: str, timeout: float = 60.0) -> str:
        def _go(page):
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            return f"opened {url} — title: {page.title()!r}"

        return self._call(_go, timeout)

    def screenshot_png(self, timeout: float = 60.0) -> bytes:
        return self._call(lambda page: page.screenshot(full_page=False), timeout)

    def current_url(self, timeout: float = 30.0) -> str:
        return self._call(lambda page: page.url, timeout)

    def click(self, x: int, y: int, timeout: float = 60.0) -> str:
        self._call(lambda page: page.mouse.click(x, y), timeout)
        return f"clicked ({x}, {y})"

    def type_text(self, text: str, timeout: float = 60.0) -> str:
        self._call(lambda page: page.keyboard.type(text, delay=10), timeout)
        return f"typed {len(text)} chars"

    def press_key(self, key: str, timeout: float = 60.0) -> str:
        self._call(lambda page: page.keyboard.press(key), timeout)
        return f"pressed {key}"
