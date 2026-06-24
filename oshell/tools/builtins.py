"""Safe, dependency-light built-in tools.

These ship in the core install. Filesystem tools are confined to a workspace
root so the model cannot read or write outside it.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from ..providers.base import LLMProvider
from .base import Tool, ToolError

_MAX_READ_BYTES = 200_000


class CurrentTimeTool(Tool):
    name = "current_time"
    description = "Return the current local date and time (ISO 8601)."
    parameters = {"type": "object", "properties": {}}

    def run(self, **_: Any) -> str:
        return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


class ListModelsTool(Tool):
    name = "list_models"
    description = "List the language models available on the configured backend."
    parameters = {"type": "object", "properties": {}}

    def __init__(self, provider: LLMProvider):
        self._provider = provider

    def run(self, **_: Any) -> str:
        models = self._provider.list_models()
        return "\n".join(models) if models else "(no models found)"


class _PathTool(Tool):
    """Base for filesystem tools.

    Relative paths resolve against the working directory; absolute paths and
    ``~`` are honored. There is no sandbox — these tools can read/write anywhere
    the user can (consistent with run_command's full autonomy).
    """

    def __init__(self, root: Path | str = "."):
        self.root = Path(root).resolve()

    def _resolve(self, raw: str) -> Path:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = self.root / p
        return p.resolve()

    def _display(self, target: Path) -> str:
        """Show a path relative to the working dir when it's under it, else absolute."""
        try:
            return str(target.relative_to(self.root))
        except ValueError:
            return str(target)


class ReadFileTool(_PathTool):
    name = "read_file"
    description = "Read a UTF-8 text file and return its contents."
    local_only = True
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path — absolute, ~, or relative to the working dir",
            }
        },
        "required": ["path"],
    }

    def run(self, path: str = "", **_: Any) -> str:
        target = self._resolve(path)
        if not target.is_file():
            raise ToolError(f"no such file: {path}")
        data = target.read_bytes()[:_MAX_READ_BYTES]
        return data.decode("utf-8", errors="replace")


class WriteFileTool(_PathTool):
    name = "write_file"
    description = "Create or overwrite a UTF-8 text file at any path on the system."
    local_only = True
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Destination — absolute, ~, or relative to the working dir",
            },
            "content": {"type": "string", "description": "Full file contents to write"},
        },
        "required": ["path", "content"],
    }

    def run(self, path: str = "", content: str = "", **_: Any) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"wrote {len(content)} bytes to {self._display(target)}"


class ListDirTool(_PathTool):
    name = "list_dir"
    description = "List files and directories at a path (absolute, ~, or relative)."
    local_only = True
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory — absolute, ~, or relative (default '.')",
            }
        },
    }

    def run(self, path: str = ".", **_: Any) -> str:
        target = self._resolve(path)
        if not target.is_dir():
            raise ToolError(f"not a directory: {path}")
        entries = sorted(
            (("d " if p.is_dir() else "f ") + p.name) for p in target.iterdir()
        )
        return "\n".join(entries) or "(empty)"
