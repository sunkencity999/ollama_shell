"""Context compaction: fold old turns into a summary, never lose the thread."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from oshell.agent import Agent, Compacted
from oshell.config import Config
from oshell.providers.base import ChatChunk, LLMProvider, Message
from oshell.tools import ToolRegistry


class _Summarizer(LLMProvider):
    """Answers every chat() with a canned summary; records the model used."""

    name = "summarizer"

    def __init__(self, reply="- earlier: user set up a project"):
        self.reply = reply
        self.models_used: list[str] = []

    def list_models(self):
        return ["m", "fast:4b"]

    def chat(self, messages: list[Message], *, model="", **kw: Any) -> Iterator[ChatChunk]:
        self.models_used.append(model)
        yield ChatChunk(content=self.reply, done=True)


def _stuffed_agent(n_pairs=10, **config_kwargs) -> tuple[Agent, _Summarizer]:
    provider = _Summarizer()
    agent = Agent(provider, ToolRegistry([]), Config(**config_kwargs), model="m")
    for i in range(n_pairs):
        agent.messages.append(Message(role="user", content=f"question {i} " + "x" * 200))
        agent.messages.append(Message(role="assistant", content=f"answer {i} " + "y" * 200))
    return agent, provider


def test_compact_replaces_old_with_summary_keeps_tail():
    agent, provider = _stuffed_agent()
    before = len(agent.messages)
    info = agent.compact(keep_recent=4)
    assert isinstance(info, Compacted) and info.dropped > 0
    assert len(agent.messages) == before - info.dropped
    # Summary message present, tail intact, system prompt untouched.
    assert agent.messages[0].role == "system"
    assert "compacted to save context" in agent.messages[1].content
    assert agent.messages[-1].content.startswith("answer 9")
    assert agent.messages[-4].content.startswith("question 8")


def test_compact_preserves_pinned_and_clears_excluded():
    agent, _ = _stuffed_agent()
    agent.pin(3)  # "answer 0 yyy…"
    agent.exclude(4)
    pinned_text = agent.messages[3].content
    agent.compact(keep_recent=4)
    assert agent.messages[1].content == pinned_text  # survived verbatim, in order
    assert agent.excluded == set()
    # Structural prefix (system + pinned + summary) is pinned against future passes.
    assert {0, 1, 2} <= agent.pinned


def test_compact_uses_fast_model_when_routed():
    agent, provider = _stuffed_agent()
    agent.config.routing.fast_model = "fast:4b"
    agent.compact(keep_recent=4)
    assert provider.models_used == ["fast:4b"]


def test_short_conversation_is_left_alone():
    agent, provider = _stuffed_agent(n_pairs=2)
    assert agent.compact(keep_recent=6) is None
    assert provider.models_used == []  # no wasted summarizer call


def test_tail_never_opens_with_orphan_tool_result():
    from oshell.providers.base import ToolCall

    agent, _ = _stuffed_agent()
    # A realistic tool exchange landing right at the cut boundary:
    # assistant requests → tool answers → conversation continues.
    agent.messages[-3:-3] = [
        Message(role="assistant", content="", tool_calls=[ToolCall(name="t", arguments={})]),
        Message(role="tool", content="tool output", tool_call_id="t1"),
    ]
    agent.compact(keep_recent=4)
    kept = agent.messages
    assert kept[0].role == "system"
    for i, m in enumerate(kept):
        if m.role == "tool":  # every kept tool result still has its parent before it
            assert kept[i - 1].role in ("assistant", "tool")


def test_auto_compact_fires_in_send():
    # A tiny context window + stuffed history => send() compacts before asking.
    agent, provider = _stuffed_agent(context_length=256, compact_threshold=0.5)
    events = list(agent.send("one more question"))
    assert any(isinstance(e, Compacted) for e in events)


def test_auto_compact_disabled_by_zero_threshold():
    agent, _ = _stuffed_agent(context_length=256, compact_threshold=0.0)
    events = list(agent.send("one more question"))
    assert not any(isinstance(e, Compacted) for e in events)


def test_context_fill_shrinks_after_compaction():
    agent, _ = _stuffed_agent(context_length=1024)
    before = agent.context_fill()
    agent.compact(keep_recent=4)
    assert agent.context_fill() < before
