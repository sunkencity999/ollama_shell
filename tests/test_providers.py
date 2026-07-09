"""Provider tests: response parsing (mocked) + a live Ollama smoke test."""

from __future__ import annotations

import json

import pytest

from oshell.config import Config, ProviderConfig
from oshell.providers import OllamaProvider, OpenAICompatProvider, get_provider
from oshell.providers.base import Message


class _FakeResp:
    def __init__(self, *, json_data=None, lines=None):
        self._json = json_data
        self._lines = lines or []

    def raise_for_status(self):
        pass

    def json(self):
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
