"""The sgpt lineage: propose / describe / code / fix, with a scripted provider."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from oshell import shellops
from oshell.providers.base import ChatChunk, LLMProvider, Message


class _Scripted(LLMProvider):
    name = "scripted"

    def __init__(self, reply: str):
        self.reply = reply
        self.seen: list[list[Message]] = []

    def list_models(self) -> list[str]:
        return ["m"]

    def chat(self, messages: list[Message], **kwargs: Any) -> Iterator[ChatChunk]:
        self.seen.append(messages)
        yield ChatChunk(content=self.reply, done=True)


def test_clean_command_strips_fences_prefixes_and_chatter():
    assert shellops.clean_command("```bash\nfind . -name '*.json'\n```") == "find . -name '*.json'"
    assert shellops.clean_command("$ ls -la") == "ls -la"
    assert shellops.clean_command("Here is the command:\nls -la\n") == "ls -la"
    assert shellops.clean_command("`du -sh *`") == "du -sh *"
    assert shellops.clean_command("   ") == ""
    assert shellops.clean_command("cannot: needs root") == "CANNOT:needs root"
    # Multi-line proposals collapse to the first line: one command means one command.
    assert shellops.clean_command("cd x\nrm -rf y") == "cd x"


def test_clean_code_keeps_every_fenced_block_and_nothing_else():
    reply = "Sure!\n```python\nprint(1)\n```\nand\n```python\nprint(2)\n```\nEnjoy."
    assert shellops.clean_code(reply) == "print(1)\n\nprint(2)\n"
    assert shellops.clean_code("print('hi')") == "print('hi')\n"


def test_propose_command_sends_host_context_and_role():
    prov = _Scripted("```sh\ndf -h\n```")
    ctx = shellops.HostContext(cwd="/tmp/x", listing="a, b", stdin="err 1")
    out = shellops.propose_command(prov, "m", "disk space", ctx, examples="\n\nEX")
    assert out == "df -h"
    system, user = prov.seen[0][0].content, prov.seen[0][1].content
    assert "EXACTLY ONE shell command" in system and system.endswith("EX")
    assert "/tmp/x" in user and "a, b" in user and "err 1" in user and "disk space" in user


def test_describe_and_code_use_their_roles():
    prov = _Scripted("Lists files, **long** format.")
    assert "Lists files" in shellops.describe_command(prov, "m", "ls -l")
    assert "terse" in prov.seen[0][0].content
    prov2 = _Scripted("```python\nprint('x')\n```")
    assert shellops.generate_code(prov2, "m", "print x", "python", stdin="data") == "print('x')\n"
    assert "language is python" in prov2.seen[0][0].content
    assert "data" in prov2.seen[0][1].content


def test_diagnose_failure_parses_why_and_fix():
    prov = _Scripted("WHY: the directory doesn't exist.\nFIX: mkdir -p build && make")
    d = shellops.diagnose_failure(prov, "m", "make", 2, output="No rule")
    assert d.why == "the directory doesn't exist."
    assert d.fix == "mkdir -p build && make"
    assert "Exit code: 2" in prov.seen[0][1].content and "No rule" in prov.seen[0][1].content
    # NONE / sloppy formats
    assert shellops.parse_diagnosis("WHY: gone.\nFIX: NONE").fix is None
    loose = shellops.parse_diagnosis("It failed because reasons.")
    assert loose.why == "It failed because reasons." and loose.fix is None
    fenced = shellops.parse_diagnosis("```\nWHY: a\nFIX: `ls`\n```")
    assert fenced.fix == "ls"


def test_last_command_roundtrip(tmp_path):
    f = tmp_path / "last_cmd"
    assert shellops.read_last_command(f) is None
    shellops.record_last_command("git push origin main", 128, cwd="/repo", path=f)
    last = shellops.read_last_command(f)
    assert last.command == "git push origin main"
    assert last.exit_code == 128 and last.cwd == "/repo" and last.when is not None
    # The shell hooks write the same shape by hand — including multi-line commands.
    f.write_text("1\n/home/u\n1700000000\nfor x in a b; do\n  echo $x\ndone\n")
    last = shellops.read_last_command(f)
    assert last.exit_code == 1 and last.command.startswith("for x in") and "done" in last.command
    f.write_text("garbage")
    assert shellops.read_last_command(f) is None


def test_do_history_feeds_only_successes(tmp_path):
    f = tmp_path / "do.jsonl"
    assert shellops.do_examples(path=f) == ""
    shellops.record_do("list", "ls", 0, path=f)
    shellops.record_do("explode", "rm -rf /", 1, path=f)
    ex = shellops.do_examples(path=f)
    assert "command: ls" in ex and "rm -rf" not in ex


def test_destructive_tripwire():
    assert shellops.is_destructive("rm -rf ~/stuff")
    assert shellops.is_destructive("git push --force origin main")
    assert shellops.is_destructive("sudo dd if=x of=/dev/disk2")
    assert not shellops.is_destructive("ls -la")
    assert not shellops.is_destructive("rm notes.txt")
