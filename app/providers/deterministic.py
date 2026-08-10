from __future__ import annotations

from app.agent.state import NutritionTargets, UserProfile
from app.agent.language import response_language


class DeterministicGenerator:
    """Safe local fallback when an AI provider is not configured."""

    async def generate(
        self,
        profile: UserProfile,
        message: str,
        targets: NutritionTargets,
        knowledge: list[str],
        history: list[dict[str, str]],
        feedback: list[str] | None = None,
    ) -> str:
        if response_language(message) == "en":
            return (
                f"{profile.name}, your estimated daily target is {targets.target_kcal} kcal: "
                f"protein {targets.protein_g} g, fat {targets.fat_g} g, carbohydrates {targets.carbs_g} g. "
                "Use this as a starting point and review your progress and wellbeing over 2–3 weeks. "
                "This is general guidance, not medical advice."
            )
        greeting_words = ("привет", "здравств", "добрый", "hello")
        if any(word in message.casefold() for word in greeting_words):
            return "Здравствуйте! Чем помочь: питанием, тренировками, меню или отслеживанием прогресса?"
        restrictions = ", ".join(profile.allergies) if profile.allergies else "не указаны"
        context = f" {knowledge[0]}" if knowledge else ""
        return (
            f"{profile.name}, ориентировочная цель — {targets.target_kcal} ккал в сутки: "
            f"белки {targets.protein_g} г, жиры {targets.fat_g} г, углеводы {targets.carbs_g} г. "
            f"Указанные аллергии: {restrictions}. Начните с этого ориентира и оценивайте "
            f"динамику самочувствия и средних показателей за 2–3 недели.{context} "
            "Это справочная рекомендация, а не медицинское назначение."
        )
