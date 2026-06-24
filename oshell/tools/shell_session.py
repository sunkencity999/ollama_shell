"""A long-lived shell so ``cd``, env vars, and activated venvs persist across
``run_command`` calls — on POSIX (``/bin/sh``) and Windows (PowerShell).

We keep the shell process alive, feed it commands on stdin, and learn when a
command finishes by echoing a unique **sentinel** + exit status after it. A
reader thread drains stdout (stderr merged) into a queue so reads honor a
deadline on every platform (``select`` doesn't work on Windows pipes).

The Windows/PowerShell path can't be exercised from a POSIX dev box, so callers
should health-probe a new session and fall back to one-shot execution if it
isn't responsive — :class:`ShellSession.healthy` exists for exactly that.
"""

from __future__ import annotations

import os
import platform
import queue
import shutil
import subprocess
import threading
import uuid
from pathlib import Path


class ShellSession:
    """One persistent shell. ``run`` is serialized by an internal lock.

    ``kind`` is "posix" or "powershell"; auto-detected from the platform.
    """

    def __init__(self, cwd: Path | str = ".", kind: str | None = None):
        self._cwd = str(Path(cwd).expanduser())
        self._kind = kind or ("powershell" if platform.system().lower() == "windows" else "posix")
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._reader: threading.Thread | None = None

    # ── shell-specific bits ───────────────────────────────────────────────────
    def _shell_argv(self) -> list[str]:
        if self._kind == "powershell":
            exe = shutil.which("pwsh") or shutil.which("powershell") or "powershell"
            return [exe, "-NoProfile", "-NoLogo"]
        return [os.environ.get("SHELL") or "/bin/sh"]

    def _setup_lines(self) -> list[str]:
        # Quiet PowerShell's interactive prompt so it doesn't pollute output.
        if self._kind == "powershell":
            return ['function prompt { "" }', '$ErrorActionPreference = "Continue"']
        return []

    def _marker_cmd(self, sentinel: str) -> str:
        if self._kind == "powershell":
            return f'Write-Output "{sentinel} $LASTEXITCODE"'
        return f'printf "%s %s\\n" "{sentinel}" "$?"'

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def _ensure(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        self._proc = subprocess.Popen(
            self._shell_argv(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=self._cwd,
        )
        self._queue = queue.Queue()
        self._reader = threading.Thread(target=self._read_loop, args=(self._proc,), daemon=True)
        self._reader.start()
        for line in self._setup_lines():
            assert self._proc.stdin is not None
            self._proc.stdin.write(line + "\n")
        if self._setup_lines():
            self._proc.stdin.flush()  # type: ignore[union-attr]

    def _read_loop(self, proc: subprocess.Popen) -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            self._queue.put(line.rstrip("\n"))
        self._queue.put(None)  # EOF: process exited

    def _terminate(self) -> None:
        """Kill the shell process. Caller must hold (or not need) the lock."""
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except OSError:  # pragma: no cover
                pass
        self._proc = None

    def close(self) -> None:
        with self._lock:
            self._terminate()

    def healthy(self, timeout: float = 6.0) -> bool:
        """Cheap probe: does a trivial command round-trip through the sentinel?"""
        try:
            out, _ = self.run("echo __oshell_probe__", timeout)
            return "__oshell_probe__" in out
        except Exception:
            return False

    # ── running commands ──────────────────────────────────────────────────────
    def run(self, command: str, timeout: float) -> tuple[str, int | None]:
        """Run ``command``; return (output, exit_code). On timeout the session is
        torn down (a hung command can't be isolated) and TimeoutError is raised."""
        import time

        with self._lock:
            self._ensure()
            proc = self._proc
            assert proc is not None and proc.stdin is not None
            while not self._queue.empty():  # drop stale output
                self._queue.get_nowait()

            sentinel = f"__OSHELL_{uuid.uuid4().hex}__"
            proc.stdin.write(f"{command}\n{self._marker_cmd(sentinel)}\n")
            proc.stdin.flush()

            out: list[str] = []
            exit_code: int | None = None
            deadline = time.monotonic() + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._terminate()  # hold the lock — don't call close()
                    raise TimeoutError(f"command timed out after {timeout:g}s")
                try:
                    line = self._queue.get(timeout=min(remaining, 0.5))
                except queue.Empty:
                    continue
                if line is None:  # shell died
                    self._proc = None
                    break
                if sentinel in line:
                    exit_code = _parse_exit(line, sentinel)
                    break
                if line.strip():  # skip blank prompt lines (PowerShell)
                    out.append(line)
            return "\n".join(out), exit_code


def _parse_exit(line: str, sentinel: str) -> int | None:
    """The sentinel line looks like 'SENTINEL <code>'."""
    tail = line.split(sentinel, 1)[1].strip()
    try:
        return int(tail.split()[0])
    except (ValueError, IndexError):
        return None
