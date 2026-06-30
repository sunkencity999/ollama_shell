"""Tests for CLI helpers (secret redaction in `oshell config`)."""

from __future__ import annotations

from oshell.cli import _redact


def test_redact_masks_secret_keys():
    data = {
        "default_model": "llama3",
        "provider": {"name": "ollama", "api_key": "supersecretvalue"},
        "atlassian": {"jira_url": "https://j", "jira_token": "abc123def456"},
    }
    out = _redact(data)
    # Non-secret values pass through untouched.
    assert out["default_model"] == "llama3"
    assert out["provider"]["name"] == "ollama"
    assert out["atlassian"]["jira_url"] == "https://j"
    # Secret-looking keys are masked, and the raw value never appears.
    assert "redacted" in out["provider"]["api_key"]
    assert "supersecretvalue" not in str(out)
    assert "abc123def456" not in str(out)


def test_redact_leaves_empty_secrets_alone():
    out = _redact({"atlassian": {"jira_token": ""}})
    assert out["atlassian"]["jira_token"] == ""  # nothing to hide


def test_daydream_slash_command_runs_without_history_side_effects():
    """`/daydream` should stream a dream and not mutate the conversation."""
    from collections.abc import Iterator
    from typing import Any

    from oshell.agent import Agent
    from oshell.cli import _handle_slash
    from oshell.config import Config
    from oshell.providers.base import ChatChunk, LLMProvider, Message
    from oshell.tools import ToolRegistry
    from oshell.tools.builtins import CurrentTimeTool

    class _Dreamer(LLMProvider):
        name = "dreamer"

        def list_models(self) -> list[str]:
            return ["m"]

        def chat(self, messages: list[Message], **kwargs: Any) -> Iterator[ChatChunk]:
            yield ChatChunk(content="a quiet hum of electrons", done=True)

    agent = Agent(_Dreamer(), ToolRegistry([CurrentTimeTool()]), Config())
    before = list(agent.messages)
    assert _handle_slash(agent, "/daydream") is True
    assert agent.messages == before  # ephemeral: history untouched
