"""TUI tests using Textual's pilot. Skips cleanly if textual isn't installed."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

pytest.importorskip("textual")

from oshell.agent import Agent  # noqa: E402
from oshell.config import Config  # noqa: E402
from oshell.providers.base import ChatChunk, LLMProvider, Message, ToolCall  # noqa: E402
from oshell.tools import ToolRegistry  # noqa: E402
from oshell.tools.builtins import CurrentTimeTool  # noqa: E402
from oshell.tui.app import ContextInspector, OllamaShellTUI, ToolsPanel  # noqa: E402


class _Scripted(LLMProvider):
    name = "scripted"

    def list_models(self) -> list[str]:
        return ["scripted-model"]

    def chat(self, messages: list[Message], **kwargs: Any) -> Iterator[ChatChunk]:
        yield ChatChunk(content="hello from the model", done=True)


def _app() -> OllamaShellTUI:
    cfg = Config()
    reg = ToolRegistry([CurrentTimeTool()])
    # Disable the startup menu modal so these tests drive the main view directly.
    return OllamaShellTUI(Agent(_Scripted(), reg, cfg), show_menu_on_start=False)


async def test_tui_mounts_and_shows_tools():
    app = _app()
    async with app.run_test() as pilot:
        # The tools panel lists the active tool roster + optional features.
        tools_text = app.query_one(ToolsPanel).text
        assert "current_time" in tools_text
        assert "Optional features" in tools_text
        # Header reflects the provider and tool count.
        assert "scripted" in app.sub_title and "1 tools" in app.sub_title
        await pilot.pause()


async def test_tui_processes_a_turn():
    from textual.widgets import RichLog

    app = _app()
    async with app.run_test() as pilot:
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "hi there"
        await pilot.pause()
        await pilot.press("enter")
        # Worker thread runs agent.send(); poll until the turn is recorded.
        for _ in range(60):
            if any(m.role == "assistant" and "hello from the model" in m.content
                   for m in app.agent.messages):
                break
            await pilot.pause(0.05)
        assert app.agent.messages[-1].content == "hello from the model"
        # And the conversation pane received output (user echo + reply).
        assert len(app.query_one("#conversation", RichLog).lines) >= 2
        assert app._busy is False  # indicator cleared when the turn finished


async def test_live_indicator_states():
    app = _app()
    async with app.run_test():
        app._busy = False
        app._tick()
        assert app._live_text == ""  # idle: empty

        app._busy, app._status, app._stream = True, "Thinking", ""
        app._tick()
        assert "Thinking" in app._live_text  # spinner + status

        app._stream = "partial answer"
        app._tick()
        assert "partial answer" in app._live_text  # streamed reply preview

        app._busy = False
        app._tick()
        assert app._live_text == ""  # cleared when done


async def test_context_inspector_renders():
    app = _app()
    async with app.run_test():
        text = app.query_one(ContextInspector).text
        assert "Context" in text and "syst" in text  # system message row


async def test_escape_opens_menu_then_closes():
    # Esc is the primary menu key (F-keys are unreliable on macOS).
    from oshell.tui.menu import MenuScreen

    app = _app()
    async with app.run_test() as pilot:
        await pilot.press("escape")  # chat -> menu
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)
        await pilot.press("escape")  # menu -> chat
        await pilot.pause()
        assert not isinstance(app.screen, MenuScreen)


async def test_f2_still_opens_menu():
    # Hidden alternate binding for non-macOS keyboards.
    from oshell.tui.menu import MenuScreen

    app = _app()
    async with app.run_test() as pilot:
        await pilot.press("f2")
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)


async def test_models_menu_opens_picker_and_sets_model():
    from oshell.tui.menu import MenuScreen, ModelScreen

    app = _app()  # starts on default model "llama3"
    assert app.agent.model != "scripted-model"
    async with app.run_test() as pilot:
        await pilot.press("escape")  # open menu
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)
        await pilot.press("2")  # "2. Models" -> opens the picker (in a worker)
        for _ in range(40):
            await pilot.pause(0.05)
            if isinstance(app.screen, ModelScreen):
                break
        assert isinstance(app.screen, ModelScreen)
        await pilot.press("1")  # pick the first model -> "scripted-model"
        await pilot.pause()
        assert not isinstance(app.screen, ModelScreen)
        assert app.agent.model == "scripted-model"  # active model actually changed


def test_result_summary_is_honest():
    from oshell.tui.app import _compact_args, _summarize_result

    assert "no results" in _summarize_result("(no results)")
    assert "no results" in _summarize_result("")
    # plain text (no Rich markup — the caller escapes it)
    assert _summarize_result("[error] web search failed: boom").startswith("[error]")
    s = _summarize_result("Title\nhttps://x\nbody text")
    assert "chars" in s and "Title" in s
    assert _compact_args({"query": "hi", "max_results": 5}) == "query=hi, max_results=5"


def _convo_text(app) -> str:
    from textual.widgets import RichLog

    log = app.query_one("#conversation", RichLog)
    return "\n".join("".join(seg.text for seg in line) for line in log.lines)


async def test_tool_call_is_shown_inline():
    # A model that calls a tool (round 1) then answers (round 2).
    class _ToolThenText(LLMProvider):
        name = "tt"

        def __init__(self):
            self.calls = 0

        def list_models(self):
            return ["m"]

        def chat(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                yield ChatChunk(tool_calls=[ToolCall(name="current_time", arguments={})], done=True)
            else:
                yield ChatChunk(content="Done.", done=True)

    app = OllamaShellTUI(
        Agent(_ToolThenText(), ToolRegistry([CurrentTimeTool()]), Config()),
        show_menu_on_start=False,
    )
    async with app.run_test() as pilot:
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "what time is it?"
        await pilot.pause()
        await pilot.press("enter")
        for _ in range(60):
            await pilot.pause(0.05)
            if not app._busy and "Done." in _convo_text(app):
                break
        text = _convo_text(app)
        assert "🔧 current_time" in text  # the real call is visible inline
        assert "↳" in text  # ...with its result summary


def test_pip_install_cmd_builder():
    from oshell.tui.app import pip_install_cmd

    cmd = pip_install_cmd(["chromadb>=0.4.18", "sentence-transformers"])
    assert "install" in cmd
    assert "chromadb>=0.4.18" in cmd and "sentence-transformers" in cmd


def test_run_streaming_emits_lines_live():
    import sys

    from oshell.tui.app import run_streaming

    seen = []
    script = "import sys\nfor i in range(3): print('step', i); sys.stdout.flush()"
    rc = run_streaming([sys.executable, "-c", script], seen.append)
    assert rc == 0
    assert seen == ["step 0", "step 1", "step 2"]  # streamed in order, blank lines dropped


def test_run_streaming_returns_nonzero_on_failure():
    import sys

    from oshell.tui.app import run_streaming

    rc = run_streaming([sys.executable, "-c", "import sys; sys.exit(3)"], lambda _l: None)
    assert rc == 3


async def test_features_menu_opens():
    from oshell.tui.menu import MENU_ITEMS, FeaturesScreen, MenuScreen

    # Find "features" by id rather than a hard-coded index (order may change).
    num = next(i for i, (cid, *_rest) in enumerate(MENU_ITEMS, start=1) if cid == "features")
    app = _app()
    async with app.run_test() as pilot:
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)
        await pilot.press(str(num))
        await pilot.pause()
        assert isinstance(app.screen, FeaturesScreen)


async def test_already_installed_feature_reports_without_installing(monkeypatch):
    # Pretend every feature is already installed -> no subprocess, just a note.
    monkeypatch.setattr("oshell.tui.app.feature_installed", lambda mods: True)
    app = _app()
    async with app.run_test() as pilot:
        app._on_feature_choice("rag")
        await pilot.pause()
        assert "already installed" in _convo_text(app)


async def test_model_choice_persists_default(tmp_path, monkeypatch):
    import json

    monkeypatch.chdir(tmp_path)  # update_local_config writes to cwd
    app = _app()
    async with app.run_test() as pilot:
        app._on_model_choice("my-chosen-model")
        await pilot.pause()
    assert app.agent.model == "my-chosen-model"
    saved = json.loads((tmp_path / "config.local.json").read_text())
    assert saved["default_model"] == "my-chosen-model"


async def test_multiline_paste_buffers_and_sends():
    from textual import events
    from textual.widgets import Input

    app = _app()
    async with app.run_test() as pilot:
        inp = app.query_one(Input)
        inp.focus()
        await pilot.pause()
        inp.post_message(events.Paste("line1\nline2\nline3"))  # multi-line paste
        await pilot.pause()
        # Buffered (not lost to first line), input stays clean.
        assert app._pending_paste == "line1\nline2\nline3"
        assert inp.value == ""
        # Type a question and submit; the pasted block is included.
        inp.value = "summarize this"
        await pilot.press("enter")
        for _ in range(40):
            await pilot.pause(0.05)
            if any(m.role == "user" for m in app.agent.messages):
                break
        user_msg = next(m for m in app.agent.messages if m.role == "user")
        assert "line1" in user_msg.content and "line3" in user_msg.content
        assert "summarize this" in user_msg.content
        assert app._pending_paste == ""  # consumed


async def test_singleline_paste_still_inserts_normally():
    from textual import events
    from textual.widgets import Input

    app = _app()
    async with app.run_test() as pilot:
        inp = app.query_one(Input)
        inp.focus()
        await pilot.pause()
        inp.post_message(events.Paste("just one line"))
        await pilot.pause()
        assert inp.value == "just one line"  # normal Input paste behavior preserved
        assert app._pending_paste == ""


def test_image_path_to_b64(tmp_path):
    import base64

    from oshell.tui.app import image_path_to_b64

    f = tmp_path / "x.png"
    f.write_bytes(b"\x89PNG\r\n_data_")
    assert base64.b64decode(image_path_to_b64(str(f))) == b"\x89PNG\r\n_data_"
    with pytest.raises(ValueError):
        image_path_to_b64(str(tmp_path / "missing.png"))


def test_clipboard_image_no_image(monkeypatch):
    pytest.importorskip("PIL")  # clipboard grab needs Pillow (the 'vision'/'gui' extra)
    import PIL.ImageGrab

    from oshell.tui.app import clipboard_image_b64

    monkeypatch.setattr(PIL.ImageGrab, "grabclipboard", lambda: None)
    with pytest.raises(ValueError, match="no image"):
        clipboard_image_b64()


async def test_attach_image_then_send_includes_it(tmp_path):
    from textual.widgets import Input

    f = tmp_path / "img.png"
    f.write_bytes(b"\x89PNGfakepixels")
    app = _app()
    async with app.run_test() as pilot:
        app._on_attach_image(str(f))  # attach by path
        await pilot.pause()
        assert len(app._pending_images) == 1
        inp = app.query_one(Input)
        inp.focus()
        inp.value = "what is in this image?"
        await pilot.pause()
        await pilot.press("enter")
        for _ in range(40):
            await pilot.pause(0.05)
            if any(m.role == "user" for m in app.agent.messages):
                break
        user = next(m for m in app.agent.messages if m.role == "user")
        assert user.images and len(user.images) == 1
        assert user.content == "what is in this image?"
        assert app._pending_images == []  # consumed


def test_transcript_builder():
    app = _app()
    app.agent.messages.append(Message(role="user", content="what is 2+2?"))
    app.agent.messages.append(Message(role="assistant", content="4"))
    t = app._transcript()
    assert "> what is 2+2?" in t and "4" in t


async def test_copy_reply_uses_clipboard(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "oshell.tui.app.clipboard_write", lambda text: captured.update(text=text) or True
    )
    app = _app()
    async with app.run_test() as pilot:
        app._last_reply = "the answer is 42"
        app.action_copy_reply()  # Ctrl+Y path
        await pilot.pause()
        assert captured["text"] == "the answer is 42"


async def test_copy_falls_back_to_osc52(monkeypatch):
    monkeypatch.setattr("oshell.tui.app.clipboard_write", lambda text: False)  # no CLI clipboard
    osc = {}
    app = _app()
    async with app.run_test() as pilot:
        monkeypatch.setattr(app, "copy_to_clipboard", lambda text: osc.update(text=text))
        app._copy("hello", "thing")
        await pilot.pause()
        assert osc["text"] == "hello"  # OSC52 fallback used


async def test_copy_nothing_is_safe():
    app = _app()
    async with app.run_test() as pilot:
        app._last_reply = ""
        app.action_copy_reply()  # should not raise, just note
        await pilot.pause()


async def test_gui_toggle_activates_tools(monkeypatch, tmp_path):
    # A vision+tools model so GUI tools can actually register when toggled on.
    monkeypatch.chdir(tmp_path)  # persist gui flag into a throwaway config.local.json

    class _VisionProvider(LLMProvider):
        name = "v"

        def list_models(self):
            return ["vmodel"]

        def capabilities(self, model):
            return {"vision", "tools"}

        def chat(self, messages, **kwargs):
            yield ChatChunk(content="ok", done=True)

    # pyautogui is installed in the dev env, so the controller import path is fine.
    pytest.importorskip("pyautogui")
    cfg = Config()
    app = OllamaShellTUI(
        Agent(_VisionProvider(), ToolRegistry([CurrentTimeTool()]), cfg, model="vmodel"),
        show_menu_on_start=False,
    )
    # The agent's registry starts without GUI; rebuild via the app on toggle.
    async with app.run_test() as pilot:
        assert not app.agent.config.gui.enabled
        app._toggle_gui()
        await pilot.pause()
        assert app.agent.config.gui.enabled is True
        names = {t.name for t in app.agent.registry.active()}
        assert "screenshot" in names and "gui_click" in names
        # The model is now told about them:
        assert "screenshot" in app.agent.messages[0].content
        # Toggle back off:
        app._toggle_gui()
        await pilot.pause()
        assert app.agent.config.gui.enabled is False
        assert "screenshot" not in {t.name for t in app.agent.registry.active()}


async def test_markup_in_messages_does_not_crash():
    # Regression: message content with Rich-markup-like brackets (e.g. a markdown
    # link or a stray [/dim]) must not crash the context inspector or conversation.
    from oshell.tui.app import ContextInspector

    class _MarkupProvider(LLMProvider):
        name = "mk"

        def list_models(self):
            return ["m"]

        def chat(self, messages, **kwargs):
            yield ChatChunk(content="see [the docs](http://x) and a stray [/dim] tag", done=True)

    app = OllamaShellTUI(
        Agent(_MarkupProvider(), ToolRegistry([CurrentTimeTool()]), Config()),
        show_menu_on_start=False,
    )
    async with app.run_test() as pilot:
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "give me a [link] please"  # brackets in the user message too
        await pilot.pause()
        await pilot.press("enter")
        for _ in range(40):
            await pilot.pause(0.05)
            if app.agent.messages[-1].role == "assistant":
                break
        # No exception bubbled; the inspector rendered with the bracketed content.
        app.query_one(ContextInspector).refresh_view(app.agent)
        await pilot.pause()
        assert "the docs" in app.query_one(ContextInspector).text


async def test_menu_shows_on_startup_when_enabled():
    from oshell.tui.menu import MenuScreen

    cfg = Config()
    app = OllamaShellTUI(Agent(_Scripted(), ToolRegistry([CurrentTimeTool()]), cfg))
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)  # greeted with the menu
