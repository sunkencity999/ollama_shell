"""Bare-URL linkification: prose becomes clickable, code stays code."""

from __future__ import annotations

from oshell.linkify import linkify_urls


def test_bare_url_becomes_markdown_link():
    assert (
        linkify_urls("see https://example.com/docs for more")
        == "see [https://example.com/docs](https://example.com/docs) for more"
    )


def test_trailing_punctuation_stays_prose():
    assert (
        linkify_urls("read https://example.com.")
        == "read [https://example.com](https://example.com)."
    )
    assert linkify_urls("really: https://a.io/x?q=1!").endswith("(https://a.io/x?q=1)!")


def test_existing_markdown_links_untouched():
    text = "the [docs](https://example.com/docs) explain it"
    assert linkify_urls(text) == text
    auto = "an autolink <https://example.com> here"
    assert linkify_urls(auto) == auto


def test_code_is_left_alone():
    inline = "run `curl https://api.local/v1` to test"
    assert linkify_urls(inline) == inline
    fenced = "```bash\ncurl https://api.local/v1\n```\nsee https://example.com"
    out = linkify_urls(fenced)
    assert "curl https://api.local/v1\n```" in out  # fenced content untouched
    assert "[https://example.com](https://example.com)" in out  # prose linkified


def test_query_strings_and_fragments_survive():
    url = "https://example.com/a?b=c&d=e#frag"
    assert linkify_urls(f"go to {url} now") == f"go to [{url}]({url}) now"


def test_no_urls_no_change():
    text = "nothing to see here.\n\n- just\n- a list"
    assert linkify_urls(text) == text
