"""Roles: built-in system prompts, user overrides, placeholder filling."""

from __future__ import annotations

import pytest

from oshell import roles, shellinit


def test_builtin_roles_fill_placeholders():
    text = roles.role_prompt("shell")
    assert "{os}" not in text and "{shell}" not in text
    assert "EXACTLY ONE shell command" in text
    assert roles.role_prompt("nope") is None
    assert set(roles.list_roles()) >= {"default", "shell", "code", "describe", "fix", "sysadmin"}


def test_user_role_overrides_builtin_and_lists(tmp_path):
    d = tmp_path / "roles"
    path = roles.create_role("shell", "Only fish commands for {os}.", directory=d)
    assert path.name == "shell.md"
    assert roles.role_prompt("shell", directory=d).startswith("Only fish commands for ")
    roles.create_role("reviewer", directory=d)  # scaffolds a template
    listed = roles.list_roles(d)
    assert listed["shell"].endswith("shell.md") and listed["reviewer"].endswith("reviewer.md")
    assert listed["code"] == "builtin"
    with pytest.raises(FileExistsError):
        roles.create_role("reviewer", directory=d)
    with pytest.raises(ValueError):
        roles.create_role("Bad Name", directory=d)


def test_fill_keeps_unknown_braces():
    out = roles.fill("x {os} {unknown} {cwd}", cwd="/here")
    assert "{unknown}" in out and "/here" in out and "{os}" not in out


def test_agent_system_extra_layers_a_role_and_survives_rebuild():
    from collections.abc import Iterator
    from typing import Any

    from oshell.agent import Agent
    from oshell.config import Config
    from oshell.providers.base import ChatChunk, LLMProvider, Message
    from oshell.tools import ToolRegistry
    from oshell.tools.builtins import CurrentTimeTool

    class _P(LLMProvider):
        name = "p"

        def list_models(self) -> list[str]:
            return ["m"]

        def chat(self, messages: list[Message], **kw: Any) -> Iterator[ChatChunk]:
            yield ChatChunk(content="", done=True)

    agent = Agent(_P(), ToolRegistry([CurrentTimeTool()]), Config(project_context=False))
    base = agent.messages[0].content
    agent.system_extra = roles.role_prompt("sysadmin")
    assert agent.messages[0].content.startswith(base)
    prompt = agent.messages[0].content
    assert "## Role" in prompt and "senior systems administrator" in prompt
    agent.rebuild_system_prompt()
    assert "## Role" in agent.messages[0].content  # survives a rebuild
    agent.system_extra = None
    assert agent.messages[0].content == base


@pytest.mark.parametrize("shell", shellinit.SHELLS)
def test_init_snippets_cover_the_four_features(shell):
    s = shellinit.snippet(shell)
    assert "oshell do --print" in s  # '#…' → command on the line
    assert "oshell ask" in s  # Ctrl+G asks
    assert "last_cmd" in s  # last command capture for `oshell fix`
    assert "command not found" in s  # nudge instead of a dead end
    assert "colors.sh" in s  # theme colors into the shell
    assert "fish_prompt" not in s and "PROMPT=" not in s and "_oshell_ps1" not in s
    themed = shellinit.snippet(shell, prompt=True)
    assert len(themed) > len(s) and "OSHELL_ACCENT" in themed
    with pytest.raises(ValueError):
        shellinit.snippet("powershell")
