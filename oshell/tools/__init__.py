"""Tool registry assembly."""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..integrations.atlassian import confluence_configured, jira_configured
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
from .system import RunCommandTool, SystemInfoTool
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
        SystemInfoTool(),
        RunCommandTool(workspace, config.shell),
        ReadFileTool(workspace),
        WriteFileTool(workspace),
        ListDirTool(workspace),
        CreateDocumentTool(workspace),
        WebSearchTool(),
        FetchUrlTool(),
        AddKnowledgeTool(kb),
        SearchKnowledgeTool(kb),
    ]
    # Atlassian tools appear only when their server is configured (env or
    # config.local.json), so we don't advertise unusable tools to the model.
    atl = config.atlassian
    if jira_configured(atl):
        tools += [JiraSearchTool(atl), JiraGetIssueTool(atl)]
    if confluence_configured(atl):
        tools += [ConfluenceSearchTool(atl), ConfluenceGetPageTool(atl)]
    return ToolRegistry(tools, enabled=config.enabled_tools)
