"""Approval modes: auto runs, ask confirms, read-only hides — and denials fail safe."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from oshell.agent import Agent, ToolFinished
from oshell.config import Config
from oshell.providers.base import ChatChunk, LLMProvider, Message, ToolCall
from oshell.tools import ToolRegistry
from oshell.tools.base import Tool


class _DangerTool(Tool):
    name = "danger"
    description = "pretend shell"
    sensitive = True

    def __init__(self):
        self.ran = 0

    def run(self, **_: Any) -> str:
        self.ran += 1
        return "boom executed"


class _SafeTool(Tool):
    name = "safe"
    description = "harmless"

    def run(self, **_: Any) -> str:
        return "safe done"


class _Scripted(LLMProvider):
    name = "scripted"

    def __init__(self, script):
        self._script = script
        self.calls = 0
        self.tools_seen: list[Any] = []

    def list_models(self):
        return ["m"]

    def chat(self, messages: list[Message], tools=None, **kwargs: Any) -> Iterator[ChatChunk]:
        self.tools_seen.append(tools)
        chunks = self._script[self.calls]
        self.calls += 1
        yield from chunks


def _script_call(name):
    return [
        [ChatChunk(tool_calls=[ToolCall(name=name, arguments={})], done=True)],
        [ChatChunk(content="done", done=True)],
    ]


def _agent(mode, approver=None, script=None):
    provider = _Scripted(script or _script_call("danger"))
    danger, safe = _DangerTool(), _SafeTool()
    agent = Agent(
        provider,
        ToolRegistry([danger, safe]),
        Config(approvals=mode),
        model="m",
        approver=approver,
    )
    return agent, provider, danger


def test_auto_runs_sensitive_tools():
    agent, _, danger = _agent("auto")
    list(agent.send("go"))
    assert danger.ran == 1


def test_ask_with_approval_runs():
    agent, _, danger = _agent("ask", approver=lambda call: True)
    list(agent.send("go"))
    assert danger.ran == 1


def test_ask_declined_denies_with_message():
    agent, _, danger = _agent("ask", approver=lambda call: False)
    events = list(agent.send("go"))
    assert danger.ran == 0
    denial = next(e for e in events if isinstance(e, ToolFinished))
    assert "declined" in denial.result
    # The denial went back to the model as the tool result.
    assert any(m.role == "tool" and "declined" in m.content for m in agent.messages)


def test_ask_without_approver_fails_safe():
    agent, _, danger = _agent("ask", approver=None)
    events = list(agent.send("go"))
    assert danger.ran == 0
    assert any("approval" in e.result for e in events if isinstance(e, ToolFinished))


def test_ask_never_gates_non_sensitive_tools():
    agent, _, _ = _agent(
        "ask", approver=lambda call: False, script=_script_call("safe")
    )
    events = list(agent.send("go"))
    results = [e.result for e in events if isinstance(e, ToolFinished)]
    assert results == ["safe done"]  # ran without asking, despite a deny-all approver


def test_read_only_hides_and_blocks():
    agent, provider, danger = _agent("read-only")
    events = list(agent.send("go"))
    # Not advertised: the specs handed to the provider exclude the sensitive tool…
    advertised = [t["function"]["name"] for t in provider.tools_seen[0]]
    assert "danger" not in advertised and "safe" in advertised
    # …and a stubborn model that calls it anyway is blocked at dispatch.
    assert danger.ran == 0
    assert any(
        "read-only" in e.result for e in events if isinstance(e, ToolFinished)
    )


def test_crashing_approver_denies():
    def bad(call):
        raise RuntimeError("ui went away")

    agent, _, danger = _agent("ask", approver=bad)
    list(agent.send("go"))
    assert danger.ran == 0
