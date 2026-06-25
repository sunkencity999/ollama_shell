"""Persist and restore a conversation transcript across runs.

Lets the user close oshell and resume where they left off. The system message is
NOT persisted — it's rebuilt fresh on load from the current tools + memory — so a
resumed conversation reflects today's capabilities. Images are dropped to keep
the file small (the text of the exchange is what matters for continuity).
"""

from __future__ import annotations

import json
from pathlib import Path

from .providers.base import Message, ToolCall


def _to_dict(m: Message) -> dict:
    return {
        "role": m.role,
        "content": m.content,
        "tool_call_id": m.tool_call_id,
        "tool_calls": [
            {"name": tc.name, "arguments": tc.arguments, "id": tc.id} for tc in m.tool_calls
        ],
    }


def _from_dict(d: dict) -> Message:
    return Message(
        role=d.get("role", "user"),
        content=d.get("content", ""),
        tool_call_id=d.get("tool_call_id"),
        tool_calls=[
            ToolCall(name=t["name"], arguments=t.get("arguments", {}), id=t.get("id"))
            for t in d.get("tool_calls", [])
        ],
    )


def save_session(messages: list[Message], path: str | Path, max_messages: int = 200) -> None:
    """Write the non-system messages (most recent ``max_messages``) to ``path``."""
    keep = [m for m in messages if m.role != "system"][-max_messages:]
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"messages": [_to_dict(m) for m in keep]}, indent=2), encoding="utf-8")


def load_session(path: str | Path) -> list[Message]:
    """Read persisted messages (excluding system). Returns [] if none/invalid."""
    p = Path(path).expanduser()
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):  # pragma: no cover - defensive
        return []
    return [_from_dict(d) for d in data.get("messages", []) if d.get("role") != "system"]


def clear_session(path: str | Path) -> None:
    Path(path).expanduser().unlink(missing_ok=True)
