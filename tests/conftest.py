"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    """Run every test from a throwaway directory.

    Some code persists to the *current* directory (e.g. the model picker writes
    ``default_model`` to ``config.local.json``). Without this, running the suite
    from the repo would clobber the real config — which is exactly the bug that
    once set the live default model to the test's ``scripted-model``.
    """
    monkeypatch.chdir(tmp_path)
