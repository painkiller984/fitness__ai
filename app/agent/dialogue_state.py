from __future__ import annotations

from typing import Any


WORKFLOW_INTENTS = {
    "nutrition_targets": "nutrition_targets",
    "meal_plan": "meal_plan",
    "workout_plan": "workout_plan",
    "meal_adjustment": "meal_feedback",
}

NUTRITION_FIELDS = {
    "age",
    "sex",
    "height_cm",
    "weight_kg",
    "goal",
    "activity_level",
}
WORKOUT_FIELDS = {
    "sex",
    "goal",
    "training_place",
    "training_experience",
    "training_days_per_week",
    "available_equipment",
    "equipment_screened",
    "health_screened",
    "injuries",
    "medical_notes",
    "is_pregnant",
}


def requested_workflow(intent: str) -> str | None:
    """Map a routed intent to an explicit, mutually exclusive workflow."""
    return WORKFLOW_INTENTS.get(intent)


def switch_workflow(state: dict[str, Any], workflow: str | None) -> None:
    """Replace unfinished dialogue state while preserving the persisted profile."""
    if state.get("active_workflow") == workflow:
        return
    state["active_workflow"] = workflow
    state["pending_facts"] = {}


def allowed_profile_fields(workflow: str | None, stage_key: str | None) -> set[str]:
    """Return fields that may be persisted from the current user turn."""
    if stage_key == "name":
        return {"name", "surname"}
    if workflow in {"nutrition_targets", "meal_plan"}:
        return set(NUTRITION_FIELDS)
    if workflow == "workout_plan":
        return set(WORKOUT_FIELDS)
    if workflow == "meal_feedback":
        return {"dietary_preferences", "allergies"}
    return set()


def filter_profile_facts(
    facts: dict[str, Any], workflow: str | None, stage_key: str | None
) -> dict[str, Any]:
    allowed = allowed_profile_fields(workflow, stage_key)
    if stage_key == "name" and facts.get("name"):
        # The name gate is still mandatory, but a user may naturally provide their
        # other profile details in the same message. Keep those explicit facts
        # instead of forcing them to type the same information a second time.
        allowed |= NUTRITION_FIELDS | WORKOUT_FIELDS
    return {key: value for key, value in facts.items() if key in allowed}


def enforce_name_gate(reply: str, language: str) -> str:
    """Keep the LLM's natural reaction but enforce the non-skippable name question."""
    text = reply.strip()
    markers = ("name", "what should i call", "what's your name") if language == "en" else (
        "имя",
        "как тебя зовут",
        "как вас зовут",
    )
    if any(marker in text.casefold() for marker in markers):
        return text
    question = "What is your name?" if language == "en" else "Как тебя зовут?"
    return f"{text}\n\n{question}" if text else question


def workflow_choice(name: str | None, language: str) -> str:
    display_name = (name or "").strip()
    if language == "en":
        greeting = f"Nice to meet you, {display_name}!" if display_name else "Nice to meet you!"
        return f"{greeting} What shall we do first: calculate calories and macros or build a workout plan?"
    greeting = f"Приятно познакомиться, {display_name}!" if display_name else "Приятно познакомиться!"
    return f"{greeting} Что сделаем сначала: рассчитаем КБЖУ или составим план тренировок?"
