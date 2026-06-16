"""Knowledge-base tools: remember facts locally and recall them by meaning.

Both tools share one lazily-constructed ``KnowledgeBase`` so the embedding
model loads at most once per session, and only if a tool is actually called.
They are ``local_only`` — the store never leaves the machine.
"""

from __future__ import annotations

from typing import Any

from ..config import Config
from ..knowledge import KnowledgeBase, KnowledgeUnavailable
from .base import Tool, ToolError


class _SharedKB:
    """Holds one KnowledgeBase, created on first access."""

    def __init__(self, config: Config):
        self._config = config
        self._kb: KnowledgeBase | None = None

    def get(self) -> KnowledgeBase:
        if self._kb is None:
            self._kb = KnowledgeBase(self._config.knowledge)
        return self._kb


class AddKnowledgeTool(Tool):
    name = "add_knowledge"
    description = (
        "Store a piece of text in the local knowledge base for later semantic "
        "recall. Use to remember facts, notes, or snippets across the session."
    )
    local_only = True
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The text to remember"},
            "source": {"type": "string", "description": "Optional label for where it came from"},
        },
        "required": ["text"],
    }

    def __init__(self, shared: _SharedKB):
        self._shared = shared

    def run(self, text: str = "", source: str = "manual", **_: Any) -> str:
        if not text.strip():
            raise ToolError("text must not be empty")
        try:
            doc_id = self._shared.get().add(text, {"source": source})
        except KnowledgeUnavailable as exc:
            raise ToolError(str(exc)) from exc
        return f"stored (id={doc_id})"


class SearchKnowledgeTool(Tool):
    name = "search_knowledge"
    description = (
        "Search the local knowledge base for documents semantically similar to a "
        "query. Returns the closest stored snippets. Use before answering from memory."
    )
    local_only = True
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to look for"},
            "limit": {"type": "integer", "description": "Max hits to return (default from config)"},
        },
        "required": ["query"],
    }

    def __init__(self, shared: _SharedKB):
        self._shared = shared

    def run(self, query: str = "", limit: int | None = None, **_: Any) -> str:
        if not query.strip():
            raise ToolError("query must not be empty")
        if limit is not None:
            try:
                limit = int(limit)
            except (TypeError, ValueError):
                limit = None
        try:
            hits = self._shared.get().search(query, limit)
        except KnowledgeUnavailable as exc:
            raise ToolError(str(exc)) from exc
        if not hits:
            return "(knowledge base is empty or no matches)"
        return "\n\n".join(
            f"[{h.metadata.get('source', '?')}  dist={h.distance:.3f}]\n{h.text}" for h in hits
        )
