"""Provider registry: turn a ``ProviderConfig`` into a live ``LLMProvider``."""

from __future__ import annotations

from ..config import Config, ProviderConfig
from .base import ChatChunk, LLMProvider, Message, ToolCall
from .ollama import OllamaProvider
from .openai_compat import OpenAICompatProvider

__all__ = [
    "ChatChunk",
    "LLMProvider",
    "Message",
    "ToolCall",
    "OllamaProvider",
    "OpenAICompatProvider",
    "get_provider",
]


def get_provider(config: Config | ProviderConfig) -> LLMProvider:
    """Construct the provider named in config. Accepts either a full ``Config``
    or a bare ``ProviderConfig``."""
    pc = config.provider if isinstance(config, Config) else config
    if pc.name == "ollama":
        return OllamaProvider(host=pc.host, timeout=pc.timeout)
    if pc.name == "openai":
        return OpenAICompatProvider(host=pc.host, api_key=pc.api_key, timeout=pc.timeout)
    if pc.name == "mlx":
        # MLX servers (mlx_lm.server) speak the OpenAI schema.
        return OpenAICompatProvider(host=pc.host, api_key=pc.api_key, timeout=pc.timeout)
    raise ValueError(f"Unknown provider '{pc.name}'. Expected one of: ollama, openai, mlx.")
