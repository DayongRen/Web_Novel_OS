"""
llm/anthropic_client.py — Anthropic Claude 客户端（带重试、成本统计）
"""
from __future__ import annotations

import os
import time
from typing import Optional

import anthropic
from dotenv import load_dotenv

from .base import BaseLLMClient, LLMResponse

load_dotenv()

# Claude 定价（USD per 1M tokens，2024-12）
_PRICING: dict[str, dict] = {
    "claude-opus-4-5":    {"input": 15.0,  "output": 75.0},
    "claude-sonnet-4-5":  {"input": 3.0,   "output": 15.0},
    "claude-haiku-3-5":   {"input": 0.8,   "output": 4.0},
    "claude-opus-4-0":    {"input": 15.0,  "output": 75.0},
    "claude-sonnet-4-0":  {"input": 3.0,   "output": 15.0},
}

_DEFAULT_PRICING = {"input": 3.0, "output": 15.0}


def _calc_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = _PRICING.get(model, _DEFAULT_PRICING)
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000


class AnthropicClient(BaseLLMClient):
    def __init__(
        self,
        model: str = "claude-opus-4-5",
        max_retries: int = 3,
        retry_base_delay: float = 2.0,
        timeout: float = 120.0,
    ):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY 未设置，请在 .env 文件中配置。")
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        self.model = model
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.call_count = 0

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 8000,
        temperature: float = 0.75,
    ) -> LLMResponse:
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                msg = self._client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                texts = [
                    block.text
                    for block in msg.content
                    if getattr(block, "type", None) == "text"
                ]
                if not texts:
                    raise RuntimeError("LLM 返回了空响应（无 text block）")

                in_tok = msg.usage.input_tokens
                out_tok = msg.usage.output_tokens
                cost = _calc_cost(self.model, in_tok, out_tok)

                self.total_input_tokens += in_tok
                self.total_output_tokens += out_tok
                self.total_cost_usd += cost
                self.call_count += 1

                return LLMResponse(
                    text="\n".join(texts),
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    model=self.model,
                    stop_reason=str(msg.stop_reason),
                )

            except anthropic.RateLimitError as e:
                last_error = e
                delay = self.retry_base_delay * (2 ** attempt)
                time.sleep(delay)

            except anthropic.APIStatusError as e:
                if e.status_code >= 500:
                    last_error = e
                    delay = self.retry_base_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    raise

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_base_delay)
                else:
                    raise

        raise RuntimeError(f"LLM 调用在 {self.max_retries} 次重试后仍失败: {last_error}") from last_error

    def cost_summary(self) -> dict:
        return {
            "call_count": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "model": self.model,
        }
