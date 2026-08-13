"""File checkpoints: a safety net under the model's pen.

Before a file-mutating tool runs, the target's current state is snapshotted to
``~/.oshell/checkpoints`` — including the fact that it *didn't exist*, so undo
can delete a file the model shouldn't have created. ``/undo`` restores the most
recent checkpoint. Local models fumble more often than frontier ones; the
rewind is what makes letting them write files feel safe.
"""

from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path

DEFAULT_DIR = "~/.oshell/checkpoints"
MAX_KEPT = 20

# Tools that mutate a file, and the argument naming the target path.
FILE_WRITERS = {"write_file": "path", "create_document": "path"}


def _dir(directory: str | Path = DEFAULT_DIR) -> Path:
    return Path(directory).expanduser()


def before_tool(name: str, arguments: dict, directory: str | Path = DEFAULT_DIR) -> str | None:
    """Snapshot the file a mutating tool is about to touch.

    Returns the checkpoint id, or None when the tool doesn't write files (or
    the path argument is missing). Never raises — a failed snapshot must not
    block the tool.
    """
    param = FILE_WRITERS.get(name)
    if param is None:
        return None
    raw = arguments.get(param)
    if not raw or not isinstance(raw, str):
        return None
    try:
        target = Path(raw).expanduser()
        if not target.is_absolute():
            target = Path.cwd() / target
        # time_ns keeps ids sortable even for several snapshots per second
        # (undo_last must consume strictly newest-first).
        cid = f"{time.time_ns():019d}-{uuid.uuid4().hex[:6]}"
        cdir = _dir(directory) / cid
        cdir.mkdir(parents=True, exist_ok=True)
        existed = target.is_file()
        if existed:
            shutil.copy2(target, cdir / "content")
        (cdir / "manifest.json").write_text(
            json.dumps({"path": str(target), "existed": existed, "tool": name}),
            encoding="utf-8",
        )
        _prune(directory)
        return cid
    except Exception:  # pragma: no cover - snapshot is best-effort by contract
        return None


def _prune(directory: str | Path = DEFAULT_DIR) -> None:
    kept = sorted(d for d in _dir(directory).iterdir() if d.is_dir())
    for stale in kept[:-MAX_KEPT]:
        shutil.rmtree(stale, ignore_errors=True)


def undo_last(directory: str | Path = DEFAULT_DIR) -> str:
    """Restore the most recent checkpoint. Returns a human-readable summary.

    Raises FileNotFoundError when there's nothing to undo.
    """
    d = _dir(directory)
    checkpoints = sorted(x for x in d.iterdir() if x.is_dir()) if d.is_dir() else []
    if not checkpoints:
        raise FileNotFoundError("nothing to undo — no checkpoints yet")
    latest = checkpoints[-1]
    manifest = json.loads((latest / "manifest.json").read_text(encoding="utf-8"))
    target = Path(manifest["path"])
    if manifest["existed"]:
        shutil.copy2(latest / "content", target)
        outcome = f"restored {target} to its pre-{manifest['tool']} contents"
    else:
        target.unlink(missing_ok=True)
        outcome = f"removed {target} (it did not exist before {manifest['tool']})"
    shutil.rmtree(latest, ignore_errors=True)
    return outcome
