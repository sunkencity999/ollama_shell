"""Tests for the persistent memory layer (store, tools, prompt injection)."""

from __future__ import annotations

from oshell.agent import Agent
from oshell.agent.loop import build_system_prompt
from oshell.config import Config
from oshell.memory import MemoryStore
from oshell.providers.base import ChatChunk, LLMProvider, ToolCall
from oshell.tools import ToolRegistry
from oshell.tools.builtins import CurrentTimeTool
from oshell.tools.memory import ForgetTool, RecallTool, RememberTool, memory_tools


def _store(tmp_path):
    return MemoryStore(tmp_path / "memory.json")


def test_add_persists_and_dedupes(tmp_path):
    s = _store(tmp_path)
    s.add("uses zsh")
    s.add("uses zsh")  # dup ignored
    s.add("prefers concise answers")
    assert len(s.all()) == 2
    # persisted across instances
    assert len(MemoryStore(tmp_path / "memory.json").all()) == 2


def test_search_by_keyword(tmp_path):
    s = _store(tmp_path)
    s.add("the project codename is Bluejay")
    s.add("the cafeteria serves tacos on Tuesday")
    hits = s.search("what is the codename", limit=1)
    assert hits and "Bluejay" in hits[0]["text"]


def test_forget_by_substring_and_clear(tmp_path):
    s = _store(tmp_path)
    s.add("likes dark mode")
    s.add("likes tacos")
    assert s.forget("tacos") == 1
    assert len(s.all()) == 1
    s.add("another")
    assert s.clear() == 2
    assert s.all() == []


def test_remember_recall_forget_tools(tmp_path):
    s = _store(tmp_path)
    reg = ToolRegistry([RememberTool(s), RecallTool(s), ForgetTool(s)])
    out = reg.dispatch(ToolCall(name="remember", arguments={"text": "name is Chris"}))
    assert "remembered" in out
    assert "Chris" in reg.dispatch(ToolCall(name="recall", arguments={"query": "name"}))
    assert "forgot 1" in reg.dispatch(ToolCall(name="forget", arguments={"text": "Chris"}))


def test_forget_all_clears(tmp_path):
    s = _store(tmp_path)
    s.add("a")
    s.add("b")
    out = ForgetTool(s).run(text="all")
    assert "forgot 2" in out and s.all() == []


def test_memory_injected_into_system_prompt(tmp_path):
    s = _store(tmp_path)
    s.add("prefers concise answers")
    reg = ToolRegistry([CurrentTimeTool(), *memory_tools(s)])
    prompt = build_system_prompt(reg, memory=s)
    assert "Things you remember about the user" in prompt
    assert "prefers concise answers" in prompt
    assert "remember(" in prompt  # hybrid-capture instruction present


def test_agent_uses_shared_memory(tmp_path):
    s = _store(tmp_path)

    class _P(LLMProvider):
        name = "p"

        def list_models(self):
            return ["m"]

        def chat(self, messages, **k):
            # remember a fact, then finish
            yield ChatChunk(
                tool_calls=[ToolCall(name="remember", arguments={"text": "likes vim"})], done=True
            )

    reg = ToolRegistry([*memory_tools(s)])
    agent = Agent(_P(), reg, Config(), memory=s)
    # one round records the memory via the tool
    list(agent.send("I use vim"))
    assert any("likes vim" == m["text"] for m in s.all())
    # rebuilding the prompt now injects it
    agent.rebuild_system_prompt()
    assert "likes vim" in agent.messages[0].content


def test_recall_returns_message(tmp_path):
    s = _store(tmp_path)
    out = RecallTool(s).run(query="anything")
    assert "no matching" in out
