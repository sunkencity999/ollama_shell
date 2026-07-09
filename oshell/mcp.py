"""A minimal MCP (Model Context Protocol) stdio client — no SDK required.

oshell's tool host has always been "MCP-style"; this makes it a real MCP
*client*. Any server listed in ``config.mcp_servers`` is spawned on demand
(newline-delimited JSON-RPC 2.0 over stdin/stdout), its tools discovered via
``tools/list``, and each one adapted into a first-class ``Tool`` the agent can
call like any built-in — exactly the seam ``tools/base.py`` promised.

Out of the box oshell ships with two first-party servers configured —
`Mechanic <https://github.com/sunkencity999/mechanic>`_ ("is this normal for
this machine?") and `Drift <https://github.com/sunkencity999/drift>`_ ("what
changed on this box?") — the shell's memory of the machine it lives on. Both
degrade gracefully: if a server's binary isn't installed, its tools simply
don't register and the capabilities panel says how to get them.

Design notes:

* One long-lived subprocess per server, shared across registry rebuilds via a
  module-level cache (model switches must not respawn daemons).
* A background reader thread per client feeds a response queue; requests are
  serialized under a lock and matched by JSON-RPC id, with timeouts so a hung
  server can never hang a turn.
* All failures degrade to ``ToolError`` — the model sees "[error] …" and can
  route around it; the session never crashes.
"""

from __future__ import annotations

import atexit
import json
import os
import queue
import shutil
import subprocess
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .tools.base import Tool, ToolError

if TYPE_CHECKING:
    from .config import Config, MCPServerConfig

PROTOCOL_VERSION = "2024-11-05"
_START_TIMEOUT = 10.0  # spawn + initialize + tools/list
_CALL_TIMEOUT = 60.0  # a single tools/call


class MCPError(Exception):
    """Transport or protocol failure talking to an MCP server."""


def _expand(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value))


