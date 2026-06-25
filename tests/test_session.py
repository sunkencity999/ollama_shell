"""Tests for conversation persistence / resume."""

from __future__ import annotations

from oshell.providers.base import Message, ToolCall
from oshell.session import clear_session, load_session, save_session


def test_roundtrip_excludes_system_and_images(tmp_path):
    path = tmp_path / "s.json"
    msgs = [
        Message(role="system", content="SYS"),
        Message(role="user", content="hi"),
        Message(
            role="assistant",
            content="",
            tool_calls=[ToolCall(name="current_time", arguments={}, id="c1")],
        ),
        Message(role="tool", content="2026", tool_call_id="c1", images=["BIGB64"]),
        Message(role="assistant", content="it is 2026"),
    ]
    save_session(msgs, path)
    loaded = load_session(path)
    assert [m.role for m in loaded] == ["user", "assistant", "tool", "assistant"]  # system dropped
    assert loaded[0].content == "hi"
    assert loaded[1].tool_calls[0].name == "current_time"
    assert loaded[2].images == []  # images not persisted


def test_load_missing_is_empty(tmp_path):
    assert load_session(tmp_path / "nope.json") == []


def test_max_messages_caps(tmp_path):
    path = tmp_path / "s.json"
    msgs = [Message(role="user", content=str(i)) for i in range(10)]
    save_session(msgs, path, max_messages=3)
    loaded = load_session(path)
    assert [m.content for m in loaded] == ["7", "8", "9"]


def test_clear(tmp_path):
    path = tmp_path / "s.json"
    save_session([Message(role="user", content="x")], path)
    assert load_session(path)
    clear_session(path)
    assert load_session(path) == []
