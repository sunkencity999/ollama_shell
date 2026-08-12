"""Named-session store: save, list, resume-by-prefix, delete."""

from __future__ import annotations

import pytest

from oshell import sessions
from oshell.providers.base import Message


def _msgs(*texts: str) -> list[Message]:
    out = [Message(role="system", content="sys")]
    for i, t in enumerate(texts):
        out.append(Message(role="user" if i % 2 == 0 else "assistant", content=t))
    return out


def test_save_and_load_round_trip(tmp_path):
    d = tmp_path / "store"
    sessions.save(_msgs("hello world", "hi!"), sid="20260101-010101", model="m1", directory=d)
    meta, msgs = sessions.load("20260101-010101", d)
    assert meta["model"] == "m1"
    assert meta["title"] == "hello world"
    assert [m.role for m in msgs] == ["user", "assistant"]  # system never persisted
    assert msgs[0].content == "hello world"


def test_title_truncates_first_line(tmp_path):
    long = "x" * 100 + "\nsecond line"
    sessions.save(_msgs(long), sid="s1", model="m", directory=tmp_path)
    meta, _ = sessions.load("s1", tmp_path)
    assert len(meta["title"]) <= 61 and meta["title"].endswith("…")


def test_list_newest_first_and_latest(tmp_path):
    sessions.save(_msgs("older"), sid="20260101-000000", model="m", directory=tmp_path)
    sessions.save(_msgs("newer"), sid="20260202-000000", model="m", directory=tmp_path)
    listed = sessions.list_sessions(tmp_path)
    assert [s["id"] for s in listed] == ["20260202-000000", "20260101-000000"]
    assert sessions.latest_id(tmp_path) == "20260202-000000"
    assert sessions.latest_id(tmp_path / "empty") is None


def test_load_by_unique_prefix_and_ambiguity(tmp_path):
    sessions.save(_msgs("a"), sid="20260101-111111", model="m", directory=tmp_path)
    sessions.save(_msgs("b"), sid="20260202-222222", model="m", directory=tmp_path)
    meta, _ = sessions.load("20260202", tmp_path)  # unique prefix resolves
    assert meta["id"] == "20260202-222222"
    with pytest.raises(ValueError, match="ambiguous"):
        sessions.load("2026", tmp_path)
    with pytest.raises(FileNotFoundError):
        sessions.load("1999", tmp_path)


def test_delete(tmp_path):
    sessions.save(_msgs("bye"), sid="s9", model="m", directory=tmp_path)
    sessions.delete("s9", tmp_path)
    assert sessions.list_sessions(tmp_path) == []
    with pytest.raises(FileNotFoundError):
        sessions.delete("s9", tmp_path)


def test_max_messages_keeps_the_tail(tmp_path):
    texts = [f"msg {i}" for i in range(10)]
    sessions.save(_msgs(*texts), sid="s2", model="m", directory=tmp_path, max_messages=4)
    _, msgs = sessions.load("s2", tmp_path)
    assert len(msgs) == 4
    assert msgs[-1].content == "msg 9"
