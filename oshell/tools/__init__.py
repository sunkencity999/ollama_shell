"""Tool registry assembly."""

from __future__ import annotations

import os
from pathlib import Path

from ..config import Config
from ..providers.base import LLMProvider
from .atlassian import (
    ConfluenceGetPageTool,
    ConfluenceSearchTool,
    JiraGetIssueTool,
    JiraSearchTool,
)
from .base import Tool, ToolError, ToolRegistry
from .builtins import (
    CurrentTimeTool,
    ListDirTool,
    ListModelsTool,
    ReadFileTool,
    WriteFileTool,
)
from .documents import CreateDocumentTool
from .knowledge import AddKnowledgeTool, SearchKnowledgeTool, _SharedKB
from .web import FetchUrlTool, WebSearchTool

__all__ = ["Tool", "ToolError", "ToolRegistry", "default_registry"]


def default_registry(
    provider: LLMProvider, config: Config, workspace: Path | str = "."
) -> ToolRegistry:
    """Assemble the standard toolset. ``config.enabled_tools`` gates which are
    advertised to the model (``["*"]`` = all)."""
    kb = _SharedKB(config)  # one lazy knowledge base shared by both KB tools
    tools: list[Tool] = [
        CurrentTimeTool(),
        ListModelsTool(provider),
        ReadFileTool(workspace),
        WriteFileTool(workspace),
        ListDirTool(workspace),
        CreateDocumentTool(workspace),
        WebSearchTool(),
        FetchUrlTool(),
        AddKnowledgeTool(kb),
        SearchKnowledgeTool(kb),
    ]
    # Atlassian tools appear only when their server is configured, so we don't
    # advertise unusable tools to the model.
    if os.environ.get("JIRA_URL"):
        tools += [JiraSearchTool(), JiraGetIssueTool()]
    if os.environ.get("CONFLUENCE_URL"):
        tools += [ConfluenceSearchTool(), ConfluenceGetPageTool()]
    return ToolRegistry(tools, enabled=config.enabled_tools)
