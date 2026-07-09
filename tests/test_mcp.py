"""MCP client tests: a real subprocess speaking JSON-RPC over stdio.

The fake server below implements just enough of the protocol (initialize,
tools/list, tools/call) to exercise the client end-to-end — spawn, handshake,
discovery, calls, error paths, timeouts — without needing drift/mechanic
installed. A live smoke test at the bottom runs against the real servers when
they're present and self-skips when they aren't.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from oshell.config import Config, MCPServerConfig
from oshell.mcp import (
    MCPClient,
    MCPError,
    MCPTool,
    _content_text,
    mcp_server_status,
    mcp_tools,
)
from oshell.tools.base import ToolError

FAKE_SERVER = '''
import json, sys

TOOLS = [
    {
        "name": "echo",
        "description": "Echo the arguments back.\\n\\nSecond paragraph is trimmed.",
        "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}},
    },
    {"name": "boom", "description": "Always errors.", "inputSchema": {"type": "object"}},
    {"name": "slow", "description": "Never answers.", "inputSchema": {"type": "object"}},
]

for line in sys.stdin:
    msg = json.loads(line)
    method, req_id = msg.get("method"), msg.get("id")
    if req_id is None:
        continue  # notification
    if method == "initialize":
        result = {"protocolVersion": "2024-11-05", "capabilities": {},
                  "serverInfo": {"name": "fake", "version": "0"}}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        name = msg["params"]["name"]
        if name == "slow":
            continue  # never respond — exercises the timeout
        if name == "boom":
            result = {"content": [{"type": "text", "text": "it broke"}], "isError": True}
        else:
            args = msg["params"].get("arguments", {})
            result = {"content": [{"type": "text", "text": "echo: " + json.dumps(args)}]}
    else:
        result = {}
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}) + "\\n")
    sys.stdout.flush()
'''


@pytest.fixture
def fake_server(tmp_path) -> tuple[str, list[str]]:
    script = tmp_path / "fake_mcp.py"
    script.write_text(FAKE_SERVER)
    return sys.executable, [str(script)]


@pytest.fixture
def client(fake_server):
    cmd, args = fake_server
    c = MCPClient("fake", cmd, args)
    yield c
    c.close()


def test_list_tools_and_call(client):
    defs = client.list_tools()
    assert [d["name"] for d in defs] == ["echo", "boom", "slow"]
    out = client.call_tool("echo", {"text": "hi"})
    assert out == 'echo: {"text": "hi"}'


def test_is_error_raises(client):
    with pytest.raises(MCPError, match="it broke"):
        client.call_tool("boom", {})


def test_timeout_raises_not_hangs(client, monkeypatch):
    monkeypatch.setattr("oshell.mcp._CALL_TIMEOUT", 1.0)
    with pytest.raises(MCPError, match="no response"):
        client.call_tool("slow", {})
    # ...and the client recovers for the next call (stale ids are skipped).
    assert client.call_tool("echo", {"n": 1}) == 'echo: {"n": 1}'


def test_missing_binary_is_graceful():
    c = MCPClient("ghost", "/definitely/not/here/ghost", ["server"])
    assert not c.available()
    with pytest.raises(MCPError, match="not installed"):
        c.list_tools()


def test_dead_server_respawns(client):
    assert client.list_tools()
    client._proc.kill()
    client._proc.wait()
    # Next call notices the corpse and starts a fresh process.
    assert client.call_tool("echo", {}) == "echo: {}"


def test_mcp_tool_adapts_to_the_tool_contract(client):
    defs = client.list_tools()
    tool = MCPTool(client, defs[0])
    assert tool.name == "fake_echo"  # namespaced by server
    assert tool.description == "[fake] Echo the arguments back."  # first paragraph only
    assert tool.parameters["properties"]["text"]["type"] == "string"
    assert tool.local_only is True  # network=False default
    assert tool.run(text="x") == 'echo: {"text": "x"}'
    boom = MCPTool(client, defs[1], network=True)
    assert boom.local_only is False
    with pytest.raises(ToolError):
        boom.run()


def test_mcp_tools_from_config(fake_server):
    cmd, args = fake_server
    cfg = Config(
        mcp_servers={
            "fake": MCPServerConfig(command=cmd, args=args),
            "off": MCPServerConfig(command=cmd, args=args, enabled=False),
            "ghost": MCPServerConfig(command="/nope/ghost"),
        }
    )
    names = {t.name for t in mcp_tools(cfg)}
    assert names == {"fake_echo", "fake_boom", "fake_slow"}  # off + ghost contribute nothing
    status = dict(mcp_server_status(cfg))
    assert status == {"fake": True, "ghost": False}  # disabled servers not listed


def test_default_config_ships_mechanic_and_drift():
    cfg = Config()
    assert set(cfg.mcp_servers) == {"mechanic", "drift"}
    for server in cfg.mcp_servers.values():
        assert server.enabled
        assert server.args == ["server"]
        assert server.network is False  # local-first pair -> "local" in the privacy UI


def test_capabilities_list_mcp_servers():
    from oshell.capabilities import optional_features

    caps = {c.name for c in optional_features(Config())}
    assert "mechanic (MCP)" in caps and "drift (MCP)" in caps


def test_system_prompt_teaches_the_diagnosis_pattern(fake_server):
    from oshell.agent.loop import build_system_prompt
    from oshell.tools import ToolRegistry
    from oshell.tools.base import Tool

    class _T(Tool):
        parameters = {"type": "object", "properties": {}}

        def __init__(self, name):
            self.name = name
            self.description = name

        def run(self, **kw):
            return ""

    reg = ToolRegistry([_T("mechanic_is_this_normal"), _T("drift_diff_latest")])
    prompt = build_system_prompt(reg)
    assert "Machine memory" in prompt
    assert "mechanic_is_this_normal" in prompt
    assert "drift_diff_latest" in prompt
    assert "WHETHER something is off" in prompt  # the chained-diagnosis guidance


def test_content_text_shapes():
    two = {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}
    assert _content_text(two) == "a\nb"
    assert _content_text({"structuredContent": {"k": 1}}) == '{"k": 1}'
    assert _content_text({"other": True}) == '{"other": true}'


# ── live smoke test: the real first-party pair, when installed ────────────────


def test_live_mechanic_and_drift_round_trip():
    # conftest sandboxes $HOME, so resolve the REAL home for the live binaries.
    import pwd

    real_home = pwd.getpwuid(__import__("os").getuid()).pw_dir
    servers = {}
    for name in ("mechanic", "drift"):
        cmd = Path(real_home) / ".local/share" / name / ".venv/bin" / name
        if cmd.is_file():
            servers[name] = MCPServerConfig(
                command=str(cmd),
                args=["server"],
                env={f"{name.upper()}_DATA_DIR": f"{real_home}/.local/share/{name}-data"},
            )
    if not servers:
        pytest.skip("mechanic/drift not installed on this machine")
    cfg = Config(mcp_servers=servers)
    names = {t.name for t in mcp_tools(cfg)}
    if "mechanic" in servers:
        assert "mechanic_is_this_normal" in names
    if "drift" in servers:
        assert "drift_diff_latest" in names
