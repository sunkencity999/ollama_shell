"""Visual-regression snapshot of the TUI layout.

Marked ``snapshot`` and excluded from CI (`-m "not snapshot"`) because SVG
baselines are pinned to a Textual version. Regenerate after intentional layout
changes with:  pytest -m snapshot --snapshot-update
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

pytest.importorskip("textual")
pytest.importorskip("pytest_textual_snapshot")

from oshell.agent import Agent  # noqa: E402
from oshell.config import Config  # noqa: E402
from oshell.providers.base import ChatChunk, LLMProvider, Message  # noqa: E402
from oshell.tools import ToolRegistry  # noqa: E402
from oshell.tools.builtins import CurrentTimeTool  # noqa: E402
from oshell.tui.app import OllamaShellTUI  # noqa: E402


class _Scripted(LLMProvider):
    name = "scripted"

    def list_models(self) -> list[str]:
        return ["scripted-model"]

    def chat(self, messages: list[Message], **kwargs: Any) -> Iterator[ChatChunk]:
        yield ChatChunk(content="hello", done=True)


def _deterministic_app() -> OllamaShellTUI:
    # Fixed config (no Atlassian creds), scripted provider, clock off → stable render.
    cfg = Config(default_model="demo-model")
    agent = Agent(_Scripted(), ToolRegistry([CurrentTimeTool()]), cfg)
    return OllamaShellTUI(agent, show_clock=False, show_menu_on_start=False)


@pytest.mark.snapshot
def test_tui_layout_snapshot(snap_compare):
    assert snap_compare(_deterministic_app(), terminal_size=(100, 32))
