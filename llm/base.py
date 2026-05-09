"""
llm/base.py — LLM 客户端抽象基类
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    stop_reason: str = ""


@dataclass
class UsageRecord:
    stage: str
    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class BaseLLMClient(ABC):
    """所有 LLM 客户端必须实现的接口。"""

    @abstractmethod
    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 8000,
        temperature: float = 0.75,
    ) -> LLMResponse:
        ...
