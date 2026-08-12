"""Custom markdown slash commands: the filesystem is the registry."""

from __future__ import annotations

from oshell import commands


def test_list_ignores_invalid_names(tmp_path):
    (tmp_path / "standup.md").write_text("What did I do?")
    (tmp_path / "UPPER.md").write_text("nope")  # invalid: uppercase
    (tmp_path / "notes.txt").write_text("nope")  # invalid: not .md
    found = commands.list_commands(tmp_path)
    assert list(found) == ["standup"]


def test_missing_dir_is_empty(tmp_path):
    assert commands.list_commands(tmp_path / "nowhere") == {}


def test_render_substitutes_args(tmp_path):
    (tmp_path / "review.md").write_text("Review this diff:\n$ARGS\nBe brief.")
    out = commands.render("review", "the auth module", tmp_path)
    assert out == "Review this diff:\nthe auth module\nBe brief."


def test_render_positional_words(tmp_path):
    (tmp_path / "compare.md").write_text("Compare $1 with $2.")
    assert commands.render("compare", "redis postgres", tmp_path) == "Compare redis with postgres."
    # Missing positions become empty rather than leaking the placeholder.
    assert commands.render("compare", "redis", tmp_path) == "Compare redis with ."


def test_render_appends_args_without_placeholder(tmp_path):
    (tmp_path / "eli5.md").write_text("Explain like I'm five:")
    out = commands.render("eli5", "quantum tunneling", tmp_path)
    assert out == "Explain like I'm five:\n\nquantum tunneling"


def test_render_unknown_is_none(tmp_path):
    assert commands.render("ghost", "", tmp_path) is None


def test_slash_fallback_runs_custom_command(tmp_path, monkeypatch):
    """/standup in the REPL renders the file and sends it as a turn."""
    from collections.abc import Iterator
    from typing import Any

    from oshell.agent import Agent
    from oshell.cli import _handle_slash
    from oshell.config import Config
    from oshell.providers.base import ChatChunk, LLMProvider, Message
    from oshell.tools import ToolRegistry
    from oshell.tools.builtins import CurrentTimeTool

    (tmp_path / "standup.md").write_text("Summarize $ARGS for standup.")
    monkeypatch.setattr(commands, "DEFAULT_DIR", str(tmp_path))

    class _P(LLMProvider):
        name = "p"

        def list_models(self) -> list[str]:
            return ["m"]

        def chat(self, messages: list[Message], **kwargs: Any) -> Iterator[ChatChunk]:
            yield ChatChunk(content="ok", done=True)

    agent = Agent(_P(), ToolRegistry([CurrentTimeTool()]), Config(), model="m")
    assert _handle_slash(agent, "/standup yesterday's work") is True
    sent = [m for m in agent.messages if m.role == "user"]
    assert sent and sent[-1].content == "Summarize yesterday's work for standup."
