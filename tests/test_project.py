"""Project awareness: a real (temp) git repo yields a brief; elsewhere, None."""

from __future__ import annotations

import subprocess

from oshell.project import project_context


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _make_repo(tmp_path):
    repo = tmp_path / "proj"
    repo.mkdir()
    _git(["init", "-q", "-b", "main"], repo)
    _git(["config", "user.email", "t@t"], repo)
    _git(["config", "user.name", "t"], repo)
    (repo / "README.md").write_text("# Proj\nA tiny test project.\n")
    (repo / "package.json").write_text("{}")
    _git(["add", "-A"], repo)
    _git(["commit", "-qm", "first commit"], repo)
    return repo


def test_outside_a_repo_is_none(tmp_path):
    # conftest chdirs into tmp_path, which is not a repo
    assert project_context(tmp_path) is None


def test_repo_brief_contents(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "dirty.txt").write_text("uncommitted")
    ctx = project_context(repo)
    assert ctx is not None
    assert "Repository: proj" in ctx
    assert "Branch: main" in ctx
    assert "Node.js" in ctx  # stack detected from package.json
    assert "first commit" in ctx  # recent log
    assert "dirty.txt" in ctx  # uncommitted changes listed
    assert "A tiny test project." in ctx  # README head


def test_agent_injects_project_block(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)

    from oshell.agent import Agent
    from oshell.config import Config
    from oshell.providers.base import ChatChunk, LLMProvider
    from oshell.tools import ToolRegistry
    from oshell.tools.builtins import CurrentTimeTool

    class _P(LLMProvider):
        name = "p"

        def list_models(self):
            return ["m"]

        def chat(self, messages, **kwargs):
            yield ChatChunk(content="", done=True)

    agent = Agent(_P(), ToolRegistry([CurrentTimeTool()]), Config(), model="m")
    assert "Repository: proj" in agent.messages[0].content
    # And the flag turns it off.
    off = Agent(
        _P(), ToolRegistry([CurrentTimeTool()]), Config(project_context=False), model="m"
    )
    assert "Repository:" not in off.messages[0].content
