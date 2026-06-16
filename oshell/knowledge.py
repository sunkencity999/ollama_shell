"""Local vector knowledge base — clean successor to the monolith's ``KnowledgeBase``.

A thin, lazy wrapper over ChromaDB (persistent) + a sentence-transformers
embedding model. Everything stays on disk under the configured path; nothing
leaves the machine. Requires the ``[rag]`` extra.

The heavy bits (loading the embedding model, opening the DB) are deferred until
first use, so importing this module and constructing a ``KnowledgeBase`` are
cheap — important because the agent registers knowledge tools eagerly.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import KnowledgeConfig


class KnowledgeUnavailable(RuntimeError):
    """Raised when the ``[rag]`` dependencies are not installed."""


@dataclass
class SearchHit:
    text: str
    metadata: dict[str, Any]
    distance: float


class KnowledgeBase:
    """Persistent semantic store: add documents, search them by meaning."""

    def __init__(self, config: KnowledgeConfig | None = None):
        self.config = config or KnowledgeConfig()
        self._client = None
        self._collection = None
        self._embedder = None

    # ── lazy resource acquisition ────────────────────────────────────────────
    def _ensure(self) -> None:
        if self._collection is not None:
            return
        try:
            import chromadb  # type: ignore
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised via extras
            raise KnowledgeUnavailable(
                "knowledge base needs the 'rag' extra: pip install 'ollama-shell[rag]'"
            ) from exc

        path = Path(self.config.path).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        # Local-first: disable ChromaDB's default posthog telemetry so the
        # knowledge base never phones home. (Replaces the legacy posthog_disable
        # shim the old monolith needed.)
        settings = chromadb.config.Settings(anonymized_telemetry=False)
        self._client = chromadb.PersistentClient(path=str(path), settings=settings)
        self._collection = self._client.get_or_create_collection(self.config.collection)
        self._embedder = SentenceTransformer(self.config.model)

    def _embed(self, text: str) -> list[float]:
        self._ensure()
        return self._embedder.encode(text).tolist()  # type: ignore[union-attr]

    # ── operations ───────────────────────────────────────────────────────────
    def add(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        """Embed and store a document; returns its content-derived id."""
        self._ensure()
        doc_id = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
        self._collection.add(  # type: ignore[union-attr]
            ids=[doc_id],
            embeddings=[self._embed(text)],
            documents=[text],
            metadatas=[metadata or {"source": "manual"}],
        )
        return doc_id

    def search(self, query: str, limit: int | None = None) -> list[SearchHit]:
        """Return the ``limit`` most semantically similar stored documents."""
        self._ensure()
        n = limit or self.config.default_limit
        if self._collection.count() == 0:  # type: ignore[union-attr]
            return []
        res = self._collection.query(  # type: ignore[union-attr]
            query_embeddings=[self._embed(query)],
            n_results=min(n, self._collection.count()),  # type: ignore[union-attr]
        )
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        return [
            SearchHit(text=d, metadata=m or {}, distance=float(dist))
            for d, m, dist in zip(docs, metas, dists, strict=True)
        ]

    def count(self) -> int:
        self._ensure()
        return self._collection.count()  # type: ignore[union-attr]

    def reset(self) -> None:
        """Drop and recreate the collection (clears all documents)."""
        self._ensure()
        self._client.delete_collection(self.config.collection)  # type: ignore[union-attr]
        self._collection = self._client.get_or_create_collection(  # type: ignore[union-attr]
            self.config.collection
        )
