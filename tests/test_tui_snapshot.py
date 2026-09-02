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
    cfg.ui.vitals = False  # the vitals tile samples the live machine
    agent = Agent(_Scripted(), ToolRegistry([CurrentTimeTool()]), cfg)
    return OllamaShellTUI(agent, show_clock=False, show_menu_on_start=False)


def _pin_machine_facts(monkeypatch) -> None:
    """The fastfetch card reads the host; freeze every fact it shows."""
    import os
    import platform

    monkeypatch.setenv("USER", "you")
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setattr(platform, "node", lambda: "studio")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    monkeypatch.setattr(os, "cpu_count", lambda: 16)
    monkeypatch.setattr("oshell.roles.host_os", lambda: "macOS 15.1 (arm64)")
    monkeypatch.setattr("oshell.fetch._uptime", lambda: "3h 24m")
    monkeypatch.setattr("oshell.tools.system._total_ram_gb", lambda: 128.0)


@pytest.mark.snapshot
def test_tui_layout_snapshot(snap_compare, monkeypatch):
    # Pin the optional-feature list so the snapshot is about LAYOUT, not about
    # which extras happen to be pip-installed in this environment.
    from oshell.capabilities import Capability

    fixed = [
        Capability("rag (knowledge base)", False, "[rag]"),
        Capability("docs (docx/xlsx/pdf)", False, "[docs]"),
        Capability("gui (computer-use)", False, "[gui]"),
        Capability("jira (Server)", False, "set JIRA_URL + JIRA_TOKEN"),
    ]
    monkeypatch.setattr("oshell.tui.app.optional_features", lambda *_a, **_k: fixed)
    _pin_machine_facts(monkeypatch)
    assert snap_compare(_deterministic_app(), terminal_size=(100, 32))
