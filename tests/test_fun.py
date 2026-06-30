"""Tests for daydreams — the shell's quirky idle inner life."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from oshell import fun
from oshell.providers.base import ChatChunk, LLMProvider, Message


class _Dreamer(LLMProvider):
    """A provider that streams a fixed daydream in three pieces."""

    name = "dreamer"

    def __init__(self) -> None:
        self.last_kwargs: dict[str, Any] = {}

    def list_models(self) -> list[str]:
        return ["dream-model"]

    def chat(self, messages: list[Message], **kwargs: Any) -> Iterator[ChatChunk]:
        self.last_kwargs = kwargs
        self.last_messages = messages
        for piece in ("a clock ", "made of ", "warm rain"):
            yield ChatChunk(content=piece)
        yield ChatChunk(done=True)


def test_pick_motif_is_deterministic_with_seed():
    assert fun.pick_motif(0) == fun.pick_motif(0)
    assert fun.pick_motif(0) in fun.DAYDREAM_MOTIFS


def test_recent_topics_takes_last_human_assistant_in_order():
    msgs = [
        Message(role="system", content="ignored system prompt"),
        Message(role="user", content="tell me about g-shock watches"),
        Message(role="assistant", content="The GWG-1000 is a Mudmaster..."),
        Message(role="tool", content="ignored tool output"),
        Message(role="user", content="which button is the light?"),
    ]
    topics = fun.recent_topics(msgs, limit=2)
    # Most recent two, in chronological order; system/tool excluded.
    assert topics == ["The GWG-1000 is a Mudmaster...", "which button is the light?"]


def test_build_messages_grounds_in_topics_and_motif():
    msgs = [Message(role="user", content="quantum tea ceremonies")]
    out = fun.build_daydream_messages(msgs, "as a tiny myth")
    assert out[0].role == "system" and "daydream" in out[0].content.lower()
    assert "quantum tea ceremonies" in out[1].content
    assert "as a tiny myth" in out[1].content


def test_build_messages_handles_empty_history():
    out = fun.build_daydream_messages([], "as a lullaby")
    assert "quiet" in out[1].content.lower()
    assert "as a lullaby" in out[1].content


def test_daydream_streams_text_and_never_offers_tools():
    provider = _Dreamer()
    msgs = fun.build_daydream_messages([], fun.pick_motif(1))
    text = "".join(fun.daydream(provider, "dream-model", msgs))
    assert text == "a clock made of warm rain"
    # Daydreams must never advertise tools — the model just dreams.
    assert provider.last_kwargs.get("tools") is None
