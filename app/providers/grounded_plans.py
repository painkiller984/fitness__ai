from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from app.agent.state import NutritionTargets


@dataclass(frozen=True, slots=True)
class GroundedPlan:
    markdown: str
    sources: tuple[str, ...]

    def render(self, language: str = "ru") -> str:
        heading = "Sources" if language == "en" else "Источники"
        links = "\n".join(f"- {url}" for url in self.sources[:5])
        return f"{self.markdown}\n\n**{heading}:**\n{links}"


class GeminiGroundedPlanSearch:
    """Build personalized plans with Google Search grounding and explicit sources."""

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def workout(
        self, profile: dict[str, Any], language: str = "ru"
    ) -> GroundedPlan | None:
        prompt = (
            "Use Google Search and reliable sources such as ACSM, WHO, government health services, "
            "and peer-reviewed sports medicine literature. Create a practical personalized workout plan. "
            "The plan must explicitly use sex, training experience, goal, training location, health limitations, "
            "and available equipment when provided. Do not use the same exercise order for every person. "
            "For beginners prefer a simple learnable program; for intermediate and advanced users use suitable "
            "volume, progression, and recovery. Explain warm-up, sets, repetitions, rest, progression, and deload "
            "when appropriate. If pain, injury, pregnancy, or disease is present, advise consulting a relevant "
            "clinician and avoid presenting painful movements as mandatory. Do not diagnose. "
            f"Write the plan in {'English' if language == 'en' else 'Russian'}. "
            "Return JSON only with keys plan_markdown and sources. sources must be an array of direct source URLs. "
            f"User profile: {json.dumps(_safe_profile(profile), ensure_ascii=False)}"
        )
        return await self._generate(prompt)

    async def menu(
        self,
        profile: dict[str, Any],
        targets: NutritionTargets,
        language: str = "ru",
    ) -> GroundedPlan | None:
        prompt = (
            "Use Google Search and reliable nutrition sources such as government food databases, national health "
            "services, and reputable dietetic guidance. Create one varied personalized day menu with exact ingredient "
            "weights and 2 alternatives for each meal. Respect allergies, dietary restrictions, saved dislikes, "
            "preferences, goal, and sex. The deterministic nutrition target below is authoritative: keep total calories "
            "within 5 percent and make protein, fat, and carbohydrate totals as close as practical. Show estimated "
            "calories and P/F/C for every meal and the day total. Do not claim medical treatment. "
            f"Write the menu in {'English' if language == 'en' else 'Russian'}. "
            "Return JSON only with keys plan_markdown and sources. sources must be an array of direct source URLs. "
            f"User profile: {json.dumps(_safe_profile(profile), ensure_ascii=False)}. "
            f"Authoritative target: {json.dumps(targets.model_dump(), ensure_ascii=False)}"
        )
        return await self._generate(prompt)

    async def _generate(self, prompt: str) -> GroundedPlan | None:
        try:
            interaction = await asyncio.to_thread(
                self.client.interactions.create,
                model=self.model,
                input=prompt,
                tools=[{"type": "google_search"}],
                generation_config={"thinking_level": "minimal"},
                store=False,
            )
        except Exception:
            return None
        return parse_grounded_plan(interaction.output_text or "")


def parse_grounded_plan(raw: str) -> GroundedPlan | None:
    try:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            return None
        data = json.loads(raw[start : end + 1])
        markdown = str(data.get("plan_markdown") or "").strip()
        sources = tuple(
            dict.fromkeys(
                str(url).strip()
                for url in data.get("sources", [])
                if str(url).startswith(("https://", "http://"))
            )
        )
        if len(markdown) < 80 or not sources:
            return None
        return GroundedPlan(markdown, sources)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _safe_profile(profile: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "name",
        "age",
        "sex",
        "height_cm",
        "weight_kg",
        "goal",
        "activity_level",
        "training_place",
        "training_experience",
        "training_days_per_week",
        "available_equipment",
        "dietary_preferences",
        "allergies",
        "injuries",
        "medical_notes",
        "is_pregnant",
    }
    return {key: value for key, value in profile.items() if key in allowed}
