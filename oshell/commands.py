"""User-defined slash commands from ``~/.oshell/commands/*.md``.

Drop ``standup.md`` in that directory and ``/standup`` exists in the chat REPL
and the TUI. The file's body is the prompt; ``$ARGS`` (or ``$1``..``$9``) is
replaced with whatever follows the command. Zero config, zero registration —
the filesystem is the registry.
"""

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_DIR = "~/.oshell/commands"
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def commands_dir(directory: str | Path | None = None) -> Path:
    # DEFAULT_DIR is looked up at call time so tests (and adventurous users)
    # can repoint it on the module.
    return Path(directory or DEFAULT_DIR).expanduser()


def list_commands(directory: str | Path | None = None) -> dict[str, Path]:
    """name -> file for every valid custom command."""
    d = commands_dir(directory)
    if not d.is_dir():
        return {}
    return {
        f.stem: f for f in sorted(d.glob("*.md")) if _NAME_RE.match(f.stem)
    }


def render(name: str, args: str = "", directory: str | Path | None = None) -> str | None:
    """The prompt for /<name> with arguments substituted, or None if unknown.

    ``$ARGS`` gets the whole argument string; ``$1``..``$9`` get whitespace-split
    words (missing ones become empty). A file with no placeholder still works —
    the args are appended on their own line so nothing the user typed is lost.
    """
    path = list_commands(directory).get(name)
    if path is None:
        return None
    try:
        body = path.read_text(encoding="utf-8").strip()
    except OSError:  # pragma: no cover - defensive
        return None
    words = args.split()
    had_placeholder = "$ARGS" in body or re.search(r"\$[1-9]", body)
    body = body.replace("$ARGS", args)
    for i in range(9, 0, -1):  # $9 before $1 so $1 doesn't eat $12's prefix
        body = body.replace(f"${i}", words[i - 1] if i <= len(words) else "")
    if args and not had_placeholder:
        body = f"{body}\n\n{args}"
    return body
