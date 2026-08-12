"""Clickable links in the transcript: LinkLog opens the URL under the pointer."""

from __future__ import annotations

import pytest

pytest.importorskip("textual")

from rich.style import Style  # noqa: E402
from rich.text import Text  # noqa: E402
from textual.app import App, ComposeResult  # noqa: E402

from oshell.tui.app import LinkLog  # noqa: E402


class _LinkApp(App):
    def __init__(self) -> None:
        super().__init__()
        self.opened: list[str] = []

    def compose(self) -> ComposeResult:
        yield LinkLog()

    def open_url(self, url: str, *, new_tab: bool = True) -> None:  # no real browser
        self.opened.append(url)


async def test_click_on_link_opens_it():
    app = _LinkApp()
    async with app.run_test() as pilot:
        log = app.query_one(LinkLog)
        log.write(Text("open the docs", style=Style(link="https://example.com/docs")))
        await pilot.pause()
        await pilot.click(LinkLog, offset=(3, 0))  # inside "open the docs"
        assert app.opened == ["https://example.com/docs"]


async def test_click_on_plain_text_opens_nothing():
    app = _LinkApp()
    async with app.run_test() as pilot:
        log = app.query_one(LinkLog)
        log.write(Text("plain prose, no link"))
        await pilot.pause()
        await pilot.click(LinkLog, offset=(3, 0))
        assert app.opened == []


async def _drag(pilot, start: tuple[int, int], end: tuple[int, int]) -> None:
    await pilot.mouse_down(LinkLog, offset=start)
    await pilot.hover(LinkLog, offset=end)
    await pilot.mouse_up(LinkLog, offset=end)
    await pilot.pause()


async def test_drag_selects_exact_characters():
    app = _LinkApp()
    async with app.run_test() as pilot:
        log = app.query_one(LinkLog)
        log.write(Text("hello selectable world"))
        await pilot.pause()
        await _drag(pilot, (2, 0), (10, 0))
        assert app.screen.get_selected_text() == "llo selec"


async def test_multiline_drag_and_ctrl_c_copies_without_quitting():
    app = _LinkApp()
    copied: list[str] = []
    app.copy_to_clipboard = copied.append  # no real clipboard in CI
    async with app.run_test() as pilot:
        log = app.query_one(LinkLog)
        log.write(Text("first line here"))
        log.write(Text("second line here"))
        await pilot.pause()
        await _drag(pilot, (6, 0), (6, 1))
        await pilot.press("ctrl+c")
        # (Textual's multi-line selection end is inclusive of the cell under
        # the pointer, hence the strip before comparing.)
        assert [c.rstrip() for c in copied] == ["line here\nsecond"]
        assert app.is_running  # ctrl+c with a selection copies; it must not quit


async def test_selection_is_visibly_highlighted():
    """The selected span paints with the screen--selection style — and the
    highlight covers exactly the characters that ctrl+c would copy."""
    app = _LinkApp()
    async with app.run_test() as pilot:
        log = app.query_one(LinkLog)
        log.write(Text("hello selectable world"))
        await pilot.pause()
        await _drag(pilot, (2, 0), (10, 0))
        sel_style = app.screen.get_component_rich_style("screen--selection")
        highlighted = "".join(
            seg.text
            for seg in log.render_line(0)
            if seg.style and seg.style.bgcolor == sel_style.bgcolor
        )
        assert highlighted == "llo selec"
        assert app.screen.get_selected_text() == "llo selec"  # highlight == copy


async def test_no_selection_paints_no_highlight():
    app = _LinkApp()
    async with app.run_test() as pilot:
        log = app.query_one(LinkLog)
        log.write(Text("nothing selected here"))
        await pilot.pause()
        sel_style = app.screen.get_component_rich_style("screen--selection")
        assert not any(
            seg.style and seg.style.bgcolor == sel_style.bgcolor
            for seg in log.render_line(0)
        )


async def test_drag_ending_on_link_selects_instead_of_opening():
    app = _LinkApp()
    async with app.run_test() as pilot:
        log = app.query_one(LinkLog)
        log.write(Text("plain line"))
        log.write(Text("visit the docs", style=Style(link="https://example.com/docs")))
        await pilot.pause()
        await _drag(pilot, (0, 0), (5, 1))
        assert app.opened == []  # a selection drag never navigates
        assert "plain line\nvisit" in (app.screen.get_selected_text() or "")


async def test_markdown_reply_links_are_clickable():
    """The full path a reply takes: linkify -> rich Markdown -> LinkLog click."""
    from rich.markdown import Markdown

    from oshell.linkify import linkify_urls

    app = _LinkApp()
    async with app.run_test() as pilot:
        log = app.query_one(LinkLog)
        log.write(Markdown(linkify_urls("docs live at https://example.com/x")))
        await pilot.pause()
        # "docs live at " is 13 cells; click a few cells into the URL text.
        await pilot.click(LinkLog, offset=(16, 0))
        assert app.opened == ["https://example.com/x"]
