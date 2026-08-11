from __future__ import annotations


def route_intent(message: str) -> str:
    """Deterministic intent router for the known fitness workflows."""
    text = message.casefold()
    adjustment_words = (
        "добавить в рацион", "учесть в рационе", "хочу съесть", "хочу есть",
        "люблю есть", "сладост", "шоколад", "зефир", "маршмеллоу",
        "marshmallow", "zephyr", "chocolate",
    )
    meal_words = ("меню", "рацион", "питан", "блюд", "продукт", "meal plan", "menu")
    workout_words = ("трениров", "упражнен", "подход", "повтор", "workout", "exercise")
    target_words = ("калори", "кбжу", "бжу", "белк", "жир", "углевод", "macros")

    has_meal = any(word in text for word in meal_words)
    has_workout = any(word in text for word in workout_words)
    has_targets = any(word in text for word in target_words)
    if has_workout and (has_meal or has_targets):
        return "ambiguous_workflow"
    if any(word in text for word in adjustment_words):
        return "meal_adjustment"
    if has_targets:
        return "nutrition_targets"
    if has_meal:
        return "meal_plan"
    if has_workout:
        return "workout_plan"
    if any(word in text for word in ("объём", "прогресс", "сон", "мой вес", "вес сегодня")):
        return "progress"
    return "general_coaching"
