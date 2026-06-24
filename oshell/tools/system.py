"""Terminal / computer-use tools: run shell commands and report system info.

``run_command`` is what makes this an *agentic* shell — the model can inspect
the machine, run scripts, drive git/build tools, etc. It executes through the
platform's own shell (``/bin/sh`` on macOS/Linux, ``cmd.exe`` on Windows), so it
is cross-platform. Per the project's chosen policy it runs with full autonomy
(no per-command confirmation); every call and its output are shown inline in the
TUI, so the user always sees exactly what ran.

``system_info`` is a safe, read-only summary (OS, arch, CPU, cores, RAM) using
only the standard library — handy for "what hardware am I on?" without a shell.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..config import ShellConfig
from .base import Tool, ToolError


def shell_invocation(
    command: str, system: str | None = None, windows_shell: str = "auto"
) -> tuple[str | list[str], bool]:
    """Return ``(args, use_shell)`` for running ``command`` on this platform.

    * Windows → PowerShell (``pwsh`` if present, else ``powershell``) via an
      explicit argv, unless ``windows_shell == "cmd"`` (then cmd.exe via shell).
    * POSIX (macOS/Linux) → the command string run through ``/bin/sh``.

    Factored out (and platform-parameterized) so the choice is unit-testable
    without actually being on Windows.
    """
    system = (system or platform.system()).lower()
    if system == "windows" and windows_shell != "cmd":
        if windows_shell in ("auto", "pwsh"):
            exe = shutil.which("pwsh") or shutil.which("powershell") or "powershell"
        else:  # "powershell"
            exe = shutil.which("powershell") or "powershell"
        return ([exe, "-NoProfile", "-NonInteractive", "-Command", command], False)
    # POSIX sh, or Windows cmd.exe when forced — both via the shell.
    return (command, True)


class RunCommandTool(Tool):
    name = "run_command"
    description = (
        "Run a shell command on the local machine and return its combined "
        "stdout/stderr and exit code. Use for system inspection (e.g. sysctl, "
        "lscpu, uname, df), file operations, git, builds, and scripts. The "
        "working directory is the workspace. Commands run via the platform shell."
    )
    local_only = True  # executes locally; never sends data to a remote
    sensitive = True  # can change the system / run arbitrary code
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command line to run"},
            "timeout": {"type": "integer", "description": "Optional per-command timeout (seconds)"},
        },
        "required": ["command"],
    }

    def __init__(self, workspace: Path | str = ".", config: ShellConfig | None = None):
        self.workspace = str(Path(workspace).expanduser())
        self.config = config or ShellConfig()

    def run(self, command: str = "", timeout: int | None = None, **_: Any) -> str:
        if not self.config.enabled:
            raise ToolError("command execution is disabled (enable shell in config)")
        if not command.strip():
            raise ToolError("command must not be empty")
        try:
            secs = float(timeout) if timeout else self.config.timeout
        except (TypeError, ValueError):
            secs = self.config.timeout
        args, use_shell = shell_invocation(command, windows_shell=self.config.windows_shell)
        try:
            proc = subprocess.run(
                args,
                shell=use_shell,  # PowerShell argv on Windows; sh on macOS/Linux
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=secs,
            )
        except subprocess.TimeoutExpired:
            raise ToolError(f"command timed out after {secs:g}s: {command}") from None
        except Exception as exc:  # pragma: no cover - spawn failures are rare
            raise ToolError(f"could not run command: {exc}") from exc

        out = (proc.stdout or "") + (proc.stderr or "")
        cap = self.config.max_output
        if len(out) > cap:
            out = out[:cap].rstrip() + "\n…[output truncated]"
        body = out.strip() or "(no output)"
        return f"$ {command}\n[exit {proc.returncode}]\n{body}"


class SystemInfoTool(Tool):
    name = "system_info"
    description = (
        "Report this machine's OS, architecture, CPU, logical core count, total "
        "RAM, and Python version. Read-only; no shell needed."
    )
    local_only = True
    parameters = {"type": "object", "properties": {}}

    def run(self, **_: Any) -> str:
        ram = _total_ram_gb()
        lines = [
            f"os:        {platform.platform()}",
            f"system:    {platform.system()} {platform.release()}",
            f"arch:      {platform.machine()}",
            f"processor: {platform.processor() or '(unknown)'}",
            f"cpu cores: {os.cpu_count()} logical",
            f"ram:       {f'{ram} GB' if ram else '(unknown)'}",
            f"python:    {platform.python_version()}",
        ]
        return "\n".join(lines)


def _total_ram_gb() -> float | None:
    """Best-effort total physical RAM in GB, stdlib only, cross-platform."""
    try:  # POSIX (Linux + macOS expose these)
        names = os.sysconf_names  # type: ignore[attr-defined]
        if "SC_PHYS_PAGES" in names and "SC_PAGE_SIZE" in names:
            total = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
            return round(total / 1e9, 1)
    except (AttributeError, ValueError, OSError):
        pass
    try:  # Windows
        import ctypes

        class _MemStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = _MemStatus()
        stat.dwLength = ctypes.sizeof(stat)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]
        return round(stat.ullTotalPhys / 1e9, 1)
    except Exception:  # pragma: no cover - non-Windows / no ctypes
        return None
