"""Tests for the web tools. Network is mocked / not touched."""

from __future__ import annotations

import pytest

from oshell.providers.base import ToolCall
from oshell.tools import ToolRegistry
from oshell.tools.web import FetchUrlTool, extract_readable

bs4 = pytest.importorskip("bs4")
BeautifulSoup = bs4.BeautifulSoup

SAMPLE_HTML = """
<html><head><title>  Hello Page  </title>
<style>.x{color:red}</style></head>
<body>
  <nav>menu menu menu</nav>
  <script>console.log('noise')</script>
  <h1>Main Heading</h1>
  <p>First paragraph of real content.</p>
  <p>Second paragraph.</p>
  <footer>copyright junk</footer>
</body></html>
"""


def test_extract_readable_strips_noise_and_keeps_text():
    out = extract_readable(SAMPLE_HTML, "http://example.com", 6000, BeautifulSoup)
    assert "Hello Page" in out          # title captured
    assert "http://example.com" in out  # url header
    assert "Main Heading" in out
    assert "First paragraph of real content." in out
    # noise removed
    assert "console.log" not in out
    assert "color:red" not in out
    assert "copyright junk" not in out
    assert "menu menu menu" not in out


def test_extract_readable_truncates():
    out = extract_readable(SAMPLE_HTML, "http://example.com", 20, BeautifulSoup)
    assert "[truncated]" in out


def test_fetch_url_rejects_non_http():
    reg = ToolRegistry([FetchUrlTool()])
    out = reg.dispatch(ToolCall(name="fetch_url", arguments={"url": "ftp://nope"}))
    assert out.startswith("[error]")
    assert "absolute http" in out


def test_fetch_url_mocked(monkeypatch):
    class _Resp:
        text = SAMPLE_HTML

        def raise_for_status(self):
            pass

    monkeypatch.setattr("oshell.tools.web.requests.get", lambda *a, **k: _Resp())
    reg = ToolRegistry([FetchUrlTool()])
    out = reg.dispatch(ToolCall(name="fetch_url", arguments={"url": "https://example.com"}))
    assert "Main Heading" in out
    assert "First paragraph" in out


def test_fetch_url_coerces_stringified_max_chars(monkeypatch):
    # Models often pass integer args as strings; the tool must not crash.
    class _Resp:
        text = SAMPLE_HTML

        def raise_for_status(self):
            pass

    monkeypatch.setattr("oshell.tools.web.requests.get", lambda *a, **k: _Resp())
    reg = ToolRegistry([FetchUrlTool()])
    out = reg.dispatch(
        ToolCall(name="fetch_url", arguments={"url": "https://example.com", "max_chars": "20"})
    )
    assert not out.startswith("[error]")
    assert "[truncated]" in out


def test_fetch_url_network_error_is_soft(monkeypatch):
    import requests

    def _boom(*a, **k):
        raise requests.RequestException("dns fail")

    monkeypatch.setattr("oshell.tools.web.requests.get", _boom)
    reg = ToolRegistry([FetchUrlTool()])
    out = reg.dispatch(ToolCall(name="fetch_url", arguments={"url": "https://example.com"}))
    assert out.startswith("[error]") and "could not fetch" in out
