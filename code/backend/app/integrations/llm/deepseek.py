"""Bounded DeepSeek analysis; no credentials or account identifiers enter prompts."""

import json

import httpx

from app.core.config import Settings


class AnalysisUnavailable(Exception):
    pass


class DeepSeekClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def complete(self, system_prompt: str, evidence: dict, *, max_tokens: int) -> str:
        key = self.settings.deepseek_api_key.get_secret_value().strip()
        if not key:
            raise AnalysisUnavailable("学习建议暂不可用，请稍后重试。")
        try:
            with httpx.Client(timeout=self.settings.deepseek_timeout) as client:
                response = client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": self.settings.deepseek_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": json.dumps(evidence, ensure_ascii=False)},
                        ],
                        "response_format": {"type": "json_object"},
                        "thinking": {"type": "disabled"},
                        "max_tokens": max_tokens,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                choice = response.json()["choices"][0]
                if choice.get("finish_reason") != "stop":
                    raise ValueError("Incomplete response")
                content = choice["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("Empty response")
                return content
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            # Never return upstream bodies, headers, API keys or raw model errors.
            raise AnalysisUnavailable(
                "学习建议暂不可用，请稍后重试。"
            ) from None
