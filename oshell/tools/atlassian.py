"""Jira & Confluence tools (Server/DC). Network-touching; flagged in the banner.

Each tool builds its client lazily from environment credentials and converts
config/HTTP failures into soft ``ToolError`` strings so a misconfigured token
never crashes the agent loop.
"""

from __future__ import annotations

from typing import Any

import requests

from ..config import AtlassianConfig
from ..integrations.atlassian import (
    AtlassianConfigError,
    ConfluenceClient,
    JiraClient,
)
from .base import Tool, ToolError

_BODY_LIMIT = 4000


def _guard(fn):
    """Wrap a client call, mapping known failures to ToolError."""
    try:
        return fn()
    except AtlassianConfigError as exc:
        raise ToolError(f"Atlassian not configured: {exc}") from exc
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "?"
        raise ToolError(f"Atlassian API returned HTTP {code}") from exc
    except requests.RequestException as exc:
        raise ToolError(f"could not reach Atlassian: {exc}") from exc


class _AtlassianTool(Tool):
    """Base: holds the AtlassianConfig so clients resolve env-then-config."""

    def __init__(self, cfg: AtlassianConfig | None = None):
        self._cfg = cfg


class JiraSearchTool(_AtlassianTool):
    name = "jira_search"
    description = "Search Jira issues with a JQL query (Server/DC). Returns key, summary, status."
    local_only = False
    parameters = {
        "type": "object",
        "properties": {
            "jql": {
                "type": "string",
                "description": "Jira Query Language, e.g. 'project=OPS AND status=Open'",
            },
            "max_results": {"type": "integer", "description": "Max issues (default 10)"},
        },
        "required": ["jql"],
    }

    def run(self, jql: str = "", max_results: int = 10, **_: Any) -> str:
        issues = _guard(lambda: JiraClient.resolve(self._cfg).search(jql, int(max_results)))
        if not issues:
            return "(no matching issues)"
        return "\n".join(
            f"{i['key']}  [{i['status']}]  {i['summary']}  ({i['assignee'] or 'unassigned'})"
            for i in issues
        )


class JiraGetIssueTool(_AtlassianTool):
    name = "jira_get_issue"
    description = "Fetch one Jira issue by key (e.g. OPS-1234), including its description."
    local_only = False
    parameters = {
        "type": "object",
        "properties": {"key": {"type": "string", "description": "Issue key, e.g. OPS-1234"}},
        "required": ["key"],
    }

    def run(self, key: str = "", **_: Any) -> str:
        i = _guard(lambda: JiraClient.resolve(self._cfg).get_issue(key))
        desc = (i.get("description") or "")[:_BODY_LIMIT]
        return (
            f"{i['key']}  [{i['status']}]  {i['summary']}\n"
            f"assignee: {i['assignee'] or 'unassigned'}\n\n{desc}"
        )


class ConfluenceSearchTool(_AtlassianTool):
    name = "confluence_search"
    description = "Search Confluence content with a CQL query (Server/DC). Returns id, type, title."
    local_only = False
    parameters = {
        "type": "object",
        "properties": {
            "cql": {
                "type": "string",
                "description": "Confluence Query Language, e.g. 'text~\"runbook\"'",
            },
            "limit": {"type": "integer", "description": "Max results (default 10)"},
        },
        "required": ["cql"],
    }

    def run(self, cql: str = "", limit: int = 10, **_: Any) -> str:
        results = _guard(lambda: ConfluenceClient.resolve(self._cfg).search(cql, int(limit)))
        if not results:
            return "(no matching content)"
        return "\n".join(f"{r['id']}  [{r['type']}]  {r['title']}" for r in results)


class ConfluenceGetPageTool(_AtlassianTool):
    name = "confluence_get_page"
    description = (
        "Fetch a Confluence page by id, returning its title, space, and body (HTML storage)."
    )
    local_only = False
    parameters = {
        "type": "object",
        "properties": {"page_id": {"type": "string", "description": "Numeric page id"}},
        "required": ["page_id"],
    }

    def run(self, page_id: str = "", **_: Any) -> str:
        p = _guard(lambda: ConfluenceClient.resolve(self._cfg).get_page(page_id))
        body = (p.get("body") or "")[:_BODY_LIMIT]
        return f"# {p['title']}  (space {p['space']}, v{p['version']})\n\n{body}"
