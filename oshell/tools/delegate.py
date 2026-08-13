"""Delegate: hand a subtask to a fresh helper agent with its own clean context.

At local context sizes (8–32k), isolation isn't a luxury — it's a budget trick.
A research errand or multi-step side quest can burn thousands of tokens of tool
output the main conversation never needs to see; the helper spends them in its
own window and reports back one answer. Pairs with routing: the helper runs on
the fast model when one is configured.

Safety: the helper gets no approver, so under ``approvals: ask`` its sensitive
tools are denied — delegation never becomes a side door around a confirmation
the user would otherwise have seen. It also has no delegate tool of its own
(no recursive fan-out).
"""

from __future__ import annotations

from typing import Any

from ..config import Config
from ..providers.base import LLMProvider
from .base import Tool

_MAX_REPLY = 8000


class DelegateTool(Tool):
    name = "delegate"
    description = (
        "Hand a self-contained subtask to a fresh helper agent that works in its "
        "own clean context and returns only its final answer. Use for research "
        "errands or multi-step side quests whose intermediate details you don't "
        "need. The helper cannot see this conversation — include everything it "
        "needs in the task."
    )
    local_only = True  # delegation itself; the helper's own tools are gated as usual
    parameters = {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Complete, self-contained instructions for the helper",
            }
        },
        "required": ["task"],
    }

    def __init__(self, provider: LLMProvider, config: Config):
        self._provider = provider
        self._config = config

    def run(self, task: str = "", **_: Any) -> str:
        if not task.strip():
            return "[error] delegate needs a task"
        from ..agent import Agent, TurnComplete
        from . import default_registry

        model = self._config.routing.fast_model or self._config.default_model
        registry = default_registry(
            self._provider, self._config, model=model, delegate=False
        )
        helper = Agent(self._provider, registry, self._config, model=model)
        final = ""
        for event in helper.send(task):
            if isinstance(event, TurnComplete):
                final = event.text
        final = final.strip()
        if not final:
            return "[error] the helper returned nothing"
        return final[:_MAX_REPLY]
