from __future__ import annotations

import asyncio
import json

from app.agent.state import NutritionTargets, UserProfile
from app.providers.prompts import SYSTEM_PROMPT


class GeminiGenerator:
    """Gemini Interactions API adapter for the Generator role."""

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def generate(
        self,
        profile: UserProfile,
        message: str,
        targets: NutritionTargets,
        knowledge: list[str],
        history: list[dict[str, str]],
        feedback: list[str] | None = None,
    ) -> str:
        payload = {
            "system_instruction": SYSTEM_PROMPT,
            "profile": profile.model_dump(mode="json"),
            "verified_targets": targets.model_dump(mode="json"),
            "user_request": message,
            "knowledge": knowledge,
            "recent_conversation": history,
            "judge_feedback": feedback or [],
        }
        interaction = await asyncio.to_thread(
            self.client.interactions.create,
            model=self.model,
            input=json.dumps(payload, ensure_ascii=False),
            generation_config={"thinking_level": "minimal"},
            store=False,
        )
        return interaction.output_text or "Не удалось получить текстовую рекомендацию."
