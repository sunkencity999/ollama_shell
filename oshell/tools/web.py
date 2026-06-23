"""Web tools — the canonical *opt-in, network-touching* capabilities.

Two composable tools let the agent do real research:

* ``web_search``  — find candidate pages (DuckDuckGo).
* ``fetch_url``   — fetch one page and return its readable text.

Both need the ``[web]`` extra; until it's installed they return an actionable
message instead of crashing, so the agent can explain the gap. Both set
``local_only = False`` so they show up in the privacy banner.

``fetch_url`` distills the genuinely useful core of the legacy
``WebBrowser.extract_structured_content_sync`` (4k-line ``web_browsing.py``) —
title + main readable text via requests + BeautifulSoup — without dragging in
that module's ollama-client and MCP-server dependencies. This is how legacy
capability migrates into the clean core so the monolith can eventually retire.
"""

from __future__ import annotations

from typing import Any

import requests

from .base import Tool, ToolError

# A browser-ish UA; some sites 403 the default python-requests agent.
_UA = "Mozilla/5.0 (compatible; OllamaShell/0.2; +local-first-agent)"
_DEFAULT_MAX_CHARS = 6000
# Tags whose text is noise for an LLM reader.
_STRIP_TAGS = ("script", "style", "noscript", "header", "footer", "nav", "aside", "form")


class WebSearchTool(Tool):
    name = "web_search"
    description = (
        "Search the public web (DuckDuckGo) and return the top result titles, "
        "URLs, and snippets. Use for current events or facts not in the model. "
        "Follow up with fetch_url to read a result in full."
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
            # `duckduckgo_search` was renamed to `ddgs`; prefer the new package
            # and fall back to the old one for existing installs.
            try:
                from ddgs import DDGS  # type: ignore
            except ImportError:
                from duckduckgo_search import DDGS  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised via extras
            raise ToolError(
                "web search needs the optional 'web' extra: pip install 'ollama-shell[web]'"
            ) from exc

        if not query.strip():
            raise ToolError("query must not be empty")

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=int(max_results)))
        except Exception as exc:  # network hiccup, rate limit, backend change
            raise ToolError(f"web search failed: {exc}") from exc
        if not results:
            return "(no results)"
        return "\n\n".join(
            f"{r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}" for r in results
        )


class FetchUrlTool(Tool):
    name = "fetch_url"
    description = (
        "Fetch a single web page and return its title and main readable text "
        "(scripts, nav, and styling stripped). Use after web_search to read a page."
    )
    local_only = False
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The absolute http(s) URL to fetch"},
            "max_chars": {
                "type": "integer",
                "description": (
                    f"Truncate readable text to this many chars (default {_DEFAULT_MAX_CHARS})"
                ),
            },
        },
        "required": ["url"],
    }

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def run(self, url: str = "", max_chars: int = _DEFAULT_MAX_CHARS, **_: Any) -> str:
        # Models often send numeric args as strings ("6000"); coerce defensively.
        try:
            max_chars = int(max_chars)
        except (TypeError, ValueError):
            max_chars = _DEFAULT_MAX_CHARS
        if not url.startswith(("http://", "https://")):
            raise ToolError("url must be an absolute http(s) URL")
        try:
            from bs4 import BeautifulSoup  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised via extras
            raise ToolError(
                "fetch_url needs the optional 'web' extra: pip install 'ollama-shell[web]'"
            ) from exc

        try:
            resp = requests.get(url, headers={"User-Agent": _UA}, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ToolError(f"could not fetch {url}: {exc}") from exc

        return extract_readable(resp.text, url, max_chars, BeautifulSoup)


def extract_readable(html: str, url: str, max_chars: int, soup_cls: Any) -> str:
    """Pull a title + de-noised text body out of an HTML string.

    Kept as a module-level function (BeautifulSoup injected) so it can be unit
    tested without any network access.
    """
    soup = soup_cls(html, "html.parser")
    for tag in soup(_STRIP_TAGS):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""
    # Collapse whitespace; drop empty lines.
    text = "\n".join(line for line in soup.get_text("\n").splitlines() if line.strip())
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n…[truncated]"

    header = f"# {title}\n{url}\n\n" if title else f"{url}\n\n"
    return header + (text or "(no readable text found)")
