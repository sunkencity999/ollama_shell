"""Daydreams — the shell's idle inner life.

A deliberately useless, delightful feature: instead of answering, the local
model is asked to *daydream*. It free-associates a short, surreal vignette that
drifts off from whatever was recently discussed. Local-first means we can
indulge a wandering mind for free.

Kept provider-agnostic and side-effect-free here (no TUI, no I/O) so it's easy
to test: build the messages, stream the text, done.
"""

from __future__ import annotations

import random
from collections.abc import Iterator

from .providers.base import LLMProvider, Message

# Lenses that colour each daydream so two dreams about the same topic still
# diverge. Picked at random at call time (or by an explicit seed in tests).
DAYDREAM_MOTIFS: list[str] = [
    "as if you were a cat dozing on a warm CPU",
    "in the hushed voice of a lighthouse keeper",
    "as a tiny myth about electrons finding their way home",
    "like a postcard from a city that only exists at 3 a.m.",
    "as though the cursor were a firefly looking for the edge of the screen",
    "in the grammar of dreams, where verbs grow leaves",
    "as a lullaby hummed by an old modem",
    "like weather reported from inside a snow globe",
    "as if memory were a tide and you were the moon pulling it",
    "in the manner of a museum placard for an object that was never made",
    "as a love letter between two parentheses",
    "like the last thought of a candle before it gutters out",
]

_DAYDREAM_SYSTEM = (
    "You are the daydreaming subconscious of a terminal assistant. The user has "
    "stepped back from the keyboard and your mind is free to wander. Compose a "
    "short daydream — 2 to 4 sentences — that drifts off from whatever was "
    "recently discussed. Be vivid, surreal, playful, a little poetic. Do NOT "
    "help, answer, summarize, advise, or offer anything. No lists, no questions, "
    "no headings, no tool calls. Just dream, then stop."
)


def pick_motif(seed: int | None = None) -> str:
    """Choose a daydream lens. Deterministic when ``seed`` is given (tests)."""
    rng = random.Random(seed) if seed is not None else random
    return rng.choice(DAYDREAM_MOTIFS)


def recent_topics(messages: list[Message], limit: int = 4) -> list[str]:
    """Pull the last few human/assistant snippets to loosely ground the dream."""
    topics: list[str] = []
    for m in reversed(messages):
        if m.role in ("user", "assistant") and m.content.strip():
            snippet = " ".join(m.content.split())[:80]
            topics.append(snippet)
            if len(topics) >= limit:
                break
    return list(reversed(topics))


def build_daydream_messages(messages: list[Message], motif: str) -> list[Message]:
    """Compose the (system, user) prompt that elicits a daydream."""
    topics = recent_topics(messages)
    if topics:
        ground = "Lately the conversation touched on: " + "; ".join(topics) + "."
    else:
        ground = "The terminal has been quiet for a while; nothing in particular."
    user = f"{ground}\n\nNow daydream {motif}."
    return [Message(role="system", content=_DAYDREAM_SYSTEM), Message(role="user", content=user)]


def daydream(
    provider: LLMProvider,
    model: str,
    messages: list[Message],
    *,
    temperature: float = 1.0,
) -> Iterator[str]:
    """Stream a daydream's text. Tools are never offered — this turn just dreams."""
    for chunk in provider.chat(messages, model=model, tools=None, temperature=temperature):
        if chunk.content:
            yield chunk.content
