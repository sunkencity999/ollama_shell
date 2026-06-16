"""Knowledge-base tool tests.

Validation + graceful-unavailable run without heavy deps. The real add/search
round-trip auto-skips when chromadb / sentence-transformers aren't installed
(e.g. in CI, which installs only the dev extra).
"""

from __future__ import annotations

import pytest

from oshell.config import Config, KnowledgeConfig
from oshell.knowledge import KnowledgeUnavailable
from oshell.providers.base import ToolCall
from oshell.tools import ToolRegistry
from oshell.tools.knowledge import AddKnowledgeTool, SearchKnowledgeTool


class _FakeShared:
    """Pretends the rag extra is missing."""

    def get(self):
        raise KnowledgeUnavailable("knowledge base needs the 'rag' extra")


def test_empty_inputs_rejected():
    reg = ToolRegistry([AddKnowledgeTool(_FakeShared()), SearchKnowledgeTool(_FakeShared())])
    assert reg.dispatch(ToolCall(name="add_knowledge", arguments={"text": "  "})).startswith(
        "[error]"
    )
    assert reg.dispatch(ToolCall(name="search_knowledge", arguments={"query": ""})).startswith(
        "[error]"
    )


def test_unavailable_is_soft_error():
    reg = ToolRegistry([SearchKnowledgeTool(_FakeShared())])
    out = reg.dispatch(ToolCall(name="search_knowledge", arguments={"query": "anything"}))
    assert out.startswith("[error]") and "rag" in out


# ── real round-trip (skips without rag deps) ────────────────────────────────
pytest.importorskip("chromadb")
pytest.importorskip("sentence_transformers")


def test_add_then_search_roundtrip(tmp_path):
    from oshell.tools.knowledge import _SharedKB

    cfg = Config(knowledge=KnowledgeConfig(path=str(tmp_path / "kb")))
    shared = _SharedKB(cfg)
    reg = ToolRegistry([AddKnowledgeTool(shared), SearchKnowledgeTool(shared)])

    reg.dispatch(
        ToolCall(
            name="add_knowledge",
            arguments={"text": "The Joby S4 is an eVTOL aircraft.", "source": "notes"},
        )
    )
    reg.dispatch(
        ToolCall(
            name="add_knowledge",
            arguments={"text": "Sourdough bread needs a starter.", "source": "notes"},
        )
    )
    out = reg.dispatch(
        ToolCall(name="search_knowledge", arguments={"query": "electric flying taxi", "limit": 1})
    )
    # Semantic search should surface the aircraft note, not the bread note.
    assert "eVTOL" in out
    assert "Sourdough" not in out


def test_empty_kb_search(tmp_path):
    from oshell.tools.knowledge import _SharedKB

    cfg = Config(knowledge=KnowledgeConfig(path=str(tmp_path / "kb2")))
    reg = ToolRegistry([SearchKnowledgeTool(_SharedKB(cfg))])
    out = reg.dispatch(ToolCall(name="search_knowledge", arguments={"query": "anything"}))
    assert "empty" in out