class MCPClient:
    """One MCP server over stdio: spawn, handshake, list, call."""

    def __init__(
        self,
        name: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ):
        self.name = name
        self.command = _expand(command)
        self.args = list(args or [])
        self.env = {k: _expand(v) for k, v in (env or {}).items()}
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()  # serializes request/response cycles
        self._responses: queue.Queue[dict[str, Any]] = queue.Queue()
        self._next_id = 0

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def available(self) -> bool:
        """Is the server's executable present on this machine?"""
        return Path(self.command).is_file() or shutil.which(self.command) is not None

    def _alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _ensure_started(self) -> None:
        if self._alive():
            return
        if not self.available():
            raise MCPError(f"MCP server '{self.name}' not installed ({self.command})")
        env = dict(os.environ)
        env.update(self.env)
        try:
            self._proc = subprocess.Popen(
                [self.command, *self.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # FastMCP logs there; keep our TTY clean
                env=env,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise MCPError(f"could not spawn MCP server '{self.name}': {exc}") from exc
        self._responses = queue.Queue()
        threading.Thread(target=self._reader, args=(self._proc,), daemon=True).start()
        self._handshake()

    def _reader(self, proc: subprocess.Popen) -> None:
        """Pump stdout lines into the response queue until the process exits."""
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue  # stray non-JSON output — ignore
            if isinstance(msg, dict) and "id" in msg:
                self._responses.put(msg)
            # Notifications (no id) are ignored — we subscribe to nothing.

    def _handshake(self) -> None:
        result = self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "oshell", "version": "0.2"},
            },
            timeout=_START_TIMEOUT,
        )
        if not isinstance(result, dict):
            raise MCPError(f"MCP server '{self.name}': bad initialize response")
        self._notify("notifications/initialized")

    def close(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                self._proc.kill()
        self._proc = None

    # ── JSON-RPC plumbing ─────────────────────────────────────────────────────
    def _send(self, payload: dict[str, Any]) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        try:
            self._proc.stdin.write(json.dumps(payload) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise MCPError(f"MCP server '{self.name}' pipe closed: {exc}") from exc

    def _notify(self, method: str) -> None:
        self._send({"jsonrpc": "2.0", "method": method})

    def _request(self, method: str, params: dict[str, Any], timeout: float) -> Any:
        self._next_id += 1
        req_id = self._next_id
        self._send({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        while True:
            try:
                msg = self._responses.get(timeout=timeout)
            except queue.Empty:
                raise MCPError(
                    f"MCP server '{self.name}': no response to {method} in {timeout:.0f}s"
                ) from None
            if msg.get("id") != req_id:
                continue  # stale response from an interrupted earlier call
            if "error" in msg:
                err = msg["error"]
                raise MCPError(f"MCP server '{self.name}': {err.get('message', err)}")
            return msg.get("result")

    # ── the two calls that matter ─────────────────────────────────────────────
    def list_tools(self) -> list[dict[str, Any]]:
        """Discover the server's tools (name, description, inputSchema)."""
        with self._lock:
            self._ensure_started()
            result = self._request("tools/list", {}, timeout=_START_TIMEOUT)
        return list((result or {}).get("tools", []))

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Invoke a tool and return its text content (errors raise MCPError)."""
        with self._lock:
            self._ensure_started()
            result = self._request(
                "tools/call", {"name": name, "arguments": arguments}, timeout=_CALL_TIMEOUT
            )
        text = _content_text(result)
        if isinstance(result, dict) and result.get("isError"):
            raise MCPError(text or f"tool '{name}' reported an error")
        return text


def _content_text(result: Any) -> str:
    """Flatten an MCP tool result's content into the text the model reads."""
    if not isinstance(result, dict):
        return json.dumps(result)
    parts = []
    for item in result.get("content", []):
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(item.get("text", ""))
    if parts:
        return "\n".join(parts)
    if "structuredContent" in result:
        return json.dumps(result["structuredContent"])
    return json.dumps(result)


class MCPTool(Tool):
    """An MCP server's tool, adapted to oshell's Tool contract.

    Named ``<server>_<tool>`` so the model (and the Tools panel) can see which
    box of capabilities it came from.
    """

    def __init__(self, client: MCPClient, tool_def: dict[str, Any], network: bool = False):
        self._client = client
        self._remote_name = tool_def["name"]
        self.name = f"{client.name}_{self._remote_name}"
        desc = (tool_def.get("description") or "").strip().split("\n\n")[0]
        self.description = f"[{client.name}] {desc}" if desc else f"[{client.name}] MCP tool"
        self.parameters = tool_def.get("inputSchema") or {"type": "object", "properties": {}}
        self.local_only = not network
        self.sensitive = False

    def run(self, **kwargs: Any) -> str:
        try:
            return self._client.call_tool(self._remote_name, kwargs)
        except MCPError as exc:
            raise ToolError(str(exc)) from exc


# ── shared clients: registry rebuilds must not respawn daemons ────────────────
_clients: dict[tuple[str, str], MCPClient] = {}
_clients_lock = threading.Lock()


@atexit.register
def _close_all() -> None:  # terminate spawned servers cleanly at exit
    with _clients_lock:
        for client in _clients.values():
            client.close()


def _shared_client(name: str, cfg: MCPServerConfig) -> MCPClient:
    key = (name, f"{cfg.command} {' '.join(cfg.args)}")
    with _clients_lock:
        if key not in _clients:
            _clients[key] = MCPClient(name, cfg.command, cfg.args, cfg.env)
        return _clients[key]


def mcp_tools(config: Config) -> list[Tool]:
    """Tools from every enabled, installed MCP server in config.

    A server that is missing, disabled, or fails discovery contributes no
    tools — the shell starts regardless, and the capabilities panel explains
    what's absent.
    """
    tools: list[Tool] = []
    seen: set[str] = set()
    for name, server in (config.mcp_servers or {}).items():
        if not server.enabled:
            continue
        client = _shared_client(name, server)
        if not client.available():
            continue
        try:
            defs = client.list_tools()
        except MCPError:
            continue  # unreachable/broken server — skip, never block startup
        for d in defs:
            tool = MCPTool(client, d, network=server.network)
            if tool.name in seen:  # a server advertising duplicates must not crash startup
                continue
            seen.add(tool.name)
            tools.append(tool)
    return tools


def mcp_server_status(config: Config) -> list[tuple[str, bool]]:
    """(name, available) for each configured server — for the capabilities panel."""
    out = []
    for name, server in (config.mcp_servers or {}).items():
        if not server.enabled:
            continue
        out.append((name, _shared_client(name, server).available()))
    return out
