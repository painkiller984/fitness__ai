from __future__ import annotations

from app.agent.state import ActivityLevel, Goal, NutritionTargets, Sex, UserProfile


ACTIVITY_FACTORS: dict[ActivityLevel, float] = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHT: 1.375,
    ActivityLevel.MODERATE: 1.55,
    ActivityLevel.HIGH: 1.725,
    ActivityLevel.VERY_HIGH: 1.9,
}

GOAL_FACTORS: dict[Goal, float] = {
    Goal.WEIGHT_LOSS: 0.85,
    Goal.MUSCLE_GAIN: 1.10,
    Goal.MAINTENANCE: 1.0,
    Goal.WELLBEING: 1.0,
}

PROTEIN_PER_KG: dict[Goal, float] = {
    Goal.WEIGHT_LOSS: 1.8,
    Goal.MUSCLE_GAIN: 1.8,
    Goal.MAINTENANCE: 1.6,
    Goal.WELLBEING: 1.4,
}


def calculate_nutrition_targets(profile: UserProfile) -> NutritionTargets:
    """Return an estimate, not a medical prescription.

    Uses Mifflin-St Jeor for BMR and conservative goal adjustments. Strict
    arithmetic lives here so an LLM can never invent the numbers.
    """
    sex_offset = 5 if profile.sex == Sex.MALE else -161
    bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + sex_offset
    maintenance = bmr * ACTIVITY_FACTORS[profile.activity_level]
    raw_target = maintenance * GOAL_FACTORS[profile.goal]

    warnings: list[str] = []
    screening_floor = 1500 if profile.sex == Sex.MALE else 1200
    if raw_target < screening_floor:
        warnings.append(
            "Расчёт достиг нижнего защитного порога. Не снижайте калорийность без консультации специалиста."
        )
    target = max(raw_target, screening_floor)

    protein = profile.weight_kg * PROTEIN_PER_KG[profile.goal]
    fat = max(profile.weight_kg * 0.8, target * 0.20 / 9)
    carbs = max((target - protein * 4 - fat * 9) / 4, 0)

    return NutritionTargets(
        bmr_kcal=round(bmr),
        maintenance_kcal=round(maintenance),
        target_kcal=round(target),
        protein_g=round(protein),
        fat_g=round(fat),
        carbs_g=round(carbs),
        warnings=warnings,
    )


def validate_targets(targets: NutritionTargets, tolerance_kcal: int = 60) -> list[str]:
    macro_kcal = targets.protein_g * 4 + targets.fat_g * 9 + targets.carbs_g * 4
    problems: list[str] = []
    if abs(macro_kcal - targets.target_kcal) > tolerance_kcal:
        problems.append("Сумма калорий из БЖУ не совпадает с целевой калорийностью.")
    if min(targets.protein_g, targets.fat_g, targets.carbs_g) < 0:
        problems.append("Значения БЖУ не могут быть отрицательными.")
    return problems
