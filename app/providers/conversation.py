from __future__ import annotations

import asyncio
import json
from typing import Protocol

from app.providers.openai_compatible import OpenAICompatibleClient
from app.providers.prompts import CHAT_SYSTEM_PROMPT


class ConversationResponder(Protocol):
    async def respond(self, message: str, history: list[dict[str, str]], profile: dict | None = None) -> str: ...


class GeminiConversationResponder:
    """Free-form conversational layer backed by the Gemini Interactions API."""

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def respond(self, message: str, history: list[dict[str, str]], profile: dict | None = None) -> str:
        interaction = await asyncio.to_thread(
            self.client.interactions.create,
            model=self.model,
            input=json.dumps(
                {
                    "system_instruction": CHAT_SYSTEM_PROMPT,
                    "conversation": history,
                    "user_message": message,
                    "persistent_profile": profile or {},
                },
                ensure_ascii=False,
            ),
            generation_config={"thinking_level": "minimal"},
            store=False,
        )
        return interaction.output_text or "Не удалось получить ответ от модели."


class OpenAICompatibleConversationResponder:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.client = OpenAICompatibleClient(base_url, api_key, model)

    async def respond(self, message: str, history: list[dict[str, str]], profile: dict | None = None) -> str:
        return await self.client.complete(
            CHAT_SYSTEM_PROMPT,
            {"conversation": history, "user_message": message, "persistent_profile": profile or {}},
        )


class DeterministicConversationResponder:
    async def respond(self, message: str, history: list[dict[str, str]], profile: dict | None = None) -> str:
        return (
            "Здравствуйте! Я Forma — помощник по тренировкам, питанию и расчёту калорий. "
            "Чтобы ответы были свободными и персональными, добавьте ключ Gemini в AI_API_KEY."
        )
