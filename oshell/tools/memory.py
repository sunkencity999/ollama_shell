"""Memory tools: remember / recall / forget durable facts about the user.

Stored memories are auto-injected into the system prompt, so the model usually
doesn't need to call ``recall`` for things it already knows — but ``recall`` lets
it search the full set when memory grows beyond what's injected.
"""

from __future__ import annotations

from typing import Any

from ..memory import MemoryStore
from .base import Tool, ToolError


class RememberTool(Tool):
    name = "remember"
    description = (
        "Save a durable fact or preference about the user to long-term memory so "
        "you'll know it in future sessions (e.g. their name, tools they use, how "
        "they like answers). Don't store secrets/passwords or transient details."
    )
    local_only = True
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The fact to remember, one concise sentence"}
        },
        "required": ["text"],
    }

    def __init__(self, store: MemoryStore):
        self._store = store

    def run(self, text: str = "", **_: Any) -> str:
        if not text.strip():
            raise ToolError("nothing to remember")
        self._store.add(text)
        return f"remembered: {text.strip()}"


class RecallTool(Tool):
    name = "recall"
    description = "Search your long-term memory for facts about the user matching a query."
    local_only = True
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to look for"},
            "limit": {"type": "integer", "description": "Max memories to return (default 5)"},
        },
        "required": ["query"],
    }

    def __init__(self, store: MemoryStore):
        self._store = store

    def run(self, query: str = "", limit: int = 5, **_: Any) -> str:
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 5
        hits = self._store.search(query, limit)
        if not hits:
            return "(no matching memories)"
        return "\n".join(f"- {m['text']}" for m in hits)


class ForgetTool(Tool):
    name = "forget"
    description = "Remove memories matching the given text from long-term memory."
    local_only = True
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text/id to remove, or 'all' to clear"}
        },
        "required": ["text"],
    }

    def __init__(self, store: MemoryStore):
        self._store = store

    def run(self, text: str = "", **_: Any) -> str:
        if not text.strip():
            raise ToolError("specify what to forget")
        if text.strip().lower() in ("all", "everything"):
            n = self._store.clear()
        else:
            n = self._store.forget(text)
        return f"forgot {n} memor{'y' if n == 1 else 'ies'}"


def memory_tools(store: MemoryStore) -> list[Tool]:
    return [RememberTool(store), RecallTool(store), ForgetTool(store)]
