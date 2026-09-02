"""The sgpt lineage: turn intent into commands, commands into understanding.

shell_gpt made a generation of people treat the terminal as a conversation:
``sgpt -s "…"`` → a command → *execute / describe / abort*. This module is
that layer for oshell, factored out of the CLI so it is unit-testable with a
scripted provider and reusable from shell widgets::

    propose_command()   task → one command            (oshell do)
    describe_command()  command → what it does        (oshell explain, [d]escribe)
    generate_code()     prompt → raw code, no fences  (oshell code)
    diagnose_failure()  failed cmd → WHY + FIX        (oshell fix)

Plus the little state the shell integration writes for us: the last command
the user ran and how it exited (``~/.oshell/last_cmd``), so ``oshell fix``
works on whatever just went wrong — no re-typing, no copy-paste.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from . import roles
from .providers.base import LLMProvider, Message

LAST_CMD_FILE = "~/.oshell/last_cmd"
DO_HISTORY = "~/.oshell/do_history.jsonl"
_FENCE_RE = re.compile(r"^```[^\n]*\n(.*?)\n?```\s*$", re.S)


@dataclass
class HostContext:
    """What the model needs to know to write a command that works *here*."""

    cwd: str
    listing: str  # first few dir entries, comma-joined
    stdin: str = ""  # piped input (tail), if any

    @classmethod
    def gather(cls, stdin: str = "", max_entries: int = 40) -> HostContext:
        cwd = os.getcwd()
        try:
            listing = ", ".join(sorted(os.listdir(cwd))[:max_entries])
        except OSError:  # pragma: no cover - defensive
            listing = ""
        return cls(cwd=cwd, listing=listing, stdin=stdin)

    def block(self) -> str:
        s = f"Working directory: {self.cwd}\nDirectory contents: {self.listing}"
        if self.stdin:
            s += f"\n\nPiped input:\n```\n{self.stdin}\n```"
        return s


@dataclass
class Diagnosis:
    why: str
    fix: str | None  # a command, or None when the model saw no safe one-liner


# ── model plumbing ───────────────────────────────────────────────────────────
def complete(
    provider: LLMProvider, model: str, system: str, user: str, temperature: float = 0.2
) -> str:
    """One non-streaming completion, joined to a string."""
    chunks = provider.chat(
        [Message(role="system", content=system), Message(role="user", content=user)],
        model=model,
        stream=False,
        temperature=temperature,
    )
    return "".join(c.content for c in chunks)


def strip_fences(text: str) -> str:
    """Drop a single surrounding ``` fence (with optional language tag)."""
    t = text.strip()
    m = _FENCE_RE.match(t)
    if m:
        return m.group(1).strip("\n")
    return t.strip("`").strip()


def clean_command(reply: str) -> str:
    """One command out of a model reply: unfenced, first line, shell-prefix free.

    Returns "" for nothing usable. A ``CANNOT: reason`` sentinel is preserved
    so callers can show the reason instead of running it.
    """
    body = strip_fences(reply)
    for prefix in ("bash\n", "sh\n", "zsh\n", "$ "):
        body = body.removeprefix(prefix)
    body = body.strip()
    if not body:
        return ""
    if body.upper().startswith("CANNOT:"):
        return "CANNOT:" + body[7:].strip()
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    first = lines[0] if lines else ""
    # Models sometimes lead with a chatty line; if a later line looks like the
    # actual command (starts with a known binary shape), prefer it.
    if len(lines) > 1 and (first.endswith(":") or first.lower().startswith(("here", "you can"))):
        first = lines[1]
    return first.lstrip("$ ").strip()


def clean_code(reply: str) -> str:
    """All the code, none of the chatter: unfenced, trailing prose trimmed."""
    body = strip_fences(reply)
    # If the model wrapped multiple blocks, keep the fenced material only.
    blocks = re.findall(r"```[^\n]*\n(.*?)```", reply, re.S)
    if blocks:
        body = "\n\n".join(b.rstrip("\n") for b in blocks)
    return body.rstrip() + "\n"


# ── the four verbs ───────────────────────────────────────────────────────────
def propose_command(
    provider: LLMProvider,
    model: str,
    task: str,
    ctx: HostContext | None = None,
    examples: str = "",
    role: str = "shell",
) -> str:
    """Task → a single shell command (or "CANNOT: …", or "")."""
    ctx = ctx or HostContext.gather()
    system = (roles.role_prompt(role) or roles.BUILTIN_ROLES["shell"]) + examples
    reply = complete(provider, model, system, f"{ctx.block()}\n\nTask: {task}")
    return clean_command(reply)


def describe_command(
    provider: LLMProvider, model: str, command: str, role: str = "describe"
) -> str:
    """Command → a short markdown description (flags, hazards)."""
    system = roles.role_prompt(role) or roles.BUILTIN_ROLES["describe"]
    return complete(provider, model, system, f"Command:\n{command}", temperature=0.3).strip()


