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


def format_profile_data(profile: dict[str, Any] | None, language: str = "ru") -> str:
    if not profile:
        if language == "en":
            return "I don’t have any saved data yet. Tell me your name, age, sex, height, weight, goal, and activity level."
        return "Пока у меня нет сохранённых данных о вас. Расскажите имя, возраст, пол, рост, вес, цель и активность."
    labels_ru = {
        "name": "имя",
        "age": "возраст",
        "sex": "пол",
        "height_cm": "рост",
        "weight_kg": "вес",
        "goal": "цель",
        "activity_level": "активность",
        "training_place": "место тренировок",
        "training_experience": "уровень подготовки",
        "training_days_per_week": "тренировочных дней в неделю",
        "available_equipment": "оборудование",
        "target_kcal": "калории",
        "protein_g": "белки",
        "fat_g": "жиры",
        "carbs_g": "углеводы",
    }
    labels_en = {
        "name": "name",
        "age": "age",
        "sex": "sex",
        "height_cm": "height",
        "weight_kg": "weight",
        "goal": "goal",
        "activity_level": "activity",
        "training_place": "training place",
        "training_experience": "training level",
        "training_days_per_week": "training days per week",
        "available_equipment": "equipment",
        "target_kcal": "calories",
        "protein_g": "protein",
        "fat_g": "fat",
        "carbs_g": "carbohydrates",
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
    translations_ru = {
        "male": "мужской",
        "female": "женский",
        "weight_loss": "снижение веса",
        "muscle_gain": "набор мышечной массы",
        "maintenance": "поддержание формы",
        "wellbeing": "улучшение самочувствия",
        "sedentary": "низкая",
        "light": "лёгкая",
        "moderate": "умеренная",
        "high": "высокая",
        "very_high": "очень высокая",
        "home": "дома",
        "gym": "спортзал",
        "both": "несколько мест",
        "outdoors": "улица или парк",
        "beginner": "новичок",
        "intermediate": "опытный",
        "advanced": "продвинутый",
    }
    translations_en = {
        "male": "male",
        "female": "female",
        "weight_loss": "weight loss",
        "muscle_gain": "muscle gain",
        "maintenance": "maintenance",
        "wellbeing": "improved wellbeing",
        "sedentary": "sedentary",
        "light": "light",
        "moderate": "moderate",
        "high": "high",
        "very_high": "very high",
        "home": "home",
        "gym": "gym",
        "both": "multiple places",
        "outdoors": "outdoors",
        "beginner": "beginner",
        "intermediate": "intermediate",
        "advanced": "advanced",
    }
    labels = labels_en if language == "en" else labels_ru
    translations = translations_en if language == "en" else translations_ru
    values = [
        f"{labels[key]} — {(', '.join(item.replace('_', ' ') for item in profile[key]) if key == 'available_equipment' and isinstance(profile[key], list) else translations.get(str(profile[key]), profile[key]))}{suffixes.get(key, '')}"
        for key in labels
        if profile.get(key) not in (None, "", [])
    ]
    prefix = "Saved data: " if language == "en" else "Сохранённые данные: "
    return prefix + ", ".join(values) + "."
