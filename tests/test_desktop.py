"""Tests for desktop notification / terminal re-focus helpers (mocked subprocess)."""

from __future__ import annotations

import oshell.desktop as d


def test_notify_macos_uses_osascript(monkeypatch):
    calls = []
    monkeypatch.setattr(d.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(d.subprocess, "run", lambda *a, **k: calls.append(a[0]))
    assert d.notify("Title", "Body") is True
    assert calls[0][0] == "osascript"
    assert any("display notification" in part for part in calls[0])


def test_notify_never_raises(monkeypatch):
    def _boom(*a, **k):
        raise OSError("no such tool")

    monkeypatch.setattr(d.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(d.subprocess, "run", _boom)
    assert d.notify("t", "m") is False  # swallowed


def test_focus_terminal_macos_maps_term_program(monkeypatch):
    calls = []
    monkeypatch.setattr(d.platform, "system", lambda: "Darwin")
    monkeypatch.setenv("TERM_PROGRAM", "iTerm.app")
    monkeypatch.setattr(d.subprocess, "run", lambda *a, **k: calls.append(a[0]))
    assert d.focus_terminal() is True
    assert any('tell application "iTerm" to activate' in part for part in calls[0])


def test_focus_terminal_unknown_term_is_noop(monkeypatch):
    monkeypatch.setattr(d.platform, "system", lambda: "Darwin")
    monkeypatch.delenv("TERM_PROGRAM", raising=False)
    assert d.focus_terminal() is False
