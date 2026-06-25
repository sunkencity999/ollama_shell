"""Typed, layered configuration for oshell.

This replaces the old footgun where ``config.json`` was silently ignored by
git (a blanket ``*.json`` rule) and read/written ad-hoc as an untyped dict.

Configuration is resolved in increasing order of precedence:

    1. Built-in defaults (the ``Config`` model below)
    2. ``config.json``        — committed, shared defaults for the project
    3. ``config.local.json``  — per-machine overrides (git-ignored)
    4. Environment variables  — ``OSHELL_*`` (highest precedence)

Everything is a validated pydantic model, so a typo in a config file fails
loudly at startup instead of surfacing as a mysterious ``KeyError`` deep in a
request handler.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# Files searched, lowest precedence first. Resolved relative to the current
# working directory so the shell can be configured per-project.
_CONFIG_FILES = ("config.json", "config.local.json")
_ENV_PREFIX = "OSHELL_"


class ProviderConfig(BaseModel):
    """Which LLM backend to talk to and how to reach it."""

    name: str = "ollama"  # one of: ollama | openai | mlx (see oshell.providers)
    host: str = "http://localhost:11434"
    api_key: str | None = None  # only used by openai-compatible backends
    timeout: float = 120.0


class ShellConfig(BaseModel):
    """Local shell command execution (the run_command tool)."""

    enabled: bool = True  # commands run with full autonomy by default
    timeout: float = 60.0  # per-command wall-clock limit (seconds)
    max_output: int = 10000  # truncate combined stdout/stderr to this many chars
    # Which shell to use on Windows: auto -> pwsh, else powershell; or force "cmd".
    windows_shell: str = "auto"  # auto | powershell | pwsh | cmd
    # Keep one long-lived shell so cd / env / activated venvs persist across
    # commands (POSIX only; Windows always runs one-shot PowerShell).
    persistent: bool = True


class SessionConfig(BaseModel):
    """Persist & resume the conversation transcript across runs."""

    persist: bool = True
    path: str = "~/.oshell/last_session.json"
    max_messages: int = 200


class MemoryConfig(BaseModel):
    """Lightweight, always-on persistent memory (facts about the user)."""

    enabled: bool = True  # on by default — dependency-free
    path: str = "~/.oshell/memory.json"
    max_inject: int = 40  # most-recent memories injected into the system prompt


class GuiConfig(BaseModel):
    """GUI computer-use (desktop control). Opt-in; vision-model gated."""

    enabled: bool = False  # off by default — needs OS permissions + a vision model
    notify_on_finish: bool = True  # desktop notification when a GUI turn completes
    refocus_terminal: bool = True  # bring the terminal back to front after a GUI turn


class BrowserConfig(BaseModel):
    """Hidden browser computer-use (Playwright). Opt-in; vision-model gated."""

    enabled: bool = False  # off by default — needs the [browser] extra
    headless: bool = True  # True = the browser never appears on screen
    width: int = 1280
    height: int = 800
    timeout: float = 60.0


class KnowledgeConfig(BaseModel):
    """Local vector knowledge base (the ``[rag]`` extra)."""

    path: str = "~/.oshell/knowledge"  # ChromaDB persistent dir
    collection: str = "oshell_kb"
    model: str = "all-MiniLM-L6-v2"  # sentence-transformers embedding model
    default_limit: int = 5


class AtlassianConfig(BaseModel):
    """Jira/Confluence Server credentials.

    These can also come from environment variables (``JIRA_URL``/``JIRA_TOKEN``,
    ``CONFLUENCE_URL``/``CONFLUENCE_TOKEN``); env wins, this is the fallback so
    creds can live in a git-ignored ``config.local.json`` instead of the shell.
    """

    jira_url: str = ""
    jira_token: str = ""
    jira_user: str = ""
    confluence_url: str = ""
    confluence_token: str = ""
    confluence_user: str = ""
    auth_method: str = "pat"  # pat | bearer | basic (Server: pat == bearer)


class FinetuneConfig(BaseModel):
    """Local LoRA fine-tuning (the ``[finetune]`` path; MLX on Apple Silicon)."""

    jobs_dir: str = "~/.oshell/finetune"  # job metadata + adapters + logs
    batch_size: int = 1
    learning_rate: float = 1e-5
    iters: int = 200  # training iterations
    num_layers: int = 16  # LoRA layers to train


class Config(BaseModel):
    """Top-level runtime configuration for the shell."""

    # Model selection
    default_model: str = "llama3"
    default_vision_model: str = "llama3.2-vision"

    # Generation defaults
    temperature: float = 0.7
    context_length: int = 8192

    # Behaviour
    verbose: bool = False
    save_history: bool = True
    history_file: str = "~/.ollama_shell_history.json"

    # Backend
    provider: ProviderConfig = Field(default_factory=ProviderConfig)

    # Always-on persistent memory (facts about the user)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)

    # Conversation persistence / resume
    session: SessionConfig = Field(default_factory=SessionConfig)

    # Local vector knowledge base
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)

    # Local fine-tuning
    finetune: FinetuneConfig = Field(default_factory=FinetuneConfig)

    # Atlassian (Jira/Confluence Server) — optional fallback for env creds
    atlassian: AtlassianConfig = Field(default_factory=AtlassianConfig)

    # Local shell command execution
    shell: ShellConfig = Field(default_factory=ShellConfig)

    # GUI computer-use (opt-in)
    gui: GuiConfig = Field(default_factory=GuiConfig)

    # Hidden browser computer-use (opt-in)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)

    # Agent loop
    max_tool_iterations: int = 8  # safety cap on tool-call rounds per turn
    enabled_tools: list[str] = Field(default_factory=lambda: ["*"])  # "*" = all registered

    # ── loading / saving ────────────────────────────────────────────────────
    @classmethod
    def load(cls, root: Path | str | None = None) -> Config:
        """Build a Config by layering files and environment variables."""
        root = Path(root) if root else Path.cwd()
        data: dict[str, Any] = {}
        for fname in _CONFIG_FILES:
            path = root / fname
            if path.is_file():
                _deep_update(data, _read_json(path))
        _apply_env_overrides(data)
        return cls.model_validate(data)

    def save(self, path: Path | str = "config.local.json") -> None:
        """Persist to a machine-local file (kept out of git by .gitignore)."""
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")

    def expanded_history_file(self) -> Path:
        return Path(self.history_file).expanduser()


def update_local_config(
    updates: dict[str, Any], root: Path | str | None = None, filename: str = "config.local.json"
) -> Path:
    """Merge ``updates`` into the machine-local config file and write it back.

    Used to persist user choices (e.g. the selected default model) without
    clobbering anything else already in ``config.local.json`` (like Atlassian
    creds). The file is git-ignored.
    """
    root = Path(root) if root else Path.cwd()
    path = root / filename
    data: dict[str, Any] = _read_json(path) if path.is_file() else {}
    _deep_update(data, updates)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"Could not parse config file {path}: {exc}") from exc


def _deep_update(base: dict[str, Any], overlay: dict[str, Any]) -> None:
    """Recursively merge ``overlay`` into ``base`` (overlay wins)."""
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value


def _apply_env_overrides(data: dict[str, Any]) -> None:
    """Map ``OSHELL_FOO=bar`` -> data['foo']='bar', and ``OSHELL_PROVIDER__HOST``
    -> data['provider']['host'] (double-underscore = nesting)."""
    for env_key, raw in os.environ.items():
        if not env_key.startswith(_ENV_PREFIX):
            continue
        path = env_key[len(_ENV_PREFIX):].lower().split("__")
        cursor = data
        for part in path[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[path[-1]] = _coerce(raw)


def _coerce(raw: str) -> Any:
    """Best-effort scalar coercion for env-var strings."""
    low = raw.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw
