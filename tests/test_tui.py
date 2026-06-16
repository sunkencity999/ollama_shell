"""TUI tests using Textual's pilot. Skips cleanly if textual isn't installed."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

pytest.importorskip("textual")

from oshell.agent import Agent  # noqa: E402
from oshell.config import Config  # noqa: E402
from oshell.providers.base import ChatChunk, LLMProvider, Message  # noqa: E402
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
    return OllamaShellTUI(Agent(_Scripted(), reg, cfg))


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


async def test_context_inspector_renders():
    app = _app()
    async with app.run_test():
        text = app.query_one(ContextInspector).text
        assert "Context" in text and "syst" in text  # system message row
