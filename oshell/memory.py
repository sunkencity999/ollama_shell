"""Lightweight, always-on persistent memory — facts the assistant keeps about
the user across sessions.

Deliberately dependency-free (plain JSON, keyword recall) and distinct from the
optional RAG knowledge base: memory is small, auto-injected into the system
prompt so the model just *knows* it, whereas the knowledge base is a heavier
opt-in vector store the model must explicitly search.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

_STOPWORDS = {"the", "a", "an", "is", "to", "of", "and", "i", "my", "me", "you", "in", "on", "for"}


class MemoryStore:
    def __init__(self, path: str | Path = "~/.oshell/memory.json"):
        self.path = Path(path).expanduser()
        self._items: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return list(data.get("memories", []))
        except (json.JSONDecodeError, OSError):  # pragma: no cover - defensive
            return []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"memories": self._items}, indent=2) + "\n", encoding="utf-8"
        )

    # ── operations ─────────────────────────────────────────────────────────---
    def add(self, text: str) -> dict[str, Any]:
        """Store a memory (deduped by exact text). Returns the item."""
        text = text.strip()
        for m in self._items:
            if m["text"] == text:
                return m
        item = {
            "id": uuid.uuid4().hex[:8],
            "text": text,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        self._items.append(item)
        self._save()
        return item

    def all(self) -> list[dict[str, Any]]:
        return list(self._items)

    def recent(self, n: int) -> list[dict[str, Any]]:
        return self._items[-n:] if n > 0 else []

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Keyword-overlap recall (no embeddings)."""
        terms = {w for w in _tokens(query) if w not in _STOPWORDS}
        if not terms:
            return self.recent(limit)
        scored = []
        for m in self._items:
            words = set(_tokens(m["text"]))
            score = len(terms & words)
            if score:
                scored.append((score, m))
        scored.sort(key=lambda s: s[0], reverse=True)
        return [m for _s, m in scored[:limit]]

    def forget(self, query: str) -> int:
        """Remove memories matching ``query`` by id or substring. Returns count removed."""
        q = query.strip().lower()
        before = len(self._items)
        self._items = [
            m for m in self._items if m["id"] != query and q not in m["text"].lower()
        ]
        removed = before - len(self._items)
        if removed:
            self._save()
        return removed

    def clear(self) -> int:
        n = len(self._items)
        self._items = []
        self._save()
        return n


def _tokens(text: str) -> list[str]:
    return [w for w in "".join(c.lower() if c.isalnum() else " " for c in text).split() if w]
