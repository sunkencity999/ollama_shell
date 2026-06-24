"""Tests for the tool registry and built-in tools."""

from __future__ import annotations

from oshell.providers.base import ToolCall
from oshell.tools import ToolRegistry
from oshell.tools.builtins import (
    CurrentTimeTool,
    ListDirTool,
    ReadFileTool,
    WriteFileTool,
)


def test_registry_specs_and_dispatch():
    reg = ToolRegistry([CurrentTimeTool()])
    specs = reg.specs()
    assert specs[0]["function"]["name"] == "current_time"
    out = reg.dispatch(ToolCall(name="current_time", arguments={}))
    assert out  # ISO timestamp string


def test_registry_unknown_tool_is_soft_error():
    reg = ToolRegistry([CurrentTimeTool()])
    out = reg.dispatch(ToolCall(name="nope", arguments={}))
    assert out.startswith("[error]")


def test_enabled_gating():
    reg = ToolRegistry([CurrentTimeTool()], enabled=["nothing"])
    assert reg.specs() == []
    assert reg.dispatch(ToolCall(name="current_time", arguments={})).startswith("[error]")


def test_workspace_write_read_list(tmp_path):
    reg = ToolRegistry(
        [WriteFileTool(tmp_path), ReadFileTool(tmp_path), ListDirTool(tmp_path)]
    )
    reg.dispatch(ToolCall(name="write_file", arguments={"path": "a/b.txt", "content": "hi"}))
    assert reg.dispatch(ToolCall(name="read_file", arguments={"path": "a/b.txt"})) == "hi"
    listing = reg.dispatch(ToolCall(name="list_dir", arguments={"path": "a"}))
    assert "b.txt" in listing


def test_paths_are_not_sandboxed(tmp_path):
    # Relaxed sandbox: file tools can read/write outside the working dir.
    outside = tmp_path.parent / f"oshell-outside-{tmp_path.name}.txt"
    reg = ToolRegistry([WriteFileTool(tmp_path), ReadFileTool(tmp_path)])
    try:
        # Absolute path outside the workspace root writes fine.
        out = reg.dispatch(
            ToolCall(name="write_file", arguments={"path": str(outside), "content": "anywhere"})
        )
        assert not out.startswith("[error]") and str(outside) in out
        assert outside.read_text() == "anywhere"
        # And reads back via absolute path.
        back = reg.dispatch(ToolCall(name="read_file", arguments={"path": str(outside)}))
        assert back == "anywhere"
    finally:
        outside.unlink(missing_ok=True)


def test_tilde_path_expands(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))  # ~ -> tmp_path
    reg = ToolRegistry([WriteFileTool(tmp_path)])
    out = reg.dispatch(
        ToolCall(name="write_file", arguments={"path": "~/tilde.txt", "content": "hi"})
    )
    assert not out.startswith("[error]")
    assert (tmp_path / "tilde.txt").read_text() == "hi"


def test_tool_exception_is_caught():
    class Boom(CurrentTimeTool):
        name = "boom"

        def run(self, **kwargs):
            raise RuntimeError("kaboom")

    reg = ToolRegistry([Boom()])
    out = reg.dispatch(ToolCall(name="boom", arguments={}))
    assert out.startswith("[error]") and "kaboom" in out
