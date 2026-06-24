"""GUI computer-use tests using a fake controller (no real screen/permissions)."""

from __future__ import annotations

from collections.abc import Iterator

from oshell.config import Config, GuiConfig
from oshell.gui.controller import Controller, GuiUnavailable
from oshell.providers.base import ChatChunk, LLMProvider, ToolCall
from oshell.tools import ToolRegistry, default_registry
from oshell.tools.base import ToolResult
from oshell.tools.builtins import CurrentTimeTool
from oshell.tools.gui import ClickTool, PressKeyTool, ScreenshotTool, TypeTextTool


class FakeController(Controller):
    name = "fake"

    def __init__(self):
        self.calls: list[tuple] = []

    def screen_size(self):
        return (1920, 1080)

    def screenshot_png(self):
        return b"\x89PNG\r\nFAKE"

    def move(self, x, y):
        self.calls.append(("move", x, y))

    def click(self, x, y, button="left", clicks=1):
        self.calls.append(("click", x, y, button, clicks))

    def type_text(self, text):
        self.calls.append(("type", text))

    def press_key(self, key):
        self.calls.append(("key", key))


class _Shared:
    def __init__(self, ctl):
        self._ctl = ctl

    def get(self):
        if self._ctl is None:
            raise GuiUnavailable("no GUI here")
        return self._ctl


def test_screenshot_returns_image():
    fake = FakeController()
    out = ScreenshotTool(_Shared(fake)).run()
    assert isinstance(out, ToolResult)
    assert out.images and len(out.images) == 1
    assert "1920x1080" in out.text


def test_click_type_key_call_controller():
    fake = FakeController()
    shared = _Shared(fake)
    ClickTool(shared).run(x="100", y="200", button="left")  # stringified coords coerced
    TypeTextTool(shared).run(text="hello")
    PressKeyTool(shared).run(key="cmd+space")
    assert ("click", 100, 200, "left", 1) in fake.calls
    assert ("type", "hello") in fake.calls
    assert ("key", "cmd+space") in fake.calls


def test_gui_unavailable_is_soft_error():
    reg = ToolRegistry([ScreenshotTool(_Shared(None))])
    out = reg.dispatch(ToolCall(name="screenshot", arguments={}))
    assert out.startswith("[error]") and "GUI" in out


def test_empty_key_rejected():
    out = ToolRegistry([PressKeyTool(_Shared(FakeController()))]).dispatch(
        ToolCall(name="gui_key", arguments={"key": " "})
    )
    assert out.startswith("[error]")


# ── agent loop attaches screenshot images to the tool-result message ─────────
class _ScreenshotThenDone(LLMProvider):
    name = "s"

    def __init__(self):
        self.calls = 0

    def list_models(self):
        return ["m"]

    def chat(self, messages, **kwargs) -> Iterator[ChatChunk]:
        self.calls += 1
        if self.calls == 1:
            yield ChatChunk(tool_calls=[ToolCall(name="screenshot", arguments={})], done=True)
        else:
            yield ChatChunk(content="I can see the screen.", done=True)


def test_loop_attaches_screenshot_image():
    from oshell.agent import Agent

    reg = ToolRegistry([ScreenshotTool(_Shared(FakeController()))])
    agent = Agent(_ScreenshotThenDone(), reg, Config())
    list(agent.send("what's on screen?"))
    tool_msgs = [m for m in agent.messages if m.role == "tool"]
    assert tool_msgs and tool_msgs[0].images  # screenshot image fed back for the model
    assert tool_msgs[0].to_wire()["images"]


# ── registration gating ──────────────────────────────────────────────────---
class _CapProvider(LLMProvider):
    name = "cap"

    def __init__(self, caps):
        self._caps = set(caps)

    def list_models(self):
        return ["m"]

    def capabilities(self, model):
        return self._caps

    def chat(self, messages, **kwargs):
        yield ChatChunk(done=True)


def _names(provider, gui_enabled, model):
    cfg = Config(gui=GuiConfig(enabled=gui_enabled))
    reg = default_registry(provider, cfg, model=model)
    return {t.name for t in reg.active()}


def test_gui_tools_gated_off_by_default():
    names = _names(_CapProvider({"vision", "tools"}), gui_enabled=False, model="m")
    assert "screenshot" not in names  # opt-in


def test_gui_tools_require_vision_and_tools():
    # enabled but vision-only model -> no GUI tools
    assert "screenshot" not in _names(_CapProvider({"vision"}), True, "m")
    # enabled + vision AND tools -> GUI tools present
    names = _names(_CapProvider({"vision", "tools"}), True, "m")
    assert {"screenshot", "gui_click", "gui_type", "gui_key", "gui_move"} <= names


def test_gui_tools_absent_without_model():
    cfg = Config(gui=GuiConfig(enabled=True))
    names = {t.name for t in default_registry(_CapProvider({"vision", "tools"}), cfg).active()}
    assert "screenshot" not in names  # no model -> can't confirm vision -> skip


def test_gui_tools_are_sensitive():
    assert ScreenshotTool(_Shared(FakeController())).sensitive is True
    assert CurrentTimeTool().sensitive is False
