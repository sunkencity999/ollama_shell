"""Tool registry assembly."""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..providers.base import LLMProvider
from .base import Tool, ToolError, ToolRegistry
from .builtins import (
    CurrentTimeTool,
    ListDirTool,
    ListModelsTool,
    ReadFileTool,
    WriteFileTool,
)
from .web import WebSearchTool

__all__ = ["Tool", "ToolError", "ToolRegistry", "default_registry"]


def default_registry(
    provider: LLMProvider, config: Config, workspace: Path | str = "."
) -> ToolRegistry:
    """Assemble the standard toolset. ``config.enabled_tools`` gates which are
    advertised to the model (``["*"]`` = all)."""
    tools: list[Tool] = [
        CurrentTimeTool(),
        ListModelsTool(provider),
        ReadFileTool(workspace),
        WriteFileTool(workspace),
        ListDirTool(workspace),
        WebSearchTool(),
    ]
    return ToolRegistry(tools, enabled=config.enabled_tools)
