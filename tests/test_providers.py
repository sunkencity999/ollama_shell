"""Provider tests: response parsing (mocked) + a live Ollama smoke test."""

from __future__ import annotations

import json

import pytest

from oshell.config import Config, ProviderConfig
from oshell.providers import OllamaProvider, OpenAICompatProvider, get_provider
from oshell.providers.base import Message


class _FakeResp:
    def __init__(self, *, json_data=None, lines=None, status_code=200, text=""):
        self._json = json_data
        self._lines = lines or []
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        pass

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json

    def iter_lines(self):
        yield from self._lines


def test_registry_selects_backend():
    assert isinstance(get_provider(Config()), OllamaProvider)
    assert isinstance(get_provider(ProviderConfig(name="openai")), OpenAICompatProvider)
    with pytest.raises(ValueError):
        get_provider(ProviderConfig(name="nope"))


def test_ollama_streaming_parse(monkeypatch):
    lines = [
        json.dumps({"message": {"content": "Hel"}, "done": False}).encode(),
        json.dumps({"message": {"content": "lo"}, "done": False}).encode(),
        json.dumps({"message": {"content": ""}, "done": True}).encode(),
    ]
    monkeypatch.setattr(
        "oshell.providers.ollama.requests.post",
        lambda *a, **k: _FakeResp(lines=lines),
    )
    prov = OllamaProvider()
    chunks = list(prov.chat([Message(role="user", content="hi")], model="m"))
    assert "".join(c.content for c in chunks) == "Hello"
    assert chunks[-1].done is True


def test_ollama_tool_calls_parse(monkeypatch):
    response = {
        "message": {
            "content": "",
            "tool_calls": [
                {"function": {"name": "web_search", "arguments": {"query": "weather"}}}
            ],
        },
        "done": True,
    }
    monkeypatch.setattr(
        "oshell.providers.ollama.requests.post",
        lambda *a, **k: _FakeResp(json_data=response),
    )
    prov = OllamaProvider()
    tools = [{"type": "function", "function": {"name": "web_search"}}]
    chunks = list(prov.chat([Message(role="user", content="x")], model="m", tools=tools))
    assert len(chunks) == 1
    assert chunks[0].tool_calls[0].name == "web_search"
    assert chunks[0].tool_calls[0].arguments == {"query": "weather"}


def test_ollama_parses_stringified_arguments(monkeypatch):
    response = {
        "message": {
            "tool_calls": [
                {"function": {"name": "t", "arguments": '{"a": 1}'}}  # arguments as JSON string
            ]
        },
        "done": True,
    }
    monkeypatch.setattr(
        "oshell.providers.ollama.requests.post",
        lambda *a, **k: _FakeResp(json_data=response),
    )
    prov = OllamaProvider()
    chunks = list(prov.chat([Message(role="user")], model="m", tools=[{}]))
    assert chunks[0].tool_calls[0].arguments == {"a": 1}


# ── Live smoke test (skips when Ollama is not running) ──────────────────────
def _ollama_up() -> bool:
    try:
        return OllamaProvider().health()
    except Exception:
        return False


@pytest.mark.skipif(not _ollama_up(), reason="Ollama server not reachable")
def test_ollama_live_list_models():
    models = OllamaProvider().list_models()
    assert isinstance(models, list)


def test_ollama_list_models_info_carries_badges(monkeypatch):
    data = {
        "models": [
            {
                "name": "gemma4:26b",
                "details": {"parameter_size": "26B", "quantization_level": "Q8_0"},
            },
            {"name": "bare-model"},
        ]
    }
    monkeypatch.setattr(
        "oshell.providers.ollama.requests.get", lambda *a, **k: _FakeResp(json_data=data)
    )
    infos = OllamaProvider().list_models_info()
    assert infos[0] == {"name": "gemma4:26b", "size": "26B", "quant": "Q8_0"}
    assert infos[1] == {"name": "bare-model"}  # missing details tolerated


def test_base_list_models_info_falls_back_to_names():
    from oshell.providers.base import ChatChunk, LLMProvider

    class _P(LLMProvider):
        name = "p"

        def list_models(self):
            return ["a", "b"]

        def chat(self, messages, **kwargs):
            yield ChatChunk(content="", done=True)

    assert _P().list_models_info() == [{"name": "a"}, {"name": "b"}]


def test_ollama_max_context_from_model_info(monkeypatch):
    show = {
        "capabilities": ["completion", "tools"],
        "model_info": {"general.architecture": "gemma3", "gemma3.context_length": 131072},
    }
    monkeypatch.setattr(
        "oshell.providers.ollama.requests.post", lambda *a, **k: _FakeResp(json_data=show)
    )
    prov = OllamaProvider()
    assert prov.max_context("gemma3:27b") == 131072
    # One /api/show serves both capabilities and max_context (cached).
    assert prov.capabilities("gemma3:27b") == {"completion", "tools"}


