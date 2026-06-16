"""Web-search tool — the canonical example of an *opt-in, network-touching* tool.

It is only functional when the ``[web]`` extra is installed. Until then it
returns an actionable message instead of raising, so the agent can explain the
gap to the user. ``local_only = False`` flags it for the privacy banner.
"""

from __future__ import annotations

from typing import Any

from .base import Tool, ToolError


class WebSearchTool(Tool):
    name = "web_search"
    description = (
        "Search the public web (DuckDuckGo) and return the top result titles, "
        "URLs, and snippets. Use for current events or facts not in the model."
    )
    local_only = False  # reaches the network — surfaced in the privacy banner
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "max_results": {"type": "integer", "description": "How many results (default 5)"},
        },
        "required": ["query"],
    }

    def run(self, query: str = "", max_results: int = 5, **_: Any) -> str:
        try:
            from duckduckgo_search import DDGS  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised via extras
            raise ToolError(
                "web search needs the optional 'web' extra: pip install 'ollama-shell[web]'"
            ) from exc

        if not query.strip():
            raise ToolError("query must not be empty")

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "(no results)"
        return "\n\n".join(
            f"{r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}" for r in results
        )
