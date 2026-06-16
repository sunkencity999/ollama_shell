"""Tool abstraction and registry — the contract between the model and the host.

A ``Tool`` is the unit of capability in the reimagined shell. Each one declares
a JSON-Schema for its parameters (the same shape Ollama/OpenAI expect for
function calling) and a ``run`` method. The ``ToolRegistry`` exposes the set of
tools to the provider and dispatches the model's tool calls back to Python.

This is deliberately the same mental model as MCP: typed, discoverable
capabilities a host offers to a model. Local tools live here; remote MCP
servers can be adapted into ``Tool`` instances without the agent loop caring.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from ..providers.base import ToolCall


class Tool(ABC):
    """A single capability the model may invoke."""

    name: str
    description: str
    # JSON-Schema object describing accepted arguments.
    parameters: dict[str, Any] = {"type": "object", "properties": {}}

    # Set False for tools that touch the network/filesystem so a future policy
    # layer (or the privacy banner) can flag them. Pure/read-only -> True.
    local_only: bool = True

    @abstractmethod
    def run(self, **kwargs: Any) -> str:
        """Execute the tool and return a string result for the model to read."""

    def spec(self) -> dict[str, Any]:
        """The function-calling schema entry for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolError(Exception):
    """Raised inside a tool to signal a recoverable failure to the model."""


class ToolRegistry:
    """Holds tools, advertises their specs, and dispatches calls."""

    def __init__(self, tools: list[Tool] | None = None, enabled: list[str] | None = None):
        self._tools: dict[str, Tool] = {}
        self._enabled = enabled or ["*"]
        for t in tools or []:
            self.register(t)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def _is_enabled(self, name: str) -> bool:
        return "*" in self._enabled or name in self._enabled

    def active(self) -> list[Tool]:
        return [t for n, t in self._tools.items() if self._is_enabled(n)]

    def specs(self) -> list[dict[str, Any]]:
        """The ``tools`` array to hand the provider (empty if none active)."""
        return [t.spec() for t in self.active()]

    def dispatch(self, call: ToolCall) -> str:
        """Run a model-requested tool call, returning a string result.

        Failures are caught and returned as text so the model can recover
        rather than the whole turn crashing.
        """
        tool = self._tools.get(call.name)
        if tool is None or not self._is_enabled(call.name):
            return f"[error] unknown or disabled tool: {call.name}"
        try:
            result = tool.run(**call.arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except ToolError as exc:
            return f"[error] {exc}"
        except Exception as exc:  # defensive: never let a tool kill the loop
            return f"[error] tool '{call.name}' failed: {exc}"

    def __len__(self) -> int:
        return len(self.active())