def test_ollama_max_context_unknown(monkeypatch):
    monkeypatch.setattr(
        "oshell.providers.ollama.requests.post", lambda *a, **k: _FakeResp(json_data={})
    )
    assert OllamaProvider().max_context("mystery") is None


# ── model management: pull / delete ──────────────────────────────────────────


def test_ollama_pull_streams_progress_and_drops_show_cache(monkeypatch):
    lines = [
        json.dumps({"status": "pulling manifest"}).encode(),
        json.dumps({"status": "pulling abc123", "total": 100, "completed": 50}).encode(),
        json.dumps({"status": "success"}).encode(),
    ]
    monkeypatch.setattr(
        "oshell.providers.ollama.requests.post", lambda *a, **k: _FakeResp(lines=lines)
    )
    prov = OllamaProvider()
    prov._show_cache["m"] = {"capabilities": ["stale"]}  # re-pull must invalidate
    steps = list(prov.pull_model("m"))
    assert [s.status for s in steps] == ["pulling manifest", "pulling abc123", "success"]
    assert steps[1].percent == 50.0
    assert steps[0].percent is None  # no byte counts on bookkeeping steps
    assert "m" not in prov._show_cache


def test_ollama_pull_raises_on_midstream_error(monkeypatch):
    lines = [
        json.dumps({"status": "pulling manifest"}).encode(),
        json.dumps({"error": "pull model manifest: file does not exist"}).encode(),
    ]
    monkeypatch.setattr(
        "oshell.providers.ollama.requests.post", lambda *a, **k: _FakeResp(lines=lines)
    )
    with pytest.raises(RuntimeError, match="file does not exist"):
        list(OllamaProvider().pull_model("nope"))


def test_ollama_pull_raises_on_http_error(monkeypatch):
    monkeypatch.setattr(
        "oshell.providers.ollama.requests.post",
        lambda *a, **k: _FakeResp(status_code=500, json_data={"error": "registry unreachable"}),
    )
    with pytest.raises(RuntimeError, match="registry unreachable"):
        list(OllamaProvider().pull_model("m"))


def test_ollama_delete_and_cache_invalidation(monkeypatch):
    captured = {}

    def fake_delete(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return _FakeResp(status_code=200)

    monkeypatch.setattr("oshell.providers.ollama.requests.delete", fake_delete)
    prov = OllamaProvider()
    prov._show_cache["old:7b"] = {}
    prov.delete_model("old:7b")
    assert captured["url"].endswith("/api/delete")
    assert captured["json"] == {"model": "old:7b"}
    assert "old:7b" not in prov._show_cache


def test_ollama_delete_missing_model_raises(monkeypatch):
    monkeypatch.setattr(
        "oshell.providers.ollama.requests.delete",
        lambda *a, **k: _FakeResp(status_code=404, json_data={"error": "model 'x' not found"}),
    )
    with pytest.raises(RuntimeError, match="not found"):
        OllamaProvider().delete_model("x")


def test_model_management_gating():
    from oshell.providers.base import ChatChunk, LLMProvider

    class _P(LLMProvider):
        name = "p"

        def list_models(self):
            return []

        def chat(self, messages, **kwargs):
            yield ChatChunk(content="", done=True)

    p = _P()
    assert not p.supports_model_management()
    with pytest.raises(NotImplementedError):
        list(p.pull_model("m"))
    with pytest.raises(NotImplementedError):
        p.delete_model("m")
    assert OllamaProvider().supports_model_management()


def test_ollama_disk_size_badge(monkeypatch):
    data = {"models": [{"name": "m", "size": 17_700_000_000}]}
    monkeypatch.setattr(
        "oshell.providers.ollama.requests.get", lambda *a, **k: _FakeResp(json_data=data)
    )
    infos = OllamaProvider().list_models_info()
    assert infos[0]["disk"] == "16.5 GB"


def test_ollama_chat_passes_num_ctx(monkeypatch):
    captured = {}

    def fake_post(url, json=None, stream=False, timeout=None):
        captured.update(json)
        lines = [b'{"message": {"content": "ok"}, "done": true}']
        return _FakeResp(lines=lines)

    monkeypatch.setattr("oshell.providers.ollama.requests.post", fake_post)
    prov = OllamaProvider()
    list(prov.chat([Message(role="user", content="hi")], model="m", num_ctx=32768))
    assert captured["options"]["num_ctx"] == 32768
    # And without it, Ollama's own default is left alone.
    captured.clear()
    list(prov.chat([Message(role="user", content="hi")], model="m"))
    assert "num_ctx" not in captured["options"]
