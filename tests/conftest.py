"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path, monkeypatch):
    """Run every test from a throwaway directory AND a throwaway HOME.

    Some code persists to the *current* directory (the model picker writes
    ``default_model`` to ``config.local.json``) and to ``~/.oshell/*`` (memory,
    last session, knowledge). Isolating both keeps the suite from clobbering — or
    being polluted by — the real user's files (e.g. resuming the live session).
    """
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))  # Windows
