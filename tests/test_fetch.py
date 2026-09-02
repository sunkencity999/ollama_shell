"""oshell fetch / screensaver: pure renderers, no backend needed."""

from __future__ import annotations

from rich.console import Console

from oshell import fetch, themes
from oshell.config import Config


def test_fetch_card_renders_logo_and_facts_without_a_backend():
    cfg = Config(default_model="demo-model")
    p = themes.get_palette("everforest")
    console = Console(record=True, width=120, force_terminal=True)
    console.print(fetch.render(cfg, p, "everforest", width=120, probe_backend=False))
    text = console.export_text()
    assert "██████╗" in text  # the wordmark
    assert "demo-model" in text and "everforest" in text and "ollama" in text
    for label in ("os", "shell", "ram", "sessions", "memories", "approvals", "mood"):
        assert label in text
    # Narrow terminals get the compact mark instead of the six-row wordmark.
    narrow = Console(record=True, width=70, force_terminal=True)
    narrow.print(fetch.render(cfg, p, "everforest", width=70, probe_backend=False))
    assert "██████╗" not in narrow.export_text()


def test_logo_rows_are_rectangular():
    assert len({len(r) for r in fetch.LOGO}) == 1
    assert len({len(r) for r in fetch.MARK}) == 1
    t = fetch.logo_text(themes.get_palette("nord"))
    assert t.plain.count("\n") == len(fetch.LOGO) - 1


def test_screensaver_frame_is_exactly_the_terminal_size():
    from oshell import screensaver

    p = themes.get_palette("tokyo-night")
    for mood in ("rain", "none", "matrix"):
        f = screensaver.frame(p, mood, 100, 30, tick=7)
        lines = f.plain.split("\n")
        assert len(lines) == 30 and all(len(ln) == 100 for ln in lines)
    # The wordmark is present when it fits, absent when it can't.
    assert "██████╗" in screensaver.frame(p, "none", 100, 30, 0).plain
    assert "██████╗" not in screensaver.frame(p, "none", 40, 10, 0).plain
    assert "any key wakes" in screensaver.frame(p, "none", 100, 30, 0).plain
