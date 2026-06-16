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


def test_workspace_escape_blocked(tmp_path):
    reg = ToolRegistry([ReadFileTool(tmp_path)])
    out = reg.dispatch(ToolCall(name="read_file", arguments={"path": "../../etc/passwd"}))
    assert out.startswith("[error]")
    assert "escapes" in out


def test_tool_exception_is_caught():
    class Boom(CurrentTimeTool):
        name = "boom"

        def run(self, **kwargs):
            raise RuntimeError("kaboom")

    reg = ToolRegistry([Boom()])
    out = reg.dispatch(ToolCall(name="boom", arguments={}))
    assert out.startswith("[error]") and "kaboom" in out
