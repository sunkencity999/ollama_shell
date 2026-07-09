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

    # Always asks for a tool -> never terminates on its own. After the cap, the
    # loop does ONE tool-free call so the user still gets a final answer.
    cfg = Config(max_tool_iterations=3)
    provider = ScriptedProvider(
        [[ChatChunk(tool_calls=[ToolCall(name="current_time", arguments={})], done=True)]] * 3
        + [[ChatChunk(content="Best answer with what I gathered.", done=True)]]
    )
    agent = Agent(provider, ToolRegistry([CurrentTimeTool()]), cfg)
    events = list(agent.send("loop forever"))
    # The cap is reported...
    lim = next(e for e in events if isinstance(e, LimitReached))
    assert lim.iterations == 3
    # ...but the turn still ends with a usable answer, not a dead stop.
    assert isinstance(events[-1], TurnComplete)
    assert events[-1].text == "Best answer with what I gathered."
    assert provider.calls == 4  # 3 capped tool rounds + 1 tool-free finalization


class _CapProvider(LLMProvider):
    """Records the tools it was given; reports configurable capabilities."""

    name = "cap"

    def __init__(self, caps):
        self._caps = set(caps)
        self.last_tools = "unset"

    def list_models(self):
        return ["m"]

    def capabilities(self, model):
        return self._caps

    def chat(self, messages, *, model, tools=None, **kwargs):
        self.last_tools = tools
        yield ChatChunk(content="ok", done=True)


def _cap_agent(caps):
    prov = _CapProvider(caps)
    return Agent(prov, ToolRegistry([CurrentTimeTool()]), Config()), prov


def test_tools_suppressed_for_non_tool_model():
    agent, prov = _cap_agent({"vision"})  # vision-only, no tools (like llava)
    list(agent.send("hi"))
    assert prov.last_tools is None  # not advertised -> no 400


def test_tools_kept_for_capable_model_even_with_image():
    agent, prov = _cap_agent({"vision", "tools"})  # e.g. gemma3/4
    list(agent.send("look", images=["B64"]))
    assert prov.last_tools is not None  # capable model keeps tools on image turns


def test_tools_assumed_when_capabilities_unknown():
    agent, prov = _cap_agent(set())  # unknown -> assume capable
    list(agent.send("hi"))
    assert prov.last_tools is not None


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


def test_unfulfilled_promise_gets_one_nudge_then_acts():
    # Round 1: model announces a search but calls no tool -> loop nudges it.
    # Round 2: model actually calls the tool. Round 3: it answers.
    script = [
        [ChatChunk(content="I'm going to search for that now. One moment!", done=True)],
        [ChatChunk(tool_calls=[ToolCall(name="current_time", arguments={})], done=True)],
        [ChatChunk(content="Here is the answer.", done=True)],
    ]
    agent, provider = _agent(script)
    events = list(agent.send("look it up"))
    assert provider.calls == 3  # promise -> nudge -> tool -> answer
    assert isinstance(events[-1], TurnComplete)
    assert events[-1].text == "Here is the answer."
    # The nudge was threaded in as a user message.
    assert any(m.role == "user" and "called no tool" in m.content for m in agent.messages)


def test_promise_nudged_at_most_max_times():
    # The model keeps narrating without ever calling a tool: we prod it up to the
    # configured cap, then accept its text instead of looping forever.
    script = [
        [ChatChunk(content="I'll look that up for you.", done=True)],
        [ChatChunk(content="I'll go and search now, hold on.", done=True)],
    ]
    agent, provider = _agent(script)
    agent.config.max_promise_nudges = 1  # cap at a single nudge for a deterministic count
    events = list(agent.send("look it up"))
    assert provider.calls == 2  # original + exactly one nudge
    assert isinstance(events[-1], TurnComplete)
    assert events[-1].text == "I'll go and search now, hold on."


def test_plain_answer_is_not_nudged():
    # A normal final answer (no future-intent + action verb) must not trigger a nudge.
    agent, provider = _agent([[ChatChunk(content="The answer is 42.", done=True)]])
    events = list(agent.send("what is the answer?"))
    assert provider.calls == 1
    assert isinstance(events[-1], TurnComplete)


# ── effective context: explicit config wins; auto sizes from the model ────────


class _CtxProvider(LLMProvider):
    name = "ctx"

    def __init__(self, trained=None):
        self.trained = trained
        self.seen_num_ctx = []

    def list_models(self):
        return ["m"]

    def max_context(self, model):
        return self.trained

    def chat(self, messages, **kwargs) -> Iterator[ChatChunk]:
        self.seen_num_ctx.append(kwargs.get("num_ctx"))
        yield ChatChunk(content="ok", done=True)


def test_effective_context_explicit_config_wins():
    cfg = Config(context_length=4096)
    agent = Agent(_CtxProvider(trained=131072), ToolRegistry([]), cfg)
    assert agent.effective_context() == 4096


def test_effective_context_auto_caps_big_models():
    from oshell.config import AUTO_CONTEXT_CAP

    cfg = Config()  # context_length = 0 -> auto
    agent = Agent(_CtxProvider(trained=131072), ToolRegistry([]), cfg)
    assert agent.effective_context() == AUTO_CONTEXT_CAP


def test_effective_context_auto_uses_model_max_when_modest():
    agent = Agent(_CtxProvider(trained=16384), ToolRegistry([]), Config())
    assert agent.effective_context() == 16384


def test_effective_context_unknown_falls_back():
    agent = Agent(_CtxProvider(trained=None), ToolRegistry([]), Config())
    assert agent.effective_context() == 8192


def test_send_passes_num_ctx_to_provider():
    provider = _CtxProvider(trained=16384)
    agent = Agent(provider, ToolRegistry([]), Config())
    list(agent.send("hello"))
    assert provider.seen_num_ctx == [16384]
