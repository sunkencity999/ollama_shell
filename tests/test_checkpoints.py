"""Checkpoints: snapshot before the model writes, /undo rewinds."""

from __future__ import annotations

import pytest

from oshell import checkpoints


def test_overwrite_then_undo_restores_contents(tmp_path):
    store = tmp_path / "cps"
    target = tmp_path / "notes.txt"
    target.write_text("original", encoding="utf-8")
    cid = checkpoints.before_tool("write_file", {"path": str(target)}, directory=store)
    assert cid is not None
    target.write_text("clobbered by the model", encoding="utf-8")
    outcome = checkpoints.undo_last(directory=store)
    assert "restored" in outcome
    assert target.read_text(encoding="utf-8") == "original"


def test_created_file_undo_deletes_it(tmp_path):
    store = tmp_path / "cps"
    target = tmp_path / "brand_new.txt"
    checkpoints.before_tool("create_document", {"path": str(target)}, directory=store)
    target.write_text("should not exist", encoding="utf-8")
    outcome = checkpoints.undo_last(directory=store)
    assert "removed" in outcome
    assert not target.exists()


def test_non_writer_tools_are_ignored(tmp_path):
    assert checkpoints.before_tool("web_search", {"query": "x"}, directory=tmp_path) is None
    assert checkpoints.before_tool("write_file", {}, directory=tmp_path) is None  # no path


def test_undo_with_no_checkpoints_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        checkpoints.undo_last(directory=tmp_path / "empty")


def test_undo_consumes_newest_first(tmp_path):
    store = tmp_path / "cps"
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text("A1", encoding="utf-8")
    b.write_text("B1", encoding="utf-8")
    checkpoints.before_tool("write_file", {"path": str(a)}, directory=store)
    checkpoints.before_tool("write_file", {"path": str(b)}, directory=store)
    a.write_text("A2", encoding="utf-8")
    b.write_text("B2", encoding="utf-8")
    assert "b.txt" in checkpoints.undo_last(directory=store)  # newest first
    assert b.read_text(encoding="utf-8") == "B1" and a.read_text(encoding="utf-8") == "A2"
    assert "a.txt" in checkpoints.undo_last(directory=store)
    assert a.read_text(encoding="utf-8") == "A1"


def test_prune_keeps_recent(tmp_path, monkeypatch):
    store = tmp_path / "cps"
    monkeypatch.setattr(checkpoints, "MAX_KEPT", 3)
    target = tmp_path / "f.txt"
    target.write_text("x", encoding="utf-8")
    for _ in range(6):
        checkpoints.before_tool("write_file", {"path": str(target)}, directory=store)
    kept = [d for d in store.iterdir() if d.is_dir()]
    assert len(kept) == 3
