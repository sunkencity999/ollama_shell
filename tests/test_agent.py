"""End-to-end agent-loop tests using a scripted fake provider (no network)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from oshell.agent import Agent, TextDelta, ToolFinished, ToolStarted, TurnComplete
from oshell.config import Config
from oshell.providers.base import ChatChunk, LLMProvider, Message, ToolCall
from oshell.tools import ToolRegistry
from oshell.tools.builtins import CurrentTimeTool


class ScriptedProvider(LLMProvider):
    """Yields a pre-baked sequence of responses, one per chat() call."""

    name = "scripted"

    def __init__(self, script: list[list[ChatChunk]]):
        self._script = script
        self.calls = 0

    def list_models(self) -> list[str]:
        return ["scripted-model"]

    def chat(self, messages: list[Message], **kwargs: Any) -> Iterator[ChatChunk]:
        chunks = self._script[self.calls]
        self.calls += 1
        yield from chunks


def _agent(script):
    provider = ScriptedProvider(script)
    reg = ToolRegistry([CurrentTimeTool()])
    return Agent(provider, reg, Config()), provider


def test_plain_text_turn():
    agent, _ = _agent([[ChatChunk(content="Hello "), ChatChunk(content="world", done=True)]])
    events = list(agent.send("hi"))
    assert "".join(e.text for e in events if isinstance(e, TextDelta)) == "Hello world"
    assert isinstance(events[-1], TurnComplete)
    assert events[-1].text == "Hello world"


def test_tool_call_round_trip():
    # Round 1: model asks for the tool. Round 2: model answers using the result.
    script = [
        [ChatChunk(tool_calls=[ToolCall(name="current_time", arguments={})], done=True)],
        [ChatChunk(content="The time is recorded.", done=True)],
    ]
    agent, provider = _agent(script)
    events = list(agent.send("what time is it?"))

    assert any(isinstance(e, ToolStarted) and e.name == "current_time" for e in events)
    assert any(isinstance(e, ToolFinished) for e in events)
    assert isinstance(events[-1], TurnComplete)
    assert provider.calls == 2  # looped back after the tool result
    # A tool-result message was threaded into the conversation.
    assert any(m.role == "tool" for m in agent.messages)


def test_iteration_cap():
    from oshell.agent import LimitReached

    # Always asks for a tool -> never terminates on its own.
    cfg = Config(max_tool_iterations=3)
    provider = ScriptedProvider(
        [[ChatChunk(tool_calls=[ToolCall(name="current_time", arguments={})], done=True)]] * 3
    )
    agent = Agent(provider, ToolRegistry([CurrentTimeTool()]), cfg)
    events = list(agent.send("loop forever"))
    assert isinstance(events[-1], LimitReached)
    assert events[-1].iterations == 3


def test_send_attaches_images():
    agent, _ = _agent([[ChatChunk(content="ok", done=True)]])
    list(agent.send("what is this?", images=["BASE64IMG"]))
    user = next(m for m in agent.messages if m.role == "user")
    assert user.images == ["BASE64IMG"]
    assert user.to_wire()["images"] == ["BASE64IMG"]  # flows through to the backend


def test_system_prompt_is_tool_aware():
    from oshell.tools.builtins import CurrentTimeTool
    from oshell.tools.web import WebSearchTool

    reg = ToolRegistry([CurrentTimeTool(), WebSearchTool()])
    agent = Agent(ScriptedProvider([]), reg, Config())
    sysmsg = agent.messages[0].content
    # Lists the actual tools...
    assert "current_time" in sysmsg and "web_search" in sysmsg
    # ...and tells the model it is NOT offline (web_search reaches the network).
    assert "internet" in sysmsg.lower()
    assert "web_search" in sysmsg


def test_system_prompt_no_internet_line_without_network_tools():
    from oshell.tools.builtins import CurrentTimeTool

    reg = ToolRegistry([CurrentTimeTool()])  # local-only
    agent = Agent(ScriptedProvider([]), reg, Config())
    assert "NOT a disconnected model" not in agent.messages[0].content


def test_context_pin_exclude():
    agent, _ = _agent([[ChatChunk(content="ok", done=True)]])
    list(agent.send("first"))
    # Exclude the user message; it should drop from the wire context.
    user_idx = next(i for i, m in enumerate(agent.messages) if m.content == "first")
    agent.exclude(user_idx)
    assert all(m.content != "first" for m in agent._context())
    # System prompt is pinned and cannot be excluded.
    import pytest

    with pytest.raises(ValueError):
        agent.exclude(0)
