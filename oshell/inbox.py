"""The inbox — where unattended runs leave their notes, and their questions.

Presence is the delivery, not the run. Every scheduled job writes one short
note here: what it looked at, what it found, and — when it wanted to *change*
something while nobody was watching — the exact action, queued as a
**proposal** for you to approve or dismiss. Nothing sensitive runs
unattended; it waits here.

Notes are plain JSON files in ``~/.oshell/inbox/``, one per run, so they're
greppable, syncable, and deletable with ``rm``. The TUI shows the unread count
in the status bar; ``oshell inbox`` lists, shows, approves, dismisses.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_DIR = "~/.oshell/inbox"
STATUSES = ("unread", "read", "approved", "dismissed")
_ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[a-z0-9][a-z0-9_-]*$")


@dataclass
class Proposal:
    """A sensitive tool call a job wanted to make and couldn't (unattended)."""

    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending | approved | dismissed | failed
    result: str = ""

    @property
    def summary(self) -> str:
        if self.tool == "run_command":
            return str(self.arguments.get("command", ""))
        args = ", ".join(f"{k}={v!r}" for k, v in self.arguments.items())
        return f"{self.tool}({args})"


@dataclass
class Note:
    id: str
    ts: float
    job: str
    title: str
    body: str  # markdown
    proposals: list[Proposal] = field(default_factory=list)
    status: str = "unread"
    tools_used: list[str] = field(default_factory=list)
    duration_s: float = 0.0
    error: str = ""

    @property
    def when(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(self.ts))

    @property
    def pending(self) -> list[Proposal]:
        return [p for p in self.proposals if p.status == "pending"]


def inbox_dir(directory: str | Path | None = None) -> Path:
    return Path(directory or DEFAULT_DIR).expanduser()


def new_id(job: str, ts: float | None = None) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(ts or time.time()))
    slug = re.sub(r"[^a-z0-9_-]+", "-", job.lower()).strip("-") or "job"
    return f"{stamp}-{slug}"


def _path(note_id: str, directory: str | Path | None = None) -> Path:
    return inbox_dir(directory) / f"{note_id}.json"


def save(note: Note, directory: str | Path | None = None) -> Path:
    d = inbox_dir(directory)
    d.mkdir(parents=True, exist_ok=True)
    p = _path(note.id, d)
    p.write_text(json.dumps(asdict(note), indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def add(
    job: str,
    title: str,
    body: str,
    proposals: list[Proposal] | None = None,
    directory: str | Path | None = None,
    **extra: Any,
) -> Note:
    ts = time.time()
    note_id = new_id(job, ts)
    # Two runs in the same second would collide; bump until unique.
    n = 1
    while _path(note_id, directory).exists():
        note_id = f"{new_id(job, ts)}-{n}"
        n += 1
    note = Note(
        id=note_id, ts=ts, job=job, title=title, body=body, proposals=proposals or [], **extra
    )
    save(note, directory)
    return note


def _load(p: Path) -> Note | None:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        data["proposals"] = [Proposal(**pr) for pr in data.get("proposals", [])]
        return Note(**data)
    except (OSError, ValueError, TypeError):
        return None


def get(note_id: str, directory: str | Path | None = None) -> Note | None:
    """Fetch by id or by unique prefix."""
    p = _path(note_id, directory)
    if p.is_file():
        return _load(p)
    matches = [n for n in list_notes(directory=directory) if n.id.startswith(note_id)]
    return matches[0] if len(matches) == 1 else None


def list_notes(
    status: str | None = None, job: str | None = None, directory: str | Path | None = None
) -> list[Note]:
    """Newest first."""
    d = inbox_dir(directory)
    if not d.is_dir():
        return []
    notes = [n for n in (_load(p) for p in d.glob("*.json")) if n is not None]
    if status:
        notes = [n for n in notes if n.status == status]
    if job:
        notes = [n for n in notes if n.job == job]
    return sorted(notes, key=lambda n: n.ts, reverse=True)


def unread_count(directory: str | Path | None = None) -> int:
    return len(list_notes(status="unread", directory=directory))


def pending_count(directory: str | Path | None = None) -> int:
    return sum(len(n.pending) for n in list_notes(directory=directory))


def latest_for_job(job: str, directory: str | Path | None = None) -> Note | None:
    notes = list_notes(job=job, directory=directory)
    return notes[0] if notes else None


def mark(note_id: str, status: str, directory: str | Path | None = None) -> Note:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {', '.join(STATUSES)}")
    note = get(note_id, directory)
    if note is None:
        raise FileNotFoundError(f"no inbox note {note_id}")
    note.status = status
    save(note, directory)
    return note


def remove(note_id: str, directory: str | Path | None = None) -> None:
    note = get(note_id, directory)
    if note is None:
        raise FileNotFoundError(f"no inbox note {note_id}")
    _path(note.id, directory).unlink()


def clear(directory: str | Path | None = None, keep_pending: bool = True) -> int:
    """Delete notes; by default keep ones that still have pending proposals."""
    n = 0
    for note in list_notes(directory=directory):
        if keep_pending and note.pending:
            continue
        _path(note.id, directory).unlink(missing_ok=True)
        n += 1
    return n


def render_markdown(note: Note) -> str:
    """The note as markdown (what the CLI and the TUI print)."""
    lines = [
        f"### {note.title}",
        f"*{note.job} · {note.when} · {note.status}*",
        "",
        note.body.strip(),
    ]
    if note.error:
        lines += ["", f"**error:** {note.error}"]
    if note.proposals:
        lines += ["", "**Proposed actions** (nothing ran):"]
        for i, p in enumerate(note.proposals, 1):
            tag = "" if p.status == "pending" else f" — _{p.status}_"
            lines.append(f"{i}. `{p.summary}`{tag}")
            if p.result:
                lines.append(f"   > {p.result.splitlines()[0][:160]}")
    if note.tools_used:
        lines += ["", f"_tools: {', '.join(note.tools_used)} · {note.duration_s:.0f}s_"]
    return "\n".join(lines)
