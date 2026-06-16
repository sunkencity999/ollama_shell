"""Atlassian (Server/DC) client + tool tests. HTTP is fully mocked."""

from __future__ import annotations

import base64

import pytest
import requests

from oshell.integrations.atlassian import (
    AtlassianConfigError,
    ConfluenceClient,
    JiraClient,
    _auth_header,
    _Endpoint,
)
from oshell.providers.base import ToolCall
from oshell.tools import ToolRegistry
from oshell.tools.atlassian import JiraGetIssueTool, JiraSearchTool


class _FakeResp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self._payload


def _patch_get(monkeypatch, resp):
    """Stub the single requests.get used by the Atlassian endpoint."""
    monkeypatch.setattr(
        "oshell.integrations.atlassian.requests.get", lambda *a, **k: resp
    )


def test_auth_header_pat_is_bearer():
    h = _auth_header("pat", None, "tok123")
    assert h["Authorization"] == "Bearer tok123"


def test_auth_header_basic_is_base64():
    h = _auth_header("basic", "me@x.com", "tok")
    assert h["Authorization"].startswith("Basic ")
    decoded = base64.b64decode(h["Authorization"].split(" ", 1)[1]).decode()
    assert decoded == "me@x.com:tok"


def test_endpoint_requires_url_and_token():
    with pytest.raises(AtlassianConfigError):
        _Endpoint(base_url="", token="x")
    with pytest.raises(AtlassianConfigError):
        _Endpoint(base_url="https://j", token="")


def test_jira_search_parsing(monkeypatch):
    payload = {
        "issues": [
            {
                "key": "OPS-1",
                "fields": {
                    "summary": "Fix the thing",
                    "status": {"name": "Open"},
                    "assignee": {"displayName": "Ada"},
                },
            }
        ]
    }
    _patch_get(monkeypatch, _FakeResp(payload))
    client = JiraClient(_Endpoint(base_url="https://jira.local", token="t"))
    rows = client.search("project=OPS", 5)
    assert rows[0] == {
        "key": "OPS-1",
        "summary": "Fix the thing",
        "status": "Open",
        "assignee": "Ada",
    }


def test_confluence_search_parsing(monkeypatch):
    payload = {"results": [{"id": "123", "type": "page", "title": "Runbook"}]}
    _patch_get(monkeypatch, _FakeResp(payload))
    client = ConfluenceClient(_Endpoint(base_url="https://wiki.local", token="t"))
    rows = client.search('text~"runbook"', 10)
    assert rows[0]["title"] == "Runbook"


def test_from_env_accepts_token_alias(monkeypatch):
    # joby-datasets uses *_TOKEN; legacy used *_API_KEY. Both must work.
    monkeypatch.delenv("JIRA_API_KEY", raising=False)
    monkeypatch.setenv("JIRA_URL", "https://jira.local")
    monkeypatch.setenv("JIRA_TOKEN", "alias-tok")
    captured = {}
    _patch_get(monkeypatch, _FakeResp({"issues": []}))

    def _capture(url, headers=None, params=None, timeout=None):
        captured["auth"] = headers["Authorization"]
        return _FakeResp({"issues": []})

    monkeypatch.setattr("oshell.integrations.atlassian.requests.get", _capture)
    JiraClient.from_env().search("ORDER BY created DESC", 1)
    assert captured["auth"] == "Bearer alias-tok"


def test_jira_tool_soft_errors_when_unconfigured(monkeypatch):
    monkeypatch.delenv("JIRA_URL", raising=False)
    monkeypatch.delenv("JIRA_API_KEY", raising=False)
    reg = ToolRegistry([JiraSearchTool()])
    out = reg.dispatch(ToolCall(name="jira_search", arguments={"jql": "project=OPS"}))
    assert out.startswith("[error]") and "not configured" in out


def test_jira_tool_http_error_is_soft(monkeypatch):
    monkeypatch.setenv("JIRA_URL", "https://jira.local")
    monkeypatch.setenv("JIRA_API_KEY", "tok")
    _patch_get(monkeypatch, _FakeResp({}, status=403))
    reg = ToolRegistry([JiraGetIssueTool()])
    out = reg.dispatch(ToolCall(name="jira_get_issue", arguments={"key": "OPS-1"}))
    assert out.startswith("[error]") and "403" in out


def test_jira_search_tool_formats_rows(monkeypatch):
    monkeypatch.setenv("JIRA_URL", "https://jira.local")
    monkeypatch.setenv("JIRA_API_KEY", "tok")
    payload = {
        "issues": [
            {
                "key": "OPS-9",
                "fields": {"summary": "Deploy", "status": {"name": "Done"}, "assignee": None},
            }
        ]
    }
    _patch_get(monkeypatch, _FakeResp(payload))
    reg = ToolRegistry([JiraSearchTool()])
    out = reg.dispatch(ToolCall(name="jira_search", arguments={"jql": "project=OPS"}))
    assert "OPS-9" in out and "Done" in out and "unassigned" in out
