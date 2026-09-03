"""File watches — a job that fires when something *happens*, not on a clock.

"Tell me when the release build finishes" shouldn't cost a model call every
hour. A watch job keeps a tiny snapshot of a path (name → mtime, size) in
``~/.oshell/jobs/<name>.watch.json``; each minute-tick rescans — a directory
listing, microseconds — and only when files were created, modified or deleted
(and have **settled**: unchanged for ``settle`` seconds, so a build still
writing isn't reported as finished) does the agent wake, with the change list
in its prompt.

No inotify/FSEvents daemon: the once-a-minute tick is already running, and a
minute of latency is fine for "the download finished". Cross-platform for free.
"""

from __future__ import annotations

import fnmatch
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

EVENTS = ("any", "created", "modified", "deleted")
MAX_FILES = 5000  # a watch on a huge tree is a mistake; cap the scan


@dataclass
class WatchSpec:
    path: str
    pattern: str = "*"
    event: str = "any"
    settle: int = 10  # seconds a file must be unchanged before it counts
    recursive: bool = False

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("a watch needs a path")
        if self.event not in EVENTS:
            raise ValueError(f"event must be one of {', '.join(EVENTS)}")
        if self.settle < 0:
            raise ValueError("settle must be ≥ 0")

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WatchSpec:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> dict[str, Any]:
        return vars(self).copy()

    def describe(self) -> str:
        pat = "" if self.pattern == "*" else f" {self.pattern}"
        ev = "" if self.event == "any" else f" ({self.event})"
        return f"watch {self.path}{pat}{ev}"


@dataclass
class Change:
    kind: str  # created | modified | deleted
    path: str
    size: int = 0


Snapshot = dict[str, list[float]]  # relative path → [mtime, size]


def scan(spec: WatchSpec) -> Snapshot:
    """The current state of the watched path (files only)."""
    root = Path(spec.path).expanduser()
    snap: Snapshot = {}
    if root.is_file():
        st = root.stat()
        return {root.name: [st.st_mtime, st.st_size]}
    if not root.is_dir():
        return snap
    it = root.rglob(spec.pattern) if spec.recursive else root.glob(spec.pattern)
    for i, p in enumerate(it):
        if i >= MAX_FILES:
            break
        try:
            if not p.is_file():
                continue
            st = p.stat()
        except OSError:
            continue
        snap[str(p.relative_to(root))] = [st.st_mtime, st.st_size]
    return snap


def diff(
    prev: Snapshot, cur: Snapshot, spec: WatchSpec, now: float | None = None
) -> tuple[list[Change], Snapshot]:
    """Changes between snapshots honoring ``event`` and ``settle``.

    Returns (changes, snapshot_to_store): files that changed but haven't settled
    keep their *previous* entry in the stored snapshot, so they're reported on a
    later tick once they stop changing.
    """
    now = now or time.time()
    changes: list[Change] = []
    store: Snapshot = dict(cur)
    for rel, (mtime, size) in cur.items():
        settled = (now - mtime) >= spec.settle
        if rel not in prev:
            if settled:
                changes.append(Change("created", rel, int(size)))
            else:
                store.pop(rel, None)  # still being written: pretend we haven't seen it
        elif prev[rel] != [mtime, size]:
            if settled:
                changes.append(Change("modified", rel, int(size)))
            else:
                store[rel] = prev[rel]
    for rel in prev:
        if rel not in cur:
            changes.append(Change("deleted", rel))
    if spec.event != "any":
        changes = [c for c in changes if c.kind == spec.event]
    if spec.pattern != "*":
        changes = [c for c in changes if fnmatch.fnmatch(os.path.basename(c.path), spec.pattern)]
    return changes, store


def snapshot_path(name: str, directory: str | Path) -> Path:
    return Path(directory).expanduser() / f"{name}.watch.json"


def load_snapshot(name: str, directory: str | Path) -> Snapshot | None:
    p = snapshot_path(name, directory)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return {k: list(v) for k, v in data.items()} if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def save_snapshot(name: str, directory: str | Path, snap: Snapshot) -> None:
    p = snapshot_path(name, directory)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(snap), encoding="utf-8")


def check(
    name: str, spec: WatchSpec, directory: str | Path, now: float | None = None
) -> list[Change]:
    """Rescan and return settled changes since the stored snapshot.

    The first call establishes the baseline and reports nothing — a new watch
    shouldn't fire on everything that already exists.
    """
    now = now or time.time()
    cur = scan(spec)
    prev = load_snapshot(name, directory)
    if prev is None:
        save_snapshot(name, directory, cur)
        return []
    changes, store = diff(prev, cur, spec, now)
    save_snapshot(name, directory, store)
    return changes


def describe_changes(changes: list[Change], limit: int = 30) -> str:
    def human(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024 or unit == "TB":
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} TB"

    lines = []
    for c in changes[:limit]:
        size = f" ({human(c.size)})" if c.kind != "deleted" else ""
        lines.append(f"- {c.kind}: {c.path}{size}")
    if len(changes) > limit:
        lines.append(f"- … and {len(changes) - limit} more")
    return "\n".join(lines)


@dataclass
class WatchResult:
    changes: list[Change] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.changes)
