"""
llm/__init__.py — 根据 config 创建 LLM 客户端实例
"""
from __future__ import annotations

from .base import BaseLLMClient, LLMResponse, UsageRecord
from .anthropic_client import AnthropicClient


def make_client(config: dict) -> BaseLLMClient:
    model_cfg = config.get("model", {})
    provider = model_cfg.get("provider", "anthropic").lower()

    if provider == "anthropic":
        return AnthropicClient(
            model=model_cfg.get("name", "claude-opus-4-5"),
            max_retries=model_cfg.get("max_retries", 3),
            retry_base_delay=model_cfg.get("retry_base_delay", 2.0),
            timeout=model_cfg.get("timeout", 120.0),
        )
    else:
        raise NotImplementedError(f"暂不支持 provider: {provider}。目前支持: anthropic")


__all__ = ["BaseLLMClient", "LLMResponse", "UsageRecord", "AnthropicClient", "make_client"]
