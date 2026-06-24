"""Tests for terminal/computer-use tools (run_command, system_info)."""

from __future__ import annotations

import sys

from oshell.config import ShellConfig
from oshell.providers.base import ToolCall
from oshell.tools import ToolRegistry
from oshell.tools.system import RunCommandTool, SystemInfoTool, _total_ram_gb


def _py(code: str) -> str:
    # A portable shell command (works under sh and cmd.exe): invoke this Python.
    return f'{sys.executable} -c "{code}"'


def test_run_command_captures_output(tmp_path):
    reg = ToolRegistry([RunCommandTool(tmp_path)])
    out = reg.dispatch(
        ToolCall(name="run_command", arguments={"command": _py("print('hello-oshell')")})
    )
    assert "hello-oshell" in out
    assert "[exit 0]" in out


def test_run_command_reports_nonzero_exit(tmp_path):
    reg = ToolRegistry([RunCommandTool(tmp_path)])
    cmd = _py("import sys;sys.exit(2)")
    out = reg.dispatch(ToolCall(name="run_command", arguments={"command": cmd}))
    assert "[exit 2]" in out


def test_run_command_runs_in_workspace(tmp_path):
    (tmp_path / "marker.txt").write_text("x")
    reg = ToolRegistry([RunCommandTool(tmp_path)])
    # List the cwd contents; marker.txt should be visible (portable via Python).
    cmd = _py("import os;print('\\n'.join(os.listdir('.')))")
    out = reg.dispatch(ToolCall(name="run_command", arguments={"command": cmd}))
    assert "marker.txt" in out


def test_run_command_empty_is_error(tmp_path):
    reg = ToolRegistry([RunCommandTool(tmp_path)])
    out = reg.dispatch(ToolCall(name="run_command", arguments={"command": "   "}))
    assert out.startswith("[error]") and "empty" in out


def test_run_command_disabled(tmp_path):
    reg = ToolRegistry([RunCommandTool(tmp_path, ShellConfig(enabled=False))])
    out = reg.dispatch(ToolCall(name="run_command", arguments={"command": _py("print(1)")}))
    assert out.startswith("[error]") and "disabled" in out


def test_run_command_timeout(tmp_path):
    reg = ToolRegistry([RunCommandTool(tmp_path, ShellConfig(timeout=0.5))])
    out = reg.dispatch(
        ToolCall(name="run_command", arguments={"command": _py("import time;time.sleep(5)")})
    )
    assert out.startswith("[error]") and "timed out" in out


def test_run_command_truncates_output(tmp_path):
    reg = ToolRegistry([RunCommandTool(tmp_path, ShellConfig(max_output=50))])
    out = reg.dispatch(
        ToolCall(name="run_command", arguments={"command": _py("print('x'*500)")})
    )
    assert "[output truncated]" in out


def test_run_command_is_sensitive():
    assert RunCommandTool().sensitive is True
    assert RunCommandTool().local_only is True  # local, but flagged sensitive


def test_system_info_reports_platform():
    reg = ToolRegistry([SystemInfoTool()])
    out = reg.dispatch(ToolCall(name="system_info", arguments={}))
    assert "os:" in out and "arch:" in out and "cpu cores:" in out
    assert "python:" in out


def test_total_ram_is_positive_or_none():
    ram = _total_ram_gb()
    assert ram is None or ram > 0