def generate_code(
    provider: LLMProvider,
    model: str,
    prompt: str,
    language: str | None = None,
    stdin: str = "",
    role: str = "code",
) -> str:
    """Prompt → raw code, ready to redirect into a file."""
    system = roles.role_prompt(role) or roles.BUILTIN_ROLES["code"]
    if language:
        system += f"\nThe language is {language}."
    user = prompt
    if stdin:
        user += f"\n\nInput to work with:\n```\n{stdin}\n```"
    return clean_code(complete(provider, model, system, user))


def diagnose_failure(
    provider: LLMProvider,
    model: str,
    command: str,
    exit_code: int | None,
    output: str = "",
    role: str = "fix",
) -> Diagnosis:
    """Failed command (+ its output if piped) → why it failed and a fix."""
    system = roles.role_prompt(role) or roles.BUILTIN_ROLES["fix"]
    user = f"Command: {command}\nExit code: {exit_code if exit_code is not None else 'unknown'}"
    if output:
        user += f"\nOutput:\n```\n{output[-6000:]}\n```"
    reply = complete(provider, model, system, user)
    return parse_diagnosis(reply)


def parse_diagnosis(reply: str) -> Diagnosis:
    """Pull WHY/FIX out of the model's reply; tolerate sloppy formatting."""
    text = strip_fences(reply)
    why_m = re.search(r"WHY:\s*(.+?)(?=\n\s*FIX:|\Z)", text, re.S | re.I)
    fix_m = re.search(r"FIX:\s*(.+)", text, re.S | re.I)
    why = (why_m.group(1) if why_m else text).strip()
    fix: str | None = None
    if fix_m:
        candidate = clean_command(fix_m.group(1))
        if (
            candidate
            and candidate.upper() not in ("NONE", "NONE.")
            and not candidate.startswith("CANNOT:")
        ):
            fix = candidate
    return Diagnosis(why=why, fix=fix)


# ── state written by the shell integration ───────────────────────────────────
@dataclass
class LastCommand:
    command: str
    exit_code: int | None
    cwd: str
    when: float | None = None


def read_last_command(path: str | Path | None = None) -> LastCommand | None:
    """The last command the shell hook recorded (see ``oshell init``).

    File shape (written by shell, so deliberately not JSON): line 1 exit code,
    line 2 cwd, line 3 epoch seconds, the rest the command (may span lines).
    """
    p = Path(path or LAST_CMD_FILE).expanduser()
    try:
        raw = p.read_text(encoding="utf-8")
    except OSError:
        return None
    lines = raw.split("\n")
    if len(lines) < 4:
        return None
    try:
        code: int | None = int(lines[0].strip())
    except ValueError:
        code = None
    try:
        when: float | None = float(lines[2].strip())
    except ValueError:
        when = None
    command = "\n".join(lines[3:]).strip()
    if not command:
        return None
    return LastCommand(command=command, exit_code=code, cwd=lines[1].strip(), when=when)


def record_last_command(
    command: str, exit_code: int, cwd: str | None = None, path: str | Path | None = None
) -> None:
    """Python-side writer (the shell hooks write the same shape directly)."""
    p = Path(path or LAST_CMD_FILE).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"{exit_code}\n{cwd or os.getcwd()}\n{time.time():.0f}\n{command}\n", encoding="utf-8"
    )


# ── do-history: the shell learns which commands worked for *this* user ───────
def do_examples(limit: int = 5, path: str | Path | None = None) -> str:
    """Recent successful task→command pairs, as few-shot context."""
    p = Path(path or DO_HISTORY).expanduser()
    if not p.is_file():
        return ""
    good = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:  # pragma: no cover - defensive
            continue
        if entry.get("rc") == 0:
            good.append(f"task: {entry['task']}\ncommand: {entry['command']}")
    if not good:
        return ""
    return "\n\nCommands that worked for this user before:\n" + "\n".join(good[-limit:])


def record_do(task: str, command: str, rc: int, path: str | Path | None = None) -> None:
    p = Path(path or DO_HISTORY).expanduser()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        entry = {"ts": time.strftime("%Y-%m-%d %H:%M"), "task": task, "command": command, "rc": rc}
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:  # pragma: no cover - defensive
        pass


def is_destructive(command: str) -> bool:
    """A cheap tripwire for the confirm prompt — not a security boundary."""
    patterns = (
        r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\b",
        r"\brm\s+-rf\b",
        r"\bmkfs\b",
        r"\bdd\s+.*\bof=/dev/",
        r">\s*/dev/sd",
        r"\bchmod\s+-R\s+777\b",
        r"\bgit\s+push\s+.*--force\b",
        r"\bgit\s+reset\s+--hard\b",
        r"\bdrop\s+(table|database)\b",
        r"\b:\(\)\s*\{\s*:\|:&\s*\};:",
        r"\bshutdown\b|\breboot\b",
        r"\bkillall\b|\bpkill\s+-9\b",
    )
    return any(re.search(p, command, re.I) for p in patterns)
