"""Tests for the layered configuration loader."""

from __future__ import annotations

import json

from oshell.config import Config, update_local_config


def test_defaults_are_sane():
    cfg = Config()
    assert cfg.provider.name == "ollama"
    assert cfg.provider.host.startswith("http")
    assert cfg.max_tool_iterations > 0
    assert cfg.enabled_tools == ["*"]


def test_file_layering(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"default_model": "base-model"}))
    (tmp_path / "config.local.json").write_text(
        json.dumps({"default_model": "local-model", "temperature": 0.1})
    )
    cfg = Config.load(tmp_path)
    # config.local.json overrides config.json
    assert cfg.default_model == "local-model"
    assert cfg.temperature == 0.1


def test_env_overrides_files(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text(json.dumps({"default_model": "from-file"}))
    monkeypatch.setenv("OSHELL_DEFAULT_MODEL", "from-env")
    monkeypatch.setenv("OSHELL_TEMPERATURE", "0.42")
    monkeypatch.setenv("OSHELL_PROVIDER__HOST", "http://remote:11434")
    cfg = Config.load(tmp_path)
    assert cfg.default_model == "from-env"          # env beats file
    assert cfg.temperature == 0.42                  # coerced to float
    assert cfg.provider.host == "http://remote:11434"  # nested via __


def test_env_bool_coercion(tmp_path, monkeypatch):
    monkeypatch.setenv("OSHELL_VERBOSE", "true")
    cfg = Config.load(tmp_path)
    assert cfg.verbose is True


def test_update_local_config_merges_and_persists(tmp_path):
    # Pre-existing local config with Atlassian creds must be preserved.
    (tmp_path / "config.local.json").write_text(
        json.dumps({"atlassian": {"jira_url": "https://j", "jira_token": "t"}})
    )
    update_local_config({"default_model": "picked-model"}, root=tmp_path)
    cfg = Config.load(tmp_path)
    assert cfg.default_model == "picked-model"      # new value persisted
    assert cfg.atlassian.jira_url == "https://j"    # existing value untouched


def test_update_local_config_creates_file(tmp_path):
    update_local_config({"default_model": "m"}, root=tmp_path)
    assert (tmp_path / "config.local.json").is_file()
    assert Config.load(tmp_path).default_model == "m"


def test_roundtrip_save_load(tmp_path):
    cfg = Config(default_model="round-trip", temperature=0.9)
    out = tmp_path / "config.local.json"
    cfg.save(out)
    reloaded = Config.load(tmp_path)
    assert reloaded.default_model == "round-trip"
    assert reloaded.temperature == 0.9
