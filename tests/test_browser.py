"""Hidden-browser tool tests using a fake controller (no real Playwright)."""

from __future__ import annotations

from collections.abc import Iterator

from oshell.browser import BrowserUnavailable
from oshell.config import BrowserConfig, Config
from oshell.providers.base import ChatChunk, LLMProvider, ToolCall
from oshell.tools import ToolRegistry, default_registry
from oshell.tools.base import ToolResult
from oshell.tools.browser import (
    BrowserClickTool,
    BrowserKeyTool,
    BrowserOpenTool,
    BrowserScreenshotTool,
    BrowserTypeTool,
)


class FakeBrowser:
    def __init__(self):
        self.calls = []

    def open(self, url, timeout=60):
        self.calls.append(("open", url))
        return f"opened {url} — title: 'X'"

    def screenshot_png(self, timeout=60):
        return b"\x89PNG\r\nPAGE"

    def current_url(self, timeout=30):
        return "https://example.com/"

    def click(self, x, y, timeout=60):
        self.calls.append(("click", x, y))
        return f"clicked ({x}, {y})"

    def type_text(self, text, timeout=60):
        self.calls.append(("type", text))
        return f"typed {len(text)} chars"

    def press_key(self, key, timeout=60):
        self.calls.append(("key", key))
        return f"pressed {key}"


class _Shared:
    def __init__(self, ctl):
        self._ctl = ctl

    @property
    def timeout(self):
        return 60.0

    def get(self):
        if self._ctl is None:
            raise BrowserUnavailable("playwright not installed")
        return self._ctl


def test_open_requires_http():
    reg = ToolRegistry([BrowserOpenTool(_Shared(FakeBrowser()))])
    out = reg.dispatch(ToolCall(name="browser_open", arguments={"url": "ftp://x"}))
    assert out.startswith("[error]") and "http" in out


def test_open_navigates():
    fake = FakeBrowser()
    out = BrowserOpenTool(_Shared(fake)).run(url="https://example.com")
    assert "opened https://example.com" in out
    assert ("open", "https://example.com") in fake.calls


def test_screenshot_returns_image():
    out = BrowserScreenshotTool(_Shared(FakeBrowser())).run()
    assert isinstance(out, ToolResult)
    assert out.images and len(out.images) == 1
    assert "example.com" in out.text


def test_click_type_key():
    fake = FakeBrowser()
    shared = _Shared(fake)
    BrowserClickTool(shared).run(x="40", y="60")  # stringified coords coerced
    BrowserTypeTool(shared).run(text="hello")
    BrowserKeyTool(shared).run(key="Enter")
    assert ("click", 40, 60) in fake.calls
    assert ("type", "hello") in fake.calls
    assert ("key", "Enter") in fake.calls


def test_empty_key_rejected():
    out = ToolRegistry([BrowserKeyTool(_Shared(FakeBrowser()))]).dispatch(
        ToolCall(name="browser_key", arguments={"key": ""})
    )
    assert out.startswith("[error]")


def test_unavailable_is_soft_error():
    reg = ToolRegistry([BrowserScreenshotTool(_Shared(None))])
    out = reg.dispatch(ToolCall(name="browser_screenshot", arguments={}))
    assert out.startswith("[error]") and "playwright" in out


def test_browser_tools_are_net_not_sensitive():
    t = BrowserOpenTool(_Shared(FakeBrowser()))
    assert t.local_only is False and t.sensitive is False


# ── gating ──────────────────────────────────────────────────────────────────
class _CapProvider(LLMProvider):
    name = "cap"

    def __init__(self, caps):
        self._caps = set(caps)

    def list_models(self):
        return ["m"]

    def capabilities(self, model):
        return self._caps

    def chat(self, messages, **kwargs) -> Iterator[ChatChunk]:
        yield ChatChunk(done=True)


def _active(caps, enabled):
    cfg = Config(browser=BrowserConfig(enabled=enabled))
    reg = default_registry(_CapProvider(caps), cfg, model="m")
    return {t.name for t in reg.active()}


def test_browser_tools_gated():
    assert "browser_open" not in _active({"vision", "tools"}, enabled=False)  # off by default
    on = _active({"vision", "tools"}, enabled=True)  # on + vision -> present
    assert {"browser_open", "browser_screenshot", "browser_click"} <= on
    assert "browser_open" not in _active({"tools"}, enabled=True)  # non-vision -> absent


def test_browser_preferred_in_prompt():
    from oshell.agent.loop import build_system_prompt
    from oshell.tools.browser import browser_tools

    prompt = build_system_prompt(ToolRegistry(browser_tools(_Shared(FakeBrowser()))))
    assert "HIDDEN BROWSER" in prompt and "off-screen" in prompt
    assert "fetch_url" in prompt  # told to use fetch_url for static reads
