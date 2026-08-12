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


def _mgmt_agent():
    """An agent over a provider that records pull/delete calls."""
    from collections.abc import Iterator
    from typing import Any

    from oshell.agent import Agent
    from oshell.config import Config
    from oshell.providers.base import ChatChunk, LLMProvider, Message, PullProgress
    from oshell.tools import ToolRegistry
    from oshell.tools.builtins import CurrentTimeTool

    class _Managed(LLMProvider):
        name = "managed"

        def __init__(self):
            self.pulled: list[str] = []
            self.deleted: list[str] = []

        def list_models(self) -> list[str]:
            return ["m"]

        def chat(self, messages: list[Message], **kwargs: Any) -> Iterator[ChatChunk]:
            yield ChatChunk(content="", done=True)

        def supports_model_management(self) -> bool:
            return True

        def pull_model(self, name: str):
            self.pulled.append(name)
            yield PullProgress(status="pulling manifest")
            yield PullProgress(status="downloading", total=10, completed=10)
            yield PullProgress(status="success")

        def delete_model(self, name: str) -> None:
            self.deleted.append(name)

    provider = _Managed()
    return Agent(provider, ToolRegistry([CurrentTimeTool()]), Config(), model="m"), provider


def test_pull_slash_command_streams_progress():
    from oshell.cli import _handle_slash

    agent, provider = _mgmt_agent()
    assert _handle_slash(agent, "/pull qwen3:8b") is True
    assert provider.pulled == ["qwen3:8b"]


def test_rm_slash_command_deletes_after_confirm(monkeypatch):
    from oshell.cli import _handle_slash

    agent, provider = _mgmt_agent()
    monkeypatch.setattr("typer.confirm", lambda *a, **k: True)
    assert _handle_slash(agent, "/rm old:7b") is True
    assert provider.deleted == ["old:7b"]


def test_rm_slash_command_refuses_active_model(monkeypatch):
    from oshell.cli import _handle_slash

    agent, provider = _mgmt_agent()
    monkeypatch.setattr("typer.confirm", lambda *a, **k: True)
    assert _handle_slash(agent, "/rm m") is True  # "m" is the active model
    assert provider.deleted == []


def test_rm_slash_command_respects_declined_confirm(monkeypatch):
    from oshell.cli import _handle_slash

    agent, provider = _mgmt_agent()
    monkeypatch.setattr("typer.confirm", lambda *a, **k: False)
    assert _handle_slash(agent, "/rm old:7b") is True
    assert provider.deleted == []
