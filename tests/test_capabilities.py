"""Tests for the optional-capability reporter."""

from __future__ import annotations

from oshell.capabilities import optional_features


def test_lists_expected_features():
    names = {c.name for c in optional_features()}
    assert any("rag" in n for n in names)
    assert any("finetune" in n for n in names)
    assert any("jira" in n for n in names)
    # web is a core dependency now, not an optional feature.
    assert not any("web" in n for n in names)


def test_atlassian_reflects_env(monkeypatch):
    monkeypatch.delenv("JIRA_URL", raising=False)
    off = {c.name: c for c in optional_features()}
    assert off["jira (Server)"].available is False

    monkeypatch.setenv("JIRA_URL", "https://jira.local")
    on = {c.name: c for c in optional_features()}
    assert on["jira (Server)"].available is True
    assert on["jira (Server)"].detail == "configured"


def test_every_capability_has_a_detail_hint():
    for cap in optional_features():
        assert cap.detail  # non-empty guidance either way
