"""Named, listable conversation sessions (``~/.oshell/sessions/*.json``).

The TUI keeps its single ``last_session.json`` auto-resume (oshell/session.py);
this store is for the CLI's daily-driver flow: every chat autosaves under a
timestamped id, ``oshell sessions`` lists them, ``oshell chat --resume [ID]``
picks one up. A session file is the session.py payload plus a small metadata
header, so both readers stay simple.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .providers.base import Message
from .session import _from_dict, _to_dict

DEFAULT_DIR = "~/.oshell/sessions"
_TITLE_LEN = 60


def _dir(directory: str | Path = DEFAULT_DIR) -> Path:
    return Path(directory).expanduser()


def new_id() -> str:
    """A sortable, human-readable session id (creation time)."""
    return time.strftime("%Y%m%d-%H%M%S")


def _title(messages: list[Message]) -> str:
    """First line of the first user message — good enough to recognize later."""
    for m in messages:
        if m.role == "user" and m.content.strip():
            line = m.content.strip().splitlines()[0]
            return line[:_TITLE_LEN] + ("…" if len(line) > _TITLE_LEN else "")
    return "(empty)"


def save(
    messages: list[Message],
    *,
    sid: str,
    model: str,
    directory: str | Path = DEFAULT_DIR,
    max_messages: int = 200,
) -> Path:
    """Write/overwrite one session. Returns the file path."""
    keep = [m for m in messages if m.role != "system"][-max_messages:]
    d = _dir(directory)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{sid}.json"
    payload = {
        "id": sid,
        "title": _title(keep),
        "model": model,
        "updated": time.strftime("%Y-%m-%d %H:%M"),
        "messages": [_to_dict(m) for m in keep],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def list_sessions(directory: str | Path = DEFAULT_DIR) -> list[dict]:
    """Metadata for every stored session, newest first (no message bodies)."""
    out = []
    for f in sorted(_dir(directory).glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):  # pragma: no cover - defensive
            continue
        out.append(
            {
                "id": data.get("id", f.stem),
                "title": data.get("title", ""),
                "model": data.get("model", ""),
                "updated": data.get("updated", ""),
                "messages": len(data.get("messages", [])),
            }
        )
    return out


def load(sid: str, directory: str | Path = DEFAULT_DIR) -> tuple[dict, list[Message]]:
    """Load a session by id — or by unambiguous id prefix.

    Raises FileNotFoundError (no match) or ValueError (ambiguous prefix).
    """
    d = _dir(directory)
    path = d / f"{sid}.json"
    if not path.is_file():
        matches = sorted(d.glob(f"{sid}*.json"))
        if not matches:
            raise FileNotFoundError(f"no session matching '{sid}'")
        if len(matches) > 1:
            names = ", ".join(m.stem for m in matches[:5])
            raise ValueError(f"'{sid}' is ambiguous: {names}")
        path = matches[0]
    data = json.loads(path.read_text(encoding="utf-8"))
    meta = {k: v for k, v in data.items() if k != "messages"}
    meta.setdefault("id", path.stem)
    msgs = [_from_dict(m) for m in data.get("messages", []) if m.get("role") != "system"]
    return meta, msgs


def latest_id(directory: str | Path = DEFAULT_DIR) -> str | None:
    """The most recent session id, or None when the store is empty."""
    sessions = list_sessions(directory)
    return sessions[0]["id"] if sessions else None


def delete(sid: str, directory: str | Path = DEFAULT_DIR) -> None:
    path = _dir(directory) / f"{sid}.json"
    if not path.is_file():
        raise FileNotFoundError(f"no session '{sid}'")
    path.unlink()
