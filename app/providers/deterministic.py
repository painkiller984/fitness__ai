from __future__ import annotations

from app.agent.state import NutritionTargets, UserProfile


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
