from __future__ import annotations

import json
from typing import Any

import httpx

from app.agent.state import NutritionTargets, UserProfile
from app.providers.prompts import SYSTEM_PROMPT


class OpenAICompatibleClient:
    """Minimal Chat Completions client for OpenAI-compatible APIs and Ollama."""

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self.api_key = api_key
        self.model = model

    async def complete(self, system: str, user_payload: dict[str, Any]) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(self.endpoint, headers=headers, json=payload)
        if response.is_error:
            raise RuntimeError(f"AI provider returned HTTP {response.status_code}: {response.text[:300]}")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError("AI provider returned an unsupported Chat Completions response.") from exc
        if isinstance(content, list):
            return "".join(block.get("text", "") for block in content if isinstance(block, dict))
        return str(content or "")


class OpenAICompatibleGenerator:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.client = OpenAICompatibleClient(base_url, api_key, model)

    async def generate(
        self,
        profile: UserProfile,
        message: str,
        targets: NutritionTargets,
        knowledge: list[str],
        history: list[dict[str, str]],
        feedback: list[str] | None = None,
    ) -> str:
        return await self.client.complete(
            SYSTEM_PROMPT,
            {
                "profile": profile.model_dump(mode="json"),
                "verified_targets": targets.model_dump(mode="json"),
                "user_request": message,
                "knowledge": knowledge,
                "recent_conversation": history,
                "judge_feedback": feedback or [],
            },
        )
