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
