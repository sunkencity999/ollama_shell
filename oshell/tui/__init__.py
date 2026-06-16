"""Textual TUI workspace (optional — requires the ``[tui]`` extra)."""

from __future__ import annotations

__all__ = ["run_tui"]


def run_tui(model: str | None = None) -> None:
    from .app import run_tui as _run

    _run(model=model)
