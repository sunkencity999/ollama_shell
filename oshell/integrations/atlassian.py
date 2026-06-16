"""Clean Atlassian **Server / Data Center** clients for Jira and Confluence.

Targets the Server REST APIs (``/rest/api/2`` for Jira, ``/rest/api`` for
Confluence) — *not* Cloud (no ``/wiki`` prefix, no ``/rest/api/3``). This is a
focused successor to the legacy ``jira_mcp_integration.py`` /
``confluence_mcp_integration.py`` (150 KB combined of NL parsing + MCP
scaffolding); here we keep just the API surface the agent tools need.

Credentials are read from the same environment variables the legacy code used,
so an existing setup keeps working:

    Jira:        JIRA_URL, JIRA_API_KEY, JIRA_USER_EMAIL
    Confluence:  CONFLUENCE_URL, CONFLUENCE_API_TOKEN, CONFLUENCE_EMAIL,
                 CONFLUENCE_AUTH_METHOD  (pat | bearer | basic; default pat)

On Server, a Personal Access Token is sent as ``Authorization: Bearer <token>``
(``pat`` and ``bearer`` are equivalent); ``basic`` sends base64(user:token).
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any

import requests


class AtlassianConfigError(RuntimeError):
    """Missing/invalid Atlassian configuration (e.g. no URL or token)."""


def _auth_header(method: str, user: str | None, token: str) -> dict[str, str]:
    method = (method or "pat").lower()
    if method == "basic":
        raw = f"{user or ''}:{token}".encode()
        return {"Authorization": "Basic " + base64.b64encode(raw).decode()}
    # pat == bearer on Server/DC
    return {"Authorization": f"Bearer {token}"}


@dataclass
class _Endpoint:
    """Shared HTTP plumbing for a Server REST base + auth."""

    base_url: str
    token: str
    user: str | None = None
    auth_method: str = "pat"
    timeout: float = 30.0

    def __post_init__(self) -> None:
        if not self.base_url or not self.token:
            raise AtlassianConfigError("missing base URL or token")
        self.base_url = self.base_url.rstrip("/")

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            **_auth_header(self.auth_method, self.user, self.token),
        }
        resp = requests.get(
            f"{self.base_url}{path}", headers=headers, params=params, timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()


# ── Jira ─────────────────────────────────────────────────────────────────────
class JiraClient:
    def __init__(self, endpoint: _Endpoint):
        self._ep = endpoint

    @classmethod
    def from_env(cls) -> JiraClient:
        return cls(
            _Endpoint(
                base_url=os.environ.get("JIRA_URL", ""),
                token=os.environ.get("JIRA_API_KEY", ""),
                user=os.environ.get("JIRA_USER_EMAIL"),
                auth_method=os.environ.get("JIRA_AUTH_METHOD", "pat"),
            )
        )

    def search(self, jql: str, max_results: int = 10) -> list[dict[str, Any]]:
        data = self._ep.get(
            "/rest/api/2/search",
            {"jql": jql, "maxResults": max_results, "fields": "summary,status,assignee"},
        )
        out = []
        for issue in data.get("issues", []):
            f = issue.get("fields", {})
            out.append(
                {
                    "key": issue.get("key"),
                    "summary": f.get("summary"),
                    "status": (f.get("status") or {}).get("name"),
                    "assignee": (f.get("assignee") or {}).get("displayName"),
                }
            )
        return out

    def get_issue(self, key: str) -> dict[str, Any]:
        issue = self._ep.get(f"/rest/api/2/issue/{key}")
        f = issue.get("fields", {})
        return {
            "key": issue.get("key"),
            "summary": f.get("summary"),
            "status": (f.get("status") or {}).get("name"),
            "assignee": (f.get("assignee") or {}).get("displayName"),
            "description": f.get("description"),
        }


# ── Confluence ─────────────────────────────────────────────────────────────--
class ConfluenceClient:
    def __init__(self, endpoint: _Endpoint):
        self._ep = endpoint

    @classmethod
    def from_env(cls) -> ConfluenceClient:
        return cls(
            _Endpoint(
                base_url=os.environ.get("CONFLUENCE_URL", ""),
                token=os.environ.get("CONFLUENCE_API_TOKEN", ""),
                user=os.environ.get("CONFLUENCE_EMAIL"),
                auth_method=os.environ.get("CONFLUENCE_AUTH_METHOD", "pat"),
            )
        )

    def search(self, cql: str, limit: int = 10) -> list[dict[str, Any]]:
        data = self._ep.get("/rest/api/content/search", {"cql": cql, "limit": limit})
        return [
            {"id": r.get("id"), "type": r.get("type"), "title": r.get("title")}
            for r in data.get("results", [])
        ]

    def get_page(self, page_id: str) -> dict[str, Any]:
        data = self._ep.get(
            f"/rest/api/content/{page_id}", {"expand": "body.storage,space,version"}
        )
        body = ((data.get("body") or {}).get("storage") or {}).get("value", "")
        return {
            "id": data.get("id"),
            "title": data.get("title"),
            "space": (data.get("space") or {}).get("key"),
            "version": (data.get("version") or {}).get("number"),
            "body": body,
        }
