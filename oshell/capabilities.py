"""Report which optional capabilities are actually available in this install.

The base package is tiny; power features live behind extras (``web``, ``rag``,
``docs``, ``tui``, ``finetune``) and integrations need credentials. This module
introspects the environment so the CLI and TUI can show an honest picture of
what the running install can and can't do — rather than advertising tools that
will only error when called.
"""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass


@dataclass
class Capability:
    name: str
    available: bool
    detail: str  # how to enable it, or why it's on


def _have(*modules: str) -> bool:
    return all(importlib.util.find_spec(m) is not None for m in modules)


def optional_features() -> list[Capability]:
    """One entry per optional feature, with availability + a hint."""
    feats = [
        ("web (search/fetch)", _have("duckduckgo_search", "bs4"), "[web]"),
        ("rag (knowledge base)", _have("chromadb", "sentence_transformers"), "[rag]"),
        ("docs (docx/xlsx/pdf)", _have("docx", "openpyxl"), "[docs]"),
        ("tui", _have("textual"), "[tui]"),
        ("finetune (mlx)", _have("mlx_lm"), "[finetune]"),
    ]
    out = [
        Capability(n, ok, "enabled" if ok else f"pip install 'ollama-shell{extra}'")
        for n, ok, extra in feats
    ]

    jira = bool(os.environ.get("JIRA_URL"))
    conf = bool(os.environ.get("CONFLUENCE_URL"))
    out.append(
        Capability("jira (Server)", jira, "configured" if jira else "set JIRA_URL + JIRA_TOKEN")
    )
    out.append(
        Capability(
            "confluence (Server)",
            conf,
            "configured" if conf else "set CONFLUENCE_URL + CONFLUENCE_TOKEN",
        )
    )
    return out
