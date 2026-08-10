from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.agent.state import NutritionTargets, UserProfile


PROFILE_FIELDS = (
    "name",
    "age",
    "sex",
    "height_cm",
    "weight_kg",
    "goal",
    "activity_level",
)

BOUNDED_AGENT_INTENTS = {"nutrition_targets", "meal_plan", "workout_plan"}


def build_complete_profile(data: dict[str, Any] | None) -> UserProfile | None:
    """Build a validated profile only after all calculation inputs are known."""
    if not data or any(data.get(field) in (None, "") for field in PROFILE_FIELDS):
        return None
    try:
        return UserProfile.model_validate(data)
    except ValidationError:
        return None


def target_facts(targets: NutritionTargets) -> dict[str, int]:
    return {
        "target_kcal": targets.target_kcal,
        "protein_g": targets.protein_g,
        "fat_g": targets.fat_g,
        "carbs_g": targets.carbs_g,
    }


def should_use_bounded_agent(intent: str, profile: UserProfile | None) -> bool:
    return profile is not None and intent in BOUNDED_AGENT_INTENTS


def public_profile_context(profile: dict[str, Any] | None) -> dict[str, Any]:
    hidden = {
        "user_id",
        "expires_at",
        "created_at",
        "updated_at",
        "last_active_at",
        "deletion_requested_at",
    }
    return {key: value for key, value in (profile or {}).items() if key not in hidden}


def format_profile_data(profile: dict[str, Any] | None) -> str:
    if not profile:
        return "Пока у меня нет сохранённых данных о вас. Расскажите имя, возраст, пол, рост, вес, цель и активность."
    labels = {
        "name": "имя",
        "age": "возраст",
        "sex": "пол",
        "height_cm": "рост",
        "weight_kg": "вес",
        "goal": "цель",
        "activity_level": "активность",
        "target_kcal": "калории",
        "protein_g": "белки",
        "fat_g": "жиры",
        "carbs_g": "углеводы",
    }
    suffixes = {
        "age": " лет",
        "height_cm": " см",
        "weight_kg": " кг",
        "target_kcal": " ккал",
        "protein_g": " г",
        "fat_g": " г",
        "carbs_g": " г",
    }
    values = [
        f"{labels[key]} — {profile[key]}{suffixes.get(key, '')}"
        for key in labels
        if profile.get(key) not in (None, "", [])
    ]
    return "Сохранённые данные: " + ", ".join(values) + "."
