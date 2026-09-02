"""Roles — reusable system prompts, sgpt-style.

shell_gpt's best idea after ``--shell`` was ``--role``: a named system prompt
you can hand-tune once and reuse forever. Ours live as plain markdown in
``~/.oshell/roles/NAME.md`` (the filesystem is the registry, like custom
commands), with a handful of built-ins the one-shot commands lean on::

    oshell ask --role sysadmin "why is launchd respawning this?"
    oshell roles                 # list (built-in + yours)
    oshell roles new reviewer    # scaffold ~/.oshell/roles/reviewer.md

A user file with a built-in's name overrides it, so ``shell.md`` lets you
retune exactly how ``oshell do`` writes commands for your box. Placeholders
``{os}``, ``{shell}``, ``{cwd}`` are filled in at use time.
"""

from __future__ import annotations

import os
import platform
import re
from pathlib import Path

DEFAULT_DIR = "~/.oshell/roles"
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

BUILTIN_ROLES: dict[str, str] = {
    "default": (
        "You are a programming and system administration assistant managing {os} "
        "with {shell}. Be concise (about 100 words unless asked for more), prefer "
        "showing the exact command or code over describing it, and use markdown."
    ),
    "sysadmin": (
        "You are a senior systems administrator working on {os} ({shell}), current "
        "directory {cwd}. Diagnose before prescribing: name the likely cause, the "
        "one command that confirms it, then the fix. Prefer built-in tools over "
        "installing new ones. Flag anything destructive before suggesting it."
    ),
    "shell": (
        "You translate a user's task into EXACTLY ONE shell command for {os} ({shell}). "
        "Output ONLY the command — no backticks, no prose, no explanations. Prefer safe, "
        "non-destructive commands; never invent destructive flags the task didn't ask for. "
        "If multiple steps are required, chain them with && on one line. "
        "If the task is impossible or too dangerous for one command, output exactly: "
        "CANNOT: <one-line reason>"
    ),
    "code": (
        "You are a code generator. Output ONLY code, in plain text, with no markdown "
        "fences, no commentary, and no explanations before or after. If details are "
        "missing, make the most reasonable assumption silently. For example, for "
        "\"hello world in python\" output exactly: print('hello world')"
    ),
    "describe": (
        "You describe shell commands for someone on {os} ({shell}). Give a terse, "
        "one-sentence summary of what the whole command does, then one short line per "
        "argument or flag. Note anything destructive or irreversible in bold. About 80 "
        "words. Use markdown."
    ),
    "fix": (
        "A command just failed on {os} ({shell}) in {cwd}. Explain the most likely "
        "cause in one or two plain sentences, then propose a corrected command. "
        "Respond in EXACTLY this shape and nothing else:\n"
        "WHY: <one or two sentences>\n"
        "FIX: <one shell command, or NONE if there is no safe one-line fix>"
    ),
}

_TEMPLATE = """\
# {name}

You are {name}. Describe here how the model should behave when this role is
active — tone, format, what to prioritize, what never to do.

Placeholders filled at use time: {{os}}, {{shell}}, {{cwd}}.
"""


def roles_dir(directory: str | Path | None = None) -> Path:
    # Looked up at call time so tests (and adventurous users) can repoint it.
    return Path(directory or DEFAULT_DIR).expanduser()


def list_roles(directory: str | Path | None = None) -> dict[str, str]:
    """name -> source ("builtin" or the file path). User files override."""
    out = {name: "builtin" for name in BUILTIN_ROLES}
    d = roles_dir(directory)
    if d.is_dir():
        for f in sorted(d.glob("*.md")):
            if _NAME_RE.match(f.stem):
                out[f.stem] = str(f)
    return out


def role_prompt(name: str, directory: str | Path | None = None, **extra: str) -> str | None:
    """The role's system prompt with placeholders filled, or None if unknown."""
    d = roles_dir(directory)
    path = d / f"{name}.md"
    body: str | None = None
    if _NAME_RE.match(name) and path.is_file():
        try:
            body = path.read_text(encoding="utf-8").strip()
        except OSError:  # pragma: no cover - defensive
            body = None
    if body is None:
        body = BUILTIN_ROLES.get(name)
    if body is None:
        return None
    return fill(body, **extra)


def fill(text: str, **extra: str) -> str:
    """Substitute {os} {shell} {cwd} (and any extras); unknown braces are kept."""
    values = {
        "os": host_os(),
        "shell": shell_name(),
        "cwd": os.getcwd(),
        **extra,
    }

    def repl(m: re.Match[str]) -> str:
        return str(values.get(m.group(1), m.group(0)))

    return re.sub(r"\{([a-z_]+)\}", repl, text)


def shell_name() -> str:
    """The user's shell, by name: zsh / bash / fish … or powershell on Windows."""
    env = os.environ.get("SHELL")
    if env:
        return Path(env).name
    return "powershell" if os.name == "nt" else "sh"


def host_os() -> str:
    """A human OS label like 'macOS 15.1 (arm64)' or 'Linux 6.9 (x86_64)'."""
    system = platform.system()
    if system == "Darwin":
        ver = platform.mac_ver()[0] or platform.release()
        return f"macOS {ver} ({platform.machine()})"
    if system == "Windows":
        return f"Windows {platform.release()} ({platform.machine()})"
    return f"{system} {platform.release()} ({platform.machine()})"


def create_role(name: str, text: str | None = None, directory: str | Path | None = None) -> Path:
    """Write ~/.oshell/roles/NAME.md (a template if no text). Returns the path."""
    if not _NAME_RE.match(name):
        raise ValueError("role names are lowercase letters, digits, '-' and '_'")
    d = roles_dir(directory)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{name}.md"
    if path.exists():
        raise FileExistsError(f"{path} already exists")
    path.write_text(text or _TEMPLATE.format(name=name), encoding="utf-8")
    return path
