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
from .gui import gui_tools
from .knowledge import AddKnowledgeTool, SearchKnowledgeTool, _SharedKB
from .system import RunCommandTool, SystemInfoTool
from .web import FetchUrlTool, WebSearchTool

__all__ = ["Tool", "ToolError", "ToolRegistry", "default_registry"]


def default_registry(
    provider: LLMProvider, config: Config, workspace: Path | str = ".", model: str | None = None
) -> ToolRegistry:
    """Assemble the standard toolset. ``config.enabled_tools`` gates which are
    advertised to the model (``["*"]`` = all). GUI computer-use tools are added
    only when opted in *and* the active model is vision-capable."""
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

    # GUI computer-use: opt-in, and only for a vision+tools-capable model (it
    # must see screenshots and call action tools). Terminal stays the default.
    if config.gui.enabled and model and _gui_capable(provider, model):
        tools += gui_tools()
    return ToolRegistry(tools, enabled=config.enabled_tools)


def _gui_capable(provider: LLMProvider, model: str) -> bool:
    try:
        caps = provider.capabilities(model)
    except Exception:
        return False
    return "vision" in caps and "tools" in caps
