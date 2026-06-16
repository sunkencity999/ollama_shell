"""Events emitted by the agent loop.

The loop yields a stream of these so any front-end (CLI, Textual TUI, a test)
can render progress without the loop knowing how it's displayed. This is the
seam that let us add a TUI without touching agent logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextDelta:
    """A streamed piece of assistant text."""

    text: str


@dataclass
class ToolStarted:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolFinished:
    name: str
    result: str


@dataclass
class TurnComplete:
    """End of a turn; ``text`` is the full assistant reply."""

    text: str


@dataclass
class LimitReached:
    """The tool-iteration safety cap was hit before the model finished."""

    iterations: int


AgentEvent = TextDelta | ToolStarted | ToolFinished | TurnComplete | LimitReached
