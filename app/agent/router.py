from __future__ import annotations


def route_intent(message: str) -> str:
    """Deterministic intent router for the known fitness workflows."""
    text = message.casefold()
    routes = (
        ("meal_plan", ("меню", "питан", "блюд", "продукт")),
        ("workout_plan", ("трениров", "упражнен", "подход", "повтор")),
        ("progress", ("вес", "объём", "прогресс", "сон")),
        ("nutrition_targets", ("калори", "бжу", "белк", "жир", "углевод")),
    )
    for intent, words in routes:
        if any(word in text for word in words):
            return intent
    return "general_coaching"
