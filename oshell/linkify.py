"""Turn bare URLs in model prose into real markdown links.

Rich's Markdown makes ``[text](url)`` clickable-styled, but local models
mostly emit naked ``https://…`` — which renders as plain text. We wrap those
in markdown link syntax before rendering, carefully staying out of fenced
code blocks and inline code spans (a URL in code is code).
"""

from __future__ import annotations

import re

# Prose URL: stop at whitespace and markdown-significant closers; a negative
# lookbehind keeps us off URLs already inside [text](url) or <autolink>.
_URL = re.compile(r"(?<![(<\[])(https?://[^\s<>\)\]]+)")
# Split points whose insides we must not touch: fenced blocks first (greedy
# across lines), then inline code spans.
_PROTECTED = re.compile(r"(```.*?```|~~~.*?~~~|`[^`\n]*`)", re.DOTALL)
_TRAILING_PUNCT = ".,;:!?'\""


def _link_one(match: re.Match) -> str:
    url = match.group(1)
    # "see https://example.com." — the period is prose, not path.
    tail = ""
    while url and url[-1] in _TRAILING_PUNCT:
        tail = url[-1] + tail
        url = url[:-1]
    return f"[{url}]({url}){tail}" if url else match.group(0)


def linkify_urls(text: str) -> str:
    """Markdown-linkify bare URLs, leaving code blocks/spans untouched."""
    parts = _PROTECTED.split(text)
    # Even indices are prose; odd indices are the protected code segments.
    return "".join(
        part if i % 2 else _URL.sub(_link_one, part) for i, part in enumerate(parts)
    )
