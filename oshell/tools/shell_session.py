"""A long-lived POSIX shell so ``cd``, env vars, and activated venvs persist
across ``run_command`` calls.

We keep a ``/bin/sh`` process alive, feed it commands on stdin, and learn when a
command finishes by echoing a unique **sentinel** + ``$?`` after it. A reader
thread drains stdout (stderr merged in) into a queue so reads can honor a
deadline on every platform (``select`` doesn't work on Windows pipes — but this
session is POSIX-only anyway; Windows uses one-shot PowerShell).
"""

from __future__ import annotations

import os
import queue
import subprocess
import threading
import uuid
from pathlib import Path


class ShellSession:
    """One persistent ``/bin/sh``. ``run`` is serialized by an internal lock."""

    def __init__(self, cwd: Path | str = "."):
        self._cwd = str(Path(cwd).expanduser())
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._reader: threading.Thread | None = None

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def _ensure(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        shell = os.environ.get("SHELL") or "/bin/sh"
        self._proc = subprocess.Popen(
            [shell],
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

    # ── running commands ──────────────────────────────────────────────────────
    def run(self, command: str, timeout: float) -> tuple[str, int | None]:
        """Run ``command`` in the persistent shell; return (output, exit_code).

        On timeout the session is restarted (a hung command can't be isolated in
        a shared shell) and a TimeoutError is raised.
        """
        import time

        with self._lock:
            self._ensure()
            proc = self._proc
            assert proc is not None and proc.stdin is not None
            # Drain any stale output before issuing the new command.
            while not self._queue.empty():
                self._queue.get_nowait()

            sentinel = f"__OSHELL_{uuid.uuid4().hex}__"
            proc.stdin.write(f"{command}\n")
            proc.stdin.write(f'printf "%s %s\\n" "{sentinel}" "$?"\n')
            proc.stdin.flush()

            out: list[str] = []
            exit_code: int | None = None
            deadline = time.monotonic() + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._terminate()  # we already hold the lock — don't call close()
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
                out.append(line)
            return "\n".join(out), exit_code


def _parse_exit(line: str, sentinel: str) -> int | None:
    """The sentinel line looks like 'SENTINEL <code>'."""
    tail = line.split(sentinel, 1)[1].strip()
    try:
        return int(tail.split()[0])
    except (ValueError, IndexError):
        return None
