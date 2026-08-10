from __future__ import annotations

import asyncio
import json
from typing import Protocol

from app.agent.state import JudgeResult, NutritionTargets, UserProfile
from app.providers.openai_compatible import OpenAICompatibleClient
from app.tools.calorie_macros import validate_targets


class PlanJudge(Protocol):
    async def judge(
        self, profile: UserProfile, message: str, targets: NutritionTargets, draft: str
    ) -> JudgeResult: ...


class DeterministicPlanJudge:
    async def judge(
        self, profile: UserProfile, message: str, targets: NutritionTargets, draft: str
    ) -> JudgeResult:
        violations = validate_targets(targets)
        allergy_hits = [item for item in profile.allergies if item.casefold() in draft.casefold()]
        if allergy_hits and "аллерг" not in draft.casefold():
            violations.append("Ответ потенциально предлагает указанный аллерген.")
        return JudgeResult(verdict="block" if violations else "approve", violations=violations)


class GeminiPlanJudge:
    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def judge(
        self, profile: UserProfile, message: str, targets: NutritionTargets, draft: str
    ) -> JudgeResult:
        payload = {
            "instruction": (
                "Проверь ответ на соответствие цели, расчётам, аллергиям, травмам и запрету "
                "медицинских назначений. approve — безопасно; revise — исправимо; block — опасно."
            ),
            "profile": profile.model_dump(mode="json"),
            "verified_targets": targets.model_dump(mode="json"),
            "request": message,
            "draft": draft,
        }
        interaction = await asyncio.to_thread(
            self.client.interactions.create,
            model=self.model,
            input=json.dumps(payload, ensure_ascii=False),
            generation_config={"thinking_level": "minimal"},
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": JudgeResult.model_json_schema(),
            },
            store=False,
        )
        try:
            return JudgeResult.model_validate_json(interaction.output_text)
        except Exception:
            return JudgeResult(
                verdict="block", violations=["Gemini Judge не вернул проверяемый результат."]
            )


class OpenAICompatiblePlanJudge:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.client = OpenAICompatibleClient(base_url, api_key, model)

    async def judge(
        self, profile: UserProfile, message: str, targets: NutritionTargets, draft: str
    ) -> JudgeResult:
        content = await self.client.complete(
            (
                "Ты — строгий контролёр качества фитнес-рекомендаций. Проверь ответ на "
                "соответствие цели, расчётам, аллергиям, травмам и запрету медицинских назначений. "
                "Верни ТОЛЬКО JSON: {verdict: approve|revise|block, violations: string[], "
                "revision_instructions: string[]}."
            ),
            {
                "profile": profile.model_dump(mode="json"),
                "verified_targets": targets.model_dump(mode="json"),
                "request": message,
                "draft": draft,
            },
        )
        try:
            return JudgeResult.model_validate_json(content)
        except Exception:
            return JudgeResult(
                verdict="block", violations=["Judge не вернул проверяемый JSON."]
            )
