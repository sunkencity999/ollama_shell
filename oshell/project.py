"""Project awareness: know the repo you were launched in.

When oshell starts inside a git repository it should already know the answers
to "what is this project?" — branch, recent commits, what's dirty, the stack,
and the README's opening. This module builds that context block for the system
prompt. Everything is best-effort: any git hiccup degrades to less context,
never to an error.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_STACK_MARKERS = {
    "package.json": "Node.js",
    "pyproject.toml": "Python (pyproject)",
    "requirements.txt": "Python (requirements)",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "docker-compose.yml": "Docker Compose",
    "Makefile": "Make",
    "*.csproj": ".NET",
}
_README_CHARS = 1200
_GIT_TIMEOUT = 3.0  # seconds — never let a slow repo stall startup


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT,
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):  # pragma: no cover - defensive
        return None


def project_context(cwd: str | Path | None = None) -> str | None:
    """A compact project brief for the system prompt, or None outside a repo."""
    here = Path(cwd) if cwd else Path.cwd()
    root_s = _git(["rev-parse", "--show-toplevel"], here)
    if not root_s:
        return None
    root = Path(root_s)

    lines = [f"Repository: {root.name} (at {root})"]
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    if branch:
        lines.append(f"Branch: {branch}")

    stacks = sorted(
        label
        for marker, label in _STACK_MARKERS.items()
        if (next(root.glob(marker), None) if "*" in marker else (root / marker).exists())
    )
    if stacks:
        lines.append(f"Stack: {', '.join(stacks)}")

    status = _git(["status", "--porcelain"], root)
    if status:
        dirty = status.splitlines()
        shown = ", ".join(line[3:].strip() for line in dirty[:8])
        more = f" (+{len(dirty) - 8} more)" if len(dirty) > 8 else ""
        lines.append(f"Uncommitted changes ({len(dirty)}): {shown}{more}")

    log = _git(["log", "--oneline", "-5"], root)
    if log:
        lines.append("Recent commits:\n" + "\n".join(f"  {line}" for line in log.splitlines()))

    for name in ("README.md", "README.rst", "README"):
        readme = root / name
        if readme.is_file():
            try:
                head = readme.read_text(encoding="utf-8", errors="replace")[:_README_CHARS]
            except OSError:  # pragma: no cover - defensive
                break
            lines.append(f"README (start):\n{head}")
            break

    return "\n".join(lines)
