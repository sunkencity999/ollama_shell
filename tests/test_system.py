"""Tests for terminal/computer-use tools (run_command, system_info)."""

from __future__ import annotations

import sys

from oshell.config import ShellConfig
from oshell.providers.base import ToolCall
from oshell.tools import ToolRegistry
from oshell.tools.system import RunCommandTool, SystemInfoTool, _total_ram_gb, shell_invocation


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


def test_shell_invocation_posix_uses_sh():
    for sysname in ("Linux", "Darwin"):
        args, use_shell = shell_invocation("uname -a", system=sysname)
        assert args == "uname -a" and use_shell is True


def test_shell_invocation_windows_uses_powershell():
    args, use_shell = shell_invocation("Get-Process", system="Windows")
    assert use_shell is False
    assert isinstance(args, list)
    assert args[0].lower().endswith(("powershell", "powershell.exe", "pwsh", "pwsh.exe"))
    assert "-Command" in args and args[-1] == "Get-Process"
    assert "-NoProfile" in args


def test_shell_invocation_windows_cmd_override():
    args, use_shell = shell_invocation("dir", system="Windows", windows_shell="cmd")
    assert args == "dir" and use_shell is True  # cmd.exe via the shell


# ── persistent shell (POSIX) ────────────────────────────────────────────────
import sys as _sys  # noqa: E402

import pytest  # noqa: E402

posix_only = pytest.mark.skipif(_sys.platform == "win32", reason="persistent shell is POSIX-only")


@posix_only
def test_exit_line_parsing():
    from oshell.tools.shell_session import _parse_exit

    assert _parse_exit("SENT 0", "SENT") == 0
    assert _parse_exit("noise SENT 3", "SENT") == 3
    assert _parse_exit("SENT notanumber", "SENT") is None


@posix_only
def test_persistent_cwd_and_env_persist(tmp_path):
    from oshell.tools.shell_session import ShellSession

    (tmp_path / "sub").mkdir()
    s = ShellSession(tmp_path)
    try:
        out, code = s.run("cd sub && echo in-sub", 10)
        assert code == 0 and "in-sub" in out
        # cwd persisted from the previous command:
        out, code = s.run("basename $(pwd)", 10)
        assert out.strip() == "sub"
        # env var set earlier is still present:
        s.run("export OSHELL_TESTVAR=persisted", 10)
        out, _ = s.run("echo $OSHELL_TESTVAR", 10)
        assert out.strip() == "persisted"
    finally:
        s.close()


@posix_only
def test_persistent_run_command_tool_keeps_cwd(tmp_path):
    from oshell.config import ShellConfig

    (tmp_path / "deep").mkdir()
    tool = RunCommandTool(tmp_path, ShellConfig(persistent=True))
    tool.run(command="cd deep")
    out = tool.run(command="basename $(pwd)")
    assert "deep" in out and "[exit 0]" in out


def test_session_kind_selected_by_platform(monkeypatch):
    import oshell.tools.shell_session as ss

    monkeypatch.setattr(ss.platform, "system", lambda: "Windows")
    assert ss.ShellSession()._kind == "powershell"
    monkeypatch.setattr(ss.platform, "system", lambda: "Linux")
    assert ss.ShellSession()._kind == "posix"


def test_powershell_session_construction():
    from oshell.tools.shell_session import ShellSession

    s = ShellSession(kind="powershell")
    argv = s._shell_argv()
    assert argv[0].lower().endswith(("powershell", "powershell.exe", "pwsh", "pwsh.exe"))
    assert "-NoProfile" in argv
    marker = s._marker_cmd("SENT")
    assert "Write-Output" in marker and "SENT" in marker and "LASTEXITCODE" in marker
    assert s._setup_lines()  # quiets the PowerShell prompt


def test_run_command_falls_back_when_session_unhealthy(tmp_path, monkeypatch):
    # Simulate a persistent shell that won't start (e.g. PowerShell-over-pipe on
    # an environment where it doesn't stream): the tool must fall back to one-shot.
    import oshell.tools.shell_session as ss

    monkeypatch.setattr(ss.ShellSession, "healthy", lambda self, timeout=6.0: False)
    tool = RunCommandTool(tmp_path, ShellConfig(persistent=True))
    out = tool.run(command=_py("print('fallback-ok')"))
    assert "fallback-ok" in out and "[exit 0]" in out
    assert tool._session_failed is True  # latched -> stays on one-shot


def test_session_healthy_probe_posix(tmp_path):
    if _sys.platform == "win32":  # pragma: no cover
        return
    from oshell.tools.shell_session import ShellSession

    s = ShellSession(tmp_path, kind="posix")
    try:
        assert s.healthy() is True
    finally:
        s.close()


@posix_only
def test_persistent_timeout_raises(tmp_path):
    from oshell.config import ShellConfig

    reg = ToolRegistry([RunCommandTool(tmp_path, ShellConfig(persistent=True, timeout=0.5))])
    out = reg.dispatch(ToolCall(name="run_command", arguments={"command": "sleep 5"}))
    assert out.startswith("[error]") and "timed out" in out
