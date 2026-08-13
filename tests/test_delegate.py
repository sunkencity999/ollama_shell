"""The delegate tool: side quests in a clean context, only the answer comes back."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import oshell.tools as tools_pkg
from oshell.config import Config
from oshell.providers.base import ChatChunk, LLMProvider, Message
from oshell.tools import ToolRegistry
from oshell.tools.builtins import CurrentTimeTool
from oshell.tools.delegate import DelegateTool


class _Helper(LLMProvider):
    name = "helper"

    def __init__(self):
        self.models_used: list[str] = []
        self.prompts: list[str] = []

    def list_models(self):
        return ["m", "fast:4b"]

    def chat(self, messages: list[Message], *, model="", **kw: Any) -> Iterator[ChatChunk]:
        self.models_used.append(model)
        self.prompts.append(messages[-1].content)
        yield ChatChunk(content="the capital is Sacramento", done=True)


def _tool(monkeypatch, config) -> tuple[DelegateTool, _Helper, dict]:
    provider = _Helper()
    seen: dict = {}

    def fake_registry(prov, cfg, workspace=".", model=None, memory=None, delegate=True):
        seen["delegate"] = delegate
        seen["model"] = model
        return ToolRegistry([CurrentTimeTool()])

    monkeypatch.setattr(tools_pkg, "default_registry", fake_registry)
    return DelegateTool(provider, config), provider, seen


def test_delegate_returns_final_answer(monkeypatch):
    tool, provider, seen = _tool(monkeypatch, Config(default_model="m"))
    out = tool.run(task="what is the capital of California?")
    assert out == "the capital is Sacramento"
    assert "capital of California" in provider.prompts[0]
    assert seen["delegate"] is False  # helpers don't get helpers


def test_delegate_prefers_fast_model(monkeypatch):
    cfg = Config(default_model="m")
    cfg.routing.fast_model = "fast:4b"
    tool, provider, seen = _tool(monkeypatch, cfg)
    tool.run(task="quick errand")
    assert provider.models_used[-1] == "fast:4b"
    assert seen["model"] == "fast:4b"


def test_delegate_rejects_empty_task(monkeypatch):
    tool, provider, _ = _tool(monkeypatch, Config(default_model="m"))
    assert "[error]" in tool.run(task="   ")
    assert provider.models_used == []  # never spun up a helper


def test_default_registry_includes_delegate_once():
    """Top-level registries carry delegate; the flag removes it for helpers."""
    from oshell.tools import default_registry

    class _P(LLMProvider):
        name = "p"

        def list_models(self):
            return []

        def chat(self, messages, **kw):
            yield ChatChunk(content="", done=True)

    cfg = Config()
    cfg.mcp_servers = {}  # keep the test hermetic — no server spawns
    names = {t.name for t in default_registry(_P(), cfg).active()}
    assert "delegate" in names
    helper_names = {t.name for t in default_registry(_P(), cfg, delegate=False).active()}
    assert "delegate" not in helper_names
