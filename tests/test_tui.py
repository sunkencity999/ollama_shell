"""TUI tests using Textual's pilot. Skips cleanly if textual isn't installed."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
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
    from oshell.tui.menu import MENU_ITEMS, MenuScreen, ModelScreen

    num = next(i for i, (cid, *_r) in enumerate(MENU_ITEMS, start=1) if cid == "models")
    app = _app()  # starts on default model "llama3"
    assert app.agent.model != "scripted-model"
    async with app.run_test() as pilot:
        await pilot.press("escape")  # open menu
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)
        await pilot.press(str(num))  # "Models" -> opens the picker (in a worker)
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


def _toasts(app) -> str:
    """All toast-notification messages raised so far, joined for assertions."""
    return " | ".join(n.message for n in app._notifications)


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
        # Status chatter lives in toasts now, not the transcript.
        assert "already installed" in _toasts(app)
        assert "already installed" not in _convo_text(app)


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
        # _copy's fallback goes straight to the App base (OllamaShellTUI's own
        # copy_to_clipboard override would loop back through clipboard_write).
        from textual.app import App

        monkeypatch.setattr(
            App, "copy_to_clipboard", lambda self, text: osc.update(text=text)
        )
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


async def test_panels_survive_hostile_content():
    # Regression: scraped/fetched content can carry ANSI escapes, control chars,
    # stray markup tags and unbalanced brackets. A side-panel render must never
    # crash the session mid-turn (which previously lost in-flight research).
    from oshell.tui.app import ContextInspector, ToolsPanel

    nasty = "\x1b[31mred\x1b[0m [b]unbalanced [/dim] \x00\x07 \\[ done](http://x"
    app = _app()
    async with app.run_test() as pilot:
        app.agent.messages.append(Message(role="assistant", content=nasty))
        app.query_one(ContextInspector).refresh_view(app.agent)
        app.query_one(ToolsPanel).render_for(app.agent)
        await pilot.pause()
        # Readable text is still inspectable (plain, no exception bubbled).
        assert "Context" in app.query_one(ContextInspector).text
        assert "Active tools" in app.query_one(ToolsPanel).text


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


async def test_gui_turn_notifies_and_refocuses(monkeypatch):
    from oshell import desktop
    from oshell.tools.gui import ScreenshotTool

    notified, refocused = [], []
    monkeypatch.setattr(desktop, "notify", lambda *a: notified.append(a))
    monkeypatch.setattr(desktop, "focus_terminal", lambda: refocused.append(True))

    class _ScreenshotProvider(LLMProvider):
        name = "s"

        def __init__(self):
            self.calls = 0

        def list_models(self):
            return ["m"]

        def chat(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                yield ChatChunk(tool_calls=[ToolCall(name="screenshot", arguments={})], done=True)
            else:
                yield ChatChunk(content="done", done=True)

    # A fake GUI controller so screenshot succeeds without a real screen.
    class _FakeShared:
        def get(self):
            class _C:
                def screen_size(self):
                    return (10, 10)

                def screenshot_b64(self):
                    return "B64"

            return _C()

    reg = ToolRegistry([ScreenshotTool(_FakeShared())])
    app = OllamaShellTUI(Agent(_ScreenshotProvider(), reg, Config()), show_menu_on_start=False)
    async with app.run_test() as pilot:
        app.query_one("Input").focus()
        app.query_one("Input").value = "look at my screen"
        await pilot.pause()
        await pilot.press("enter")
        for _ in range(60):
            await pilot.pause(0.05)
            done = any(m.role == "assistant" and m.content for m in app.agent.messages)
            if not app._busy and done:
                break
        assert notified and refocused  # GUI turn -> user is told + terminal raised


async def test_normal_turn_does_not_notify(monkeypatch):
    from oshell import desktop

    notified = []
    monkeypatch.setattr(desktop, "notify", lambda *a: notified.append(a))
    app = _app()
    async with app.run_test() as pilot:
        app.query_one("Input").focus()
        app.query_one("Input").value = "hello"
        await pilot.pause()
        await pilot.press("enter")
        for _ in range(40):
            await pilot.pause(0.05)
            if not app._busy:
                break
        assert not notified  # no GUI used -> no notification spam


async def test_session_persist_and_resume(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # config.local.json writes isolated
    cfg = Config()
    cfg.session.path = str(tmp_path / "sess.json")

    def make_app():
        return OllamaShellTUI(
            Agent(_Scripted(), ToolRegistry([CurrentTimeTool()]), cfg), show_menu_on_start=False
        )

    # First app: have a turn, which persists the transcript.
    app1 = make_app()
    async with app1.run_test() as pilot:
        app1.query_one("Input").focus()
        app1.query_one("Input").value = "remember the alamo"
        await pilot.pause()
        await pilot.press("enter")
        for _ in range(40):
            await pilot.pause(0.05)
            if not app1._busy and any(m.role == "assistant" for m in app1.agent.messages):
                break

    # Second app with the same session path resumes the prior messages.
    app2 = make_app()
    async with app2.run_test():
        contents = [m.content for m in app2.agent.messages]
        assert "remember the alamo" in contents
        assert "hello from the model" in contents


async def test_new_conversation_clears(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = _app()
    app.agent.config.session.path = str(tmp_path / "sess.json")
    async with app.run_test() as pilot:
        app.agent.messages.append(Message(role="user", content="something"))
        app._new_conversation()
        await pilot.pause()
        # Only the system message remains.
        assert [m.role for m in app.agent.messages] == ["system"]


async def test_slash_daydream_runs_without_touching_history(tmp_path, monkeypatch):
    from textual.widgets import RichLog

    monkeypatch.chdir(tmp_path)
    app = _app()
    async with app.run_test() as pilot:
        before = len(app.agent.messages)
        n0 = len(app.query_one("#conversation", RichLog).lines)
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "/daydream"
        await pilot.pause()
        await pilot.press("enter")
        for _ in range(40):
            await pilot.pause(0.05)
            if not app._busy:
                break
        assert app._busy is False
        # A daydream is ephemeral: it must NOT append to conversation history...
        assert len(app.agent.messages) == before
        # ...but it did render something to the screen.
        assert len(app.query_one("#conversation", RichLog).lines) > n0


async def test_daydream_opens_dream_screen_and_wakes_on_key(tmp_path, monkeypatch):
    from oshell.tui.dream import DreamScreen

    monkeypatch.chdir(tmp_path)
    app = _app()  # fun.effects defaults on
    async with app.run_test() as pilot:
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "/daydream"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, DreamScreen)  # the sky takes the stage
        for _ in range(40):
            await pilot.pause(0.05)
            if not app._busy:
                break
        assert app.screen._done is True  # dream finished streaming
        assert "hello from the model" in app.screen._text
        await pilot.press("space")  # any key wakes the shell
        await pilot.pause()
        assert not isinstance(app.screen, DreamScreen)


async def test_daydream_streams_inline_when_effects_off(tmp_path, monkeypatch):
    from oshell.tui.dream import DreamScreen

    monkeypatch.chdir(tmp_path)
    app = _app()
    app.agent.config.fun.effects = False
    async with app.run_test() as pilot:
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "/daydream"
        await pilot.pause()
        await pilot.press("enter")
        for _ in range(40):
            await pilot.pause(0.05)
            if not app._busy:
                break
        # No full-screen takeover; the dream still landed in the transcript.
        assert not isinstance(app.screen, DreamScreen)
        assert len(app.agent.messages) == 1  # ephemeral either way (system only)


async def test_tick_renders_aurora_and_ember_when_busy():
    import time as _time

    from oshell.tui import ambient

    app = _app()
    async with app.run_test() as pilot:
        app._busy = True
        app._stream = ""
        app._status = "Thinking"
        app._ember = (ambient.EMBER_COLORS["net"], _time.monotonic())
        app._tick()
        await pilot.pause()
        # The spark and an aurora hue (not plain cyan) are both in the strip.
        assert ambient.EMBER_FRAMES[0] in app._live_text
        assert any(hex_ in app._live_text for hex_ in ambient.AURORA)
        app._busy = False


async def test_fireflies_appear_when_idle_and_disperse_on_activity():
    import time as _time

    app = _app()
    async with app.run_test() as pilot:
        # Idle past the strip delay but short of the full-screen takeover.
        app._idle_since = _time.monotonic() - 60
        app._tick()
        await pilot.pause()
        assert any(g in app._live_text for g in ("✦", "✧", "·"))
        app._idle_since = _time.monotonic()  # activity: flies disperse
        app._tick()
        await pilot.pause()
        assert app._live_text == ""


async def test_slash_clear_resets_conversation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = _app()
    app.agent.config.session.path = str(tmp_path / "sess.json")
    async with app.run_test() as pilot:
        app.agent.messages.append(Message(role="user", content="something"))
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "/clear"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        # /clear behaves like New conversation: only the system message remains
        # and the typed command is NOT sent to the model.
        assert [m.role for m in app.agent.messages] == ["system"]


async def test_slash_unknown_command_not_sent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = _app()
    async with app.run_test() as pilot:
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "/bogus"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        # Unknown slash command is swallowed, never forwarded to the model.
        assert not any(m.content == "/bogus" for m in app.agent.messages)


async def test_menu_shows_on_startup_when_enabled():
    from oshell.tui.menu import MenuScreen

    cfg = Config()
    app = OllamaShellTUI(Agent(_Scripted(), ToolRegistry([CurrentTimeTool()]), cfg))
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)  # greeted with the menu


# ── the beautification pass: markdown, vitals, themes, palette, heat ──────────


async def test_reply_renders_as_markdown():
    # The committed reply is rendered Markdown: bold loses its ** markers and
    # fenced code blocks come out as real code lines.
    class _MdProvider(LLMProvider):
        name = "md"

        def list_models(self):
            return ["m"]

        def chat(self, messages, **kwargs):
            yield ChatChunk(
                content="**important** point\n\n```python\nprint('hi')\n```", done=True
            )

    app = OllamaShellTUI(
        Agent(_MdProvider(), ToolRegistry([CurrentTimeTool()]), Config()),
        show_menu_on_start=False,
    )
    async with app.run_test() as pilot:
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "go"
        await pilot.pause()
        await pilot.press("enter")
        for _ in range(60):
            await pilot.pause(0.05)
            if not app._busy and "important" in _convo_text(app):
                break
        text = _convo_text(app)
        assert "important" in text and "**" not in text  # rendered, not raw markers
        assert "print" in text  # the code block survived


async def test_turn_stats_and_separator_rule():
    app = _app()
    async with app.run_test() as pilot:
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "hi"
        await pilot.pause()
        await pilot.press("enter")
        for _ in range(60):
            await pilot.pause(0.05)
            if not app._busy and "⏱" in _convo_text(app):
                break
        text = _convo_text(app)
        assert "⏱" in text and "ctx" in text  # vitals line under the reply
        assert "─" in text  # the timestamped rule that opens the exchange


async def test_tool_heat_marks_used_tools():
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
        inp.value = "time?"
        await pilot.pause()
        await pilot.press("enter")
        for _ in range(60):
            await pilot.pause(0.05)
            if not app._busy and "Done." in _convo_text(app):
                break
        assert app._tool_counts["current_time"] == 1
        assert "current_time ×1" in app.query_one(ToolsPanel).text  # heat in the panel


async def test_context_gauge_shows_fill():
    app = _app()
    async with app.run_test():
        text = app.query_one(ContextInspector).text
        assert ("▰" in text or "▱" in text) and "% of" in text


async def test_welcome_card_on_fresh_start():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        text = _convo_text(app)
        assert "fully local" in text  # the model badge
        assert "Try:" in text  # suggested prompts


async def test_theme_menu_choice_opens_picker_and_persists(tmp_path, monkeypatch):
    import json

    from oshell.tui.menu import ThemeScreen

    monkeypatch.chdir(tmp_path)
    app = _app()
    async with app.run_test() as pilot:
        app._on_menu_choice("theme")
        await pilot.pause()
        assert isinstance(app.screen, ThemeScreen)
        app.screen.dismiss("nord")  # choose programmatically
        await pilot.pause()
        assert app.theme == "nord"
        assert app.agent.config.theme == "nord"
    saved = json.loads((tmp_path / "config.local.json").read_text())
    assert saved["theme"] == "nord"


async def test_theme_screen_escape_restores_original():
    app = _app()
    async with app.run_test() as pilot:
        original = app.theme
        app._open_theme_picker()
        await pilot.pause()
        app.theme = "gruvbox"  # what a live highlight-preview does
        await pilot.press("escape")
        await pilot.pause()
        assert app.theme == original  # Esc puts the room back the way it was


async def test_theme_from_config_applied_on_mount():
    cfg = Config(theme="nord")
    app = OllamaShellTUI(
        Agent(_Scripted(), ToolRegistry([CurrentTimeTool()]), cfg), show_menu_on_start=False
    )
    async with app.run_test():
        assert app.theme == "nord"


async def test_menu_two_digit_number_selects_late_item():
    from oshell.tui.menu import MENU_ITEMS, MenuScreen

    num = next(i for i, (cid, *_r) in enumerate(MENU_ITEMS, start=1) if cid == "memory")
    assert num >= 10  # the point: this item was unreachable by number before
    app = _app()
    async with app.run_test() as pilot:
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)
        for ch in str(num):
            await pilot.press(ch)
        await pilot.pause()
        # Second digit made the number unambiguous -> selected immediately.
        assert not isinstance(app.screen, MenuScreen)
        assert "Memory" in _convo_text(app)  # memory summary rendered


async def test_menu_renders_sections_and_constellation():
    from textual.widgets import OptionList

    app = _app()  # fun.effects defaults on -> stars behind the menu
    async with app.run_test() as pilot:
        await pilot.press("escape")
        await pilot.pause()
        opts = app.screen.query_one(OptionList)
        prompts = [str(opts.get_option_at_index(i).prompt) for i in range(opts.option_count)]
        assert any("Conversation" in p for p in prompts)  # section headers present
        assert any("System" in p for p in prompts)
        assert app.screen.query("#menu-stars")  # the constellation strip


async def test_model_picker_shows_badges():
    from textual.widgets import OptionList

    from oshell.tui.menu import ModelScreen

    app = _app()
    async with app.run_test() as pilot:
        app.push_screen(
            ModelScreen(["m1", "m2"], "m1", infos={"m1": {"size": "26B", "quant": "Q8_0"}}),
            lambda _c: None,
        )
        await pilot.pause()
        opts = app.screen.query_one(OptionList)
        first = str(opts.get_option_at_index(0).prompt)
        assert "26B" in first and "Q8_0" in first


async def test_copy_code_block(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "oshell.tui.app.clipboard_write", lambda text: captured.update(text=text) or True
    )
    app = _app()
    async with app.run_test() as pilot:
        app._last_reply = "Sure:\n\n```python\nprint('hi')\n```\nthat's it"
        app.action_copy_code()  # Ctrl+B path
        await pilot.pause()
        assert captured["text"] == "print('hi')\n"


async def test_copy_code_block_without_code_warns():
    app = _app()
    async with app.run_test() as pilot:
        app._last_reply = "no code here"
        app.action_copy_code()
        await pilot.pause()
        assert "No code block" in _toasts(app)


async def test_command_palette_lists_app_commands():
    app = _app()
    async with app.run_test():
        titles = {c.title for c in app.get_system_commands(app.screen)}
        assert {"New conversation", "Pick theme", "Daydream", "Copy last code block"} <= titles


async def test_limit_burst_takes_the_strip_then_burns_out():
    import time as _time

    from oshell.tui import ambient

    app = _app()
    async with app.run_test() as pilot:
        app._burst = _time.monotonic()
        app._tick()
        await pilot.pause()
        assert any(g in app._live_text for g in "✷✶✧∗·")  # the storm is on stage
        app._burst = _time.monotonic() - ambient.BURST_SECONDS - 0.1
        app._tick()
        assert app._burst is None  # burned out


async def test_daydream_sky_takes_storm_mood(tmp_path, monkeypatch):
    from oshell.tui.dream import DreamScreen

    monkeypatch.chdir(tmp_path)
    app = _app()
    async with app.run_test() as pilot:
        app.agent.messages.append(
            Message(role="user", content="another error and a full traceback, ugh")
        )
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "/daydream"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, DreamScreen)
        assert app.screen.model.weather == "rain"  # stormy session -> rainy sky
        for _ in range(40):
            await pilot.pause(0.05)
            if not app._busy:
                break
        await pilot.press("space")


async def test_copy_notice_is_a_toast_not_transcript(monkeypatch):
    monkeypatch.setattr("oshell.tui.app.clipboard_write", lambda text: True)
    app = _app()
    async with app.run_test() as pilot:
        app._last_reply = "the answer"
        app.action_copy_reply()
        await pilot.pause()
        assert "Copied last reply" in _toasts(app)
        assert "opied" not in _convo_text(app)  # transcript stays conversation-only


# ── moods: rain (and friends) in the TUI's own idle strip ─────────────────────


async def test_slash_mood_sets_and_persists(tmp_path, monkeypatch):
    import json

    monkeypatch.chdir(tmp_path)
    app = _app()
    async with app.run_test() as pilot:
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "/mood rain"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.agent.config.fun.mood == "rain"
        assert "Mood set to rain" in _toasts(app)
        # Picking a mood shows it immediately — no waiting out the idle delay.
        app._tick()
        assert "╱" in app._live_text
    saved = json.loads((tmp_path / "config.local.json").read_text())
    assert saved["fun"]["mood"] == "rain"


async def test_slash_mood_unknown_warns(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = _app()
    async with app.run_test() as pilot:
        app._set_mood("volcano")
        await pilot.pause()
        assert "Unknown mood" in _toasts(app)
        assert app.agent.config.fun.mood == "fireflies"  # unchanged


async def test_mood_menu_opens_picker_and_selects(tmp_path, monkeypatch):
    from oshell.tui.menu import MoodScreen

    monkeypatch.chdir(tmp_path)
    app = _app()
    async with app.run_test() as pilot:
        app._on_menu_choice("mood")
        await pilot.pause()
        assert isinstance(app.screen, MoodScreen)
        app.screen.dismiss("snow")
        await pilot.pause()
        assert app.agent.config.fun.mood == "snow"


async def test_mood_none_keeps_the_strip_quiet():
    import time as _time

    app = _app()
    async with app.run_test() as pilot:
        app.agent.config.fun.mood = "none"
        app._idle_since = _time.monotonic() - 999
        app._tick()
        await pilot.pause()
        assert app._live_text == ""


async def test_dream_honors_picked_mood(tmp_path, monkeypatch):
    from oshell.tui.dream import DreamScreen

    monkeypatch.chdir(tmp_path)
    app = _app()
    async with app.run_test() as pilot:
        app.agent.config.fun.mood = "snow"  # even in June, the user asked for snow
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "/daydream"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, DreamScreen)
        assert app.screen.model.weather == "snow"
        for _ in range(40):
            await pilot.pause(0.05)
            if not app._busy:
                break
        await pilot.press("space")


async def test_context_gauge_reports_auto_size():
    app = _app()  # context_length defaults to 0 = auto; scripted provider -> 8k fallback
    async with app.run_test():
        text = app.query_one(ContextInspector).text
        assert "8k" in text and "(auto)" in text


# ── the mood takeover: weather on top of the live workspace ───────────────────


async def test_deep_idle_takes_over_then_wakes_to_strip_mood():
    import time as _time

    from oshell.tui.overlay import MoodOverlay

    app = _app()
    async with app.run_test() as pilot:
        app.agent.config.fun.mood = "rain"
        app._idle_since = _time.monotonic() - 999  # far past mood_takeover_seconds
        app._tick()
        await pilot.pause()
        assert isinstance(app.screen, MoodOverlay)  # the weather took the stage
        app._tick()  # the guard: no second overlay on top of the first
        await pilot.pause()
        assert len(app.screen_stack) == 2
        await pilot.press("space")  # any key wakes (and is swallowed)
        await pilot.pause()
        assert not isinstance(app.screen, MoodOverlay)
        app._tick()  # back in the strip, still raining — not another takeover
        await pilot.pause()
        assert "╱" in app._live_text


async def test_takeover_never_covers_a_menu():
    import time as _time

    from oshell.tui.menu import MenuScreen
    from oshell.tui.overlay import MoodOverlay

    app = _app()
    async with app.run_test() as pilot:
        await pilot.press("escape")  # open the menu
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)
        app._idle_since = _time.monotonic() - 999
        app._tick()
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)  # untouched
        assert not any(isinstance(s, MoodOverlay) for s in app.screen_stack)


async def test_takeover_disabled_by_config():
    import time as _time

    from oshell.tui.overlay import MoodOverlay

    app = _app()
    async with app.run_test() as pilot:
        app.agent.config.fun.mood_takeover_seconds = 0  # opt out
        app._idle_since = _time.monotonic() - 999
        app._tick()
        await pilot.pause()
        assert not isinstance(app.screen, MoodOverlay)
        assert app._live_text  # the strip mood still plays


async def test_overlay_renders_particles_over_translucent_screen():
    from oshell.tui.overlay import MoodOverlay, _Fleck

    app = _app()
    async with app.run_test() as pilot:
        app.push_screen(MoodOverlay("rain"))
        await pilot.pause()
        overlay = app.screen
        assert isinstance(overlay, MoodOverlay)
        shown = [f for f in overlay.query(_Fleck) if f.display]
        assert shown  # particles on stage
        first = [(f.styles.offset.x.value, f.styles.offset.y.value) for f in shown[:5]]
        overlay._frame()
        overlay._frame()
        await pilot.pause()
        shown2 = [f for f in overlay.query(_Fleck) if f.display]
        second = [(f.styles.offset.x.value, f.styles.offset.y.value) for f in shown2[:5]]
        assert first != second  # the rain moves
        await pilot.press("q")  # wake — the keystroke is swallowed
        await pilot.pause()
        assert not isinstance(app.screen, MoodOverlay)
        assert not any(m.role == "user" for m in app.agent.messages)  # "q" never landed


async def test_waking_from_daydream_keeps_the_mood(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = _app()
    async with app.run_test() as pilot:
        app.agent.config.fun.mood = "rain"
        inp = app.query_one("Input")
        inp.focus()
        inp.value = "/daydream"
        await pilot.pause()
        await pilot.press("enter")
        for _ in range(40):
            await pilot.pause(0.05)
            if not app._busy:
                break
        await pilot.press("space")  # wake from the dream
        await pilot.pause()
        app._tick()  # the rain is still falling in the strip
        await pilot.pause()
        assert "╱" in app._live_text


# ── the rice: status bar, keys overlay, themes, screensaver ──────────────────
async def test_statusbar_replaces_header_and_reports_state():
    from oshell.tui.statusbar import StatusBar

    app = _app()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        bar = app.query_one(StatusBar)
        assert not list(app.query("Header"))
        text = bar.text
        assert "oshell" in text and "llama3" in text and "scripted" in text
        assert "1" in text and "local" in text  # tool count + privacy posture
        assert "auto" in text  # approvals mode
        assert "tokyo-night" in text  # the theme name rides on the right
        # Busy state swaps the model for what the model is doing.
        app._busy, app._status = True, "Calling current_time"
        app._refresh_bar()
        assert "Calling current_time" in bar.text


async def test_statusbar_can_be_turned_off_for_the_stock_header():
    from textual.widgets import Header

    from oshell.tui.statusbar import StatusBar

    cfg = Config()
    cfg.ui.statusbar = False
    cfg.ui.gaps = False
    app = OllamaShellTUI(
        Agent(_Scripted(), ToolRegistry([CurrentTimeTool()]), cfg), show_menu_on_start=False
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        assert not list(app.query(StatusBar))
        assert app.query_one(Header)
        assert "gaps" not in app.query_one("#body").classes


def test_statusbar_render_is_pure_and_width_aware():
    from oshell.tui.statusbar import BarState, gauge, nerd_font_enabled, render_bar

    st = BarState(
        model="m", provider="p", n_tools=3, n_net=1, ctx_fill=0.9, tok_s=42.0, theme="nord"
    )
    wide = render_bar(st, 120, {}, nerd=False, clock=False)
    assert "1 net" in wide.plain and "42 tok/s" in wide.plain and "90%" in wide.plain
    assert wide.plain.rstrip().endswith("nord") and wide.cell_len <= 120
    narrow = render_bar(st, 30, {}, nerd=False, clock=False)
    assert narrow.cell_len <= 30  # never overflows the bar's row
    assert gauge(0.5) == "▰▰▱▱▱" and gauge(1.0) == "▰▰▰▰▰"
    assert nerd_font_enabled("on") and not nerd_font_enabled("off")


async def test_f1_opens_keys_overlay_and_any_key_closes_it():
    from oshell.tui.keys import KeysScreen

    app = _app()
    async with app.run_test() as pilot:
        await pilot.press("f1")
        await pilot.pause()
        assert isinstance(app.screen, KeysScreen)
        from rich.console import Console

        from oshell.tui.keys import keys_table

        rec = Console(record=True, width=100)
        rec.print(keys_table(list(app.BINDINGS)))
        text = rec.export_text()
        assert "/theme" in text and "Menu" in text and "F1" in text
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, KeysScreen)
        # /keys does the same from the prompt.
        assert app._handle_slash_command("/keys") is True
        await pilot.pause()
        assert isinstance(app.screen, KeysScreen)


async def test_slash_theme_sets_persists_and_refreshes_exports(tmp_path, monkeypatch):
    import json

    from oshell import themes

    monkeypatch.setattr(themes, "CURRENT_DIR", str(tmp_path / "current"))
    app = _app()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        assert app.theme == "tokyo-night"  # the default is Omarchy's default
        assert "osaka-jade" in app.available_themes  # bundled palettes are registered
        assert app._handle_slash_command("/theme osaka-jade") is True
        await pilot.pause()
        assert app.theme == "osaka-jade" and app.agent.config.theme == "osaka-jade"
        assert json.loads(Path("config.local.json").read_text())["theme"] == "osaka-jade"
        assert (tmp_path / "current" / "theme").read_text().strip() == "osaka-jade"
        assert "osaka-jade" in app.query_one("#statusbar").text
        # Unknown names are refused, state untouched.
        app._handle_slash_command("/theme not-a-theme")
        await pilot.pause()
        assert app.theme == "osaka-jade"


async def test_screensaver_menu_item_plays_the_mood_with_the_wordmark():
    from oshell.tui.menu import MENU_ITEMS
    from oshell.tui.overlay import MoodOverlay, _Logo

    ids = [cid for cid, *_r in MENU_ITEMS]
    assert "screensaver" in ids and "keys" in ids and "theme" in ids
    app = _app()
    async with app.run_test(size=(120, 40)) as pilot:
        app._on_menu_choice("screensaver")
        await pilot.pause()
        await pilot.pause(0.3)
        overlay = app.screen
        assert isinstance(overlay, MoodOverlay) and overlay.logo
        logo = overlay.query_one("#logo", _Logo)
        assert logo.display  # it fits at 120x40
        await pilot.press("space")
        await pilot.pause()
        assert not isinstance(app.screen, MoodOverlay)


# ── tiles: the riced-desktop layout ──────────────────────────────────────────
async def test_tiles_layout_has_titled_windows_vitals_and_fastfetch():
    from oshell.tui.vitals import VitalsPanel

    app = _app()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        assert "tiles" in app.query_one("#body").classes
        assert app.query_one("#conversation").border_title == "chat"
        vit = app.query_one("#vitals", VitalsPanel)
        assert vit.border_title == "vitals"
        assert app.query_one("Input").border_title == "❯"
        # A fresh session greets with fastfetch: the wordmark + the rig.
        text = _convo_text(app)
        assert "██████╗" in text and "@oshell" in text and "fully local" in text
        # Vitals repaint from a sample without touching the machine.
        from oshell.tui.vitals import VitalsSample

        vit.show(VitalsSample(cpu_pct=50, mem_used_gb=8, mem_total_gb=16, loaded=[]))
        assert "cpu" in vit.text and "50%" in vit.text and "nothing loaded" in vit.text


async def test_workspaces_switch_tabs_and_light_the_bar():
    from textual.widgets import TabbedContent

    app = _app()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        bar = app.query_one("#statusbar")
        assert " 1  2  3  4 " in bar.text
        app.action_workspace(2)
        await pilot.pause()
        assert app.query_one(TabbedContent).active == "tab-context"
        assert bar.state.workspace == 2
        app.action_workspace(0)
        await pilot.pause()
        assert app.query_one("Input").has_focus and bar.state.workspace == 0


async def test_classic_layout_keeps_the_old_shape():
    cfg = Config()
    cfg.ui.layout = "classic"
    app = OllamaShellTUI(
        Agent(_Scripted(), ToolRegistry([CurrentTimeTool()]), cfg), show_menu_on_start=False
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        assert not list(app.query("#vitals"))
        assert "tiles" not in app.query_one("#body").classes
        assert app.query_one("#conversation").border_title in ("", None)
        assert "Try:" in _convo_text(app)  # the small welcome card, not fastfetch


# ── presence: inbox in the bar, /inbox, jobs in the menu ─────────────────────
async def test_inbox_lights_the_bar_and_renders_in_chat(tmp_path):
    from oshell import inbox
    from oshell.tui.menu import MENU_ITEMS

    ids = [cid for cid, *_r in MENU_ITEMS]
    assert "inbox" in ids and "jobs" in ids
    cfg = Config()
    cfg.jobs.inbox_dir = str(tmp_path / "inbox")
    cfg.jobs.dir = str(tmp_path / "jobs")
    inbox.add(
        "disk-watch",
        "Disk at 91%",
        "Ollama models are the bulk.",
        [inbox.Proposal("run_command", {"command": "docker system prune -af"})],
        directory=cfg.jobs.inbox_dir,
    )
    app = OllamaShellTUI(
        Agent(_Scripted(), ToolRegistry([CurrentTimeTool()]), cfg), show_menu_on_start=False
    )
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        bar = app.query_one("#statusbar")
        assert bar.state.inbox == 1 and bar.state.pending == 1
        assert "1 to approve" in bar.text
        assert app._handle_slash_command("/inbox") is True
        await pilot.pause()
        text = _convo_text(app)
        assert "Disk at 91%" in text and "docker system prune -af" in text
        assert "oshell inbox approve" in text
        # Reading marks the note read; the pending proposal keeps it lit.
        assert inbox.unread_count(cfg.jobs.inbox_dir) == 0
        app._menu_jobs()
        await pilot.pause()
        assert "No scheduled jobs" in _convo_text(app)


# ── presence, managed in-app: orders / jobs / inbox screens ──────────────────
def _presence_app(tmp_path):
    cfg = Config()
    cfg.jobs.dir = str(tmp_path / "jobs")
    cfg.jobs.inbox_dir = str(tmp_path / "inbox")
    cfg.jobs.orders_path = str(tmp_path / "orders.md")
    cfg.jobs.orders_state = str(tmp_path / "orders.state.json")
    cfg.jobs.notify = False
    return OllamaShellTUI(
        Agent(_Scripted(), ToolRegistry([CurrentTimeTool()]), cfg), show_menu_on_start=False
    )


async def test_orders_screen_adds_edits_reprioritizes_and_deletes(tmp_path):
    from textual.widgets import Input as _Input

    from oshell import orders
    from oshell.tui.presence import OrdersScreen, PromptScreen

    app = _presence_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert app._handle_slash_command("/orders") is True
        await pilot.pause()
        scr = app.screen
        assert isinstance(scr, OrdersScreen)
        assert len(scr.items) == 3  # the template's examples, created on first open
        # a → prompt → Enter adds an order.
        await pilot.press("a")
        await pilot.pause()
        assert isinstance(app.screen, PromptScreen)
        app.screen.query_one(_Input).value = "Tell me when the release build lands"
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, OrdersScreen) and len(scr.items) == 4
        assert scr.items[3].text == "Tell me when the release build lands"
        assert scr.items[3].priority == "normal"
        # p cycles the highlighted (new) order's priority: normal → high.
        await pilot.press("p")
        await pilot.pause()
        assert scr.items[3].priority == "high"
        assert "[high] Tell me when the release build lands" in (tmp_path / "orders.md").read_text()
        # e edits the text in place.
        await pilot.press("e")
        await pilot.pause()
        app.screen.query_one(_Input).value = "Tell me when the release build lands in ~/builds"
        await pilot.press("enter")
        await pilot.pause()
        assert scr.items[3].text.endswith("~/builds") and scr.items[3].priority == "high"
        # d → confirm with y deletes it.
        await pilot.press("d")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        assert len(scr.items) == 3
        assert len(orders.load_orders(tmp_path / "orders.md")) == 3
        # i creates the orders job.
        await pilot.press("i")
        await pilot.pause()
        from oshell import schedule

        assert schedule.load_job("orders", tmp_path / "jobs") is not None
        assert isinstance(app.screen, OrdersScreen)  # reopened with the job line
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, OrdersScreen)


async def test_jobs_screen_creates_toggles_and_deletes(tmp_path):
    from textual.widgets import Input as _Input

    from oshell import schedule
    from oshell.tui.presence import JobsScreen

    app = _presence_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app._open_jobs()
        await pilot.pause()
        scr = app.screen
        assert isinstance(scr, JobsScreen) and scr.items == []
        await pilot.press("n")
        await pilot.pause()
        app.screen.query_one(_Input).value = "is the disk filling up?"
        await pilot.press("enter")
        await pilot.pause()
        app.screen.query_one(_Input).value = "every 6h"
        await pilot.press("enter")
        await pilot.pause()
        assert len(scr.items) == 1 and scr.items[0].every == "6h"
        name = scr.items[0].name
        await pilot.press("t")
        await pilot.pause()
        assert schedule.load_job(name, tmp_path / "jobs").enabled is False
        await pilot.press("t")
        await pilot.pause()
        assert schedule.load_job(name, tmp_path / "jobs").enabled is True
        await pilot.press("d")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        assert schedule.list_jobs(tmp_path / "jobs") == []


async def test_inbox_screen_shows_and_dismisses(tmp_path):
    from oshell import inbox
    from oshell.tui.presence import InboxScreen

    app = _presence_app(tmp_path)
    idir = tmp_path / "inbox"
    inbox.add(
        "disk-watch",
        "Disk at 91%",
        "Big.",
        [inbox.Proposal("run_command", {"command": "docker system prune -af"})],
        directory=idir,
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app._open_inbox()
        await pilot.pause()
        scr = app.screen
        assert isinstance(scr, InboxScreen) and len(scr.items) == 1
        # Enter shows the note in the conversation (marks read) and reopens the inbox.
        await pilot.press("enter")
        await pilot.pause()
        assert "Disk at 91%" in _convo_text(app)
        assert inbox.list_notes(directory=idir)[0].status == "read"
        assert isinstance(app.screen, InboxScreen)
        # x dismisses the note and its proposal.
        await pilot.press("x")
        await pilot.pause()
        n = inbox.list_notes(directory=idir)[0]
        assert n.status == "dismissed" and n.proposals[0].status == "dismissed"
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, InboxScreen)


def test_parse_when_shapes():
    from oshell.tui.presence import _parse_when

    assert _parse_when("every 6h") == {"every": "6h"}
    assert _parse_when("6h") == {"every": "6h"}
    assert _parse_when("cron 0 9 * * 1-5") == {"cron": "0 9 * * 1-5"}
    assert _parse_when("0 9 * * 1-5") == {"cron": "0 9 * * 1-5"}
    assert _parse_when("at 2026-09-05T09:00") == {"at": "2026-09-05T09:00"}
    assert _parse_when("2026-09-05T09:00") == {"at": "2026-09-05T09:00"}
