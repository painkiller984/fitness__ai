from __future__ import annotations

from typing import Any


GYM = {
    "squat": "присед со штангой или жим ногами",
    "hinge": "румынская тяга",
    "push": "жим лёжа или жим гантелей",
    "pull": "тяга верхнего или горизонтального блока",
    "shoulders": "жим гантелей сидя и подъёмы в стороны",
    "glutes": "ягодичный мост или хип-траст",
}
HOME = {
    "squat": "гоблет-присед или присед с собственным весом",
    "hinge": "румынская тяга с гантелями или ягодичный мост",
    "push": "отжимания или жим гантелей на полу",
    "pull": "тяга гантели в наклоне или тяга резины",
    "shoulders": "жим гантелей стоя или подъёмы с резиной",
    "glutes": "ягодичный мост или болгарские выпады",
}


def build_workout_program(profile: dict[str, Any], language: str = "ru") -> str:
    """Assemble a bounded program; an LLM never invents the training framework."""
    if language == "en":
        return "The flexible workout library is currently provided in Russian. Please switch to Russian for a full program."

    place = str(profile.get("training_place") or "gym")
    library = HOME if place == "home" else GYM
    level = str(profile.get("training_experience") or "beginner")
    days = int(profile.get("training_days_per_week") or 3)
    days = min(max(days, 2), 4)
    focus = _focus(profile)
    goal = str(profile.get("goal") or "maintenance")
    sex = str(profile.get("sex") or "male")
    health_note = _health_note(profile)
    schedule = "2 тренировки" if days == 2 else f"{days} тренировки"

    if level == "beginner":
        body = _full_body(library, days, goal, focus)
        heading = "Новичок: full-body, первые 4 недели"
    else:
        body = _split(library, days, level, goal, focus)
        heading = "Опытный: сплит" if level == "intermediate" else "Продвинутый: сплит с прогрессией"
    default_focus = "верх тела" if sex == "male" else "ноги и ягодицы"
    focus_line = f"Акцент: {focus or default_focus}."
    progression = _progression(level, goal)
    return "\n\n".join([
        f"**{heading}** — {schedule} в неделю, место: {'дом' if place == 'home' else 'зал'}.",
        focus_line,
        body,
        progression,
        "Перед тренировкой: 5–10 минут лёгкой разминки и 1–2 разминочных подхода первого упражнения."
        + health_note,
    ])


def _full_body(library: dict[str, str], days: int, goal: str, focus: str | None) -> str:
    sets = "2" if goal == "weight_loss" else "3"
    base = [library["squat"], library["push"], library["pull"], library["hinge"], library["shoulders"]]
    if focus == "ноги и ягодицы":
        base.insert(2, library["glutes"])
    if focus == "верх тела":
        base.extend([library["push"], library["pull"]])
    return "**Тренировка A/B:**\n" + "\n".join(
        f"{index}. {exercise} — {sets} × 8–12." for index, exercise in enumerate(base[:6], 1)
    ) + ("\nЧередуй A/B; при 3 днях: A/B/A, затем B/A/B." if days >= 3 else "\nЧередуй A и B.")


def _split(library: dict[str, str], days: int, level: str, goal: str, focus: str | None) -> str:
    sets = "3" if level == "intermediate" else "3–4"
    extra = " + дополнительный подход" if focus else ""
    sessions = [
        f"**День 1 — грудь и бицепс:** {library['push']} — {sets} × 6–10; жим под наклоном — {sets} × 8–12; сгибание рук — 2–3 × 10–15{extra}.",
        f"**День 2 — спина и трицепс:** {library['pull']} — {sets} × 8–12; тяга в наклоне — {sets} × 8–12; разгибание рук — 2–3 × 10–15.",
        f"**День 3 — плечи и ноги:** {library['squat']} — {sets} × 6–10; {library['hinge']} — {sets} × 8–12; {library['shoulders']} — 2–3 × 10–15; {library['glutes']} — 2–3 × 8–12{extra if focus == 'ноги и ягодицы' else ''}.",
    ]
    return "\n".join(sessions[:days])


def _focus(profile: dict[str, Any]) -> str | None:
    value = str(profile.get("muscle_focus") or "").casefold()
    if any(word in value for word in ("ягод", "ног")):
        return "ноги и ягодицы"
    if any(word in value for word in ("верх", "груд", "спин", "плеч")):
        return "верх тела"
    return None


def _progression(level: str, goal: str) -> str:
    reserve = "3–4" if goal == "weight_loss" else "1–3"
    if level == "advanced":
        return f"Прогрессия: держи {reserve} повтора в запасе. Когда верхняя граница повторений достигнута во всех подходах — прибавь 2–5% веса. Каждая 4-я неделя: разгрузка, минус примерно треть подходов."
    return f"Прогрессия: держи {reserve} повтора в запасе. Сначала доведи все подходы до верхней границы повторений, затем добавь минимальный вес."


def _health_note(profile: dict[str, Any]) -> str:
    if profile.get("medical_notes") or profile.get("injuries") or profile.get("is_pregnant"):
        return "\n\nПри травмах, заболеваниях, беременности или боли согласуй нагрузку с профильным специалистом. Не выполняй движение, которое вызывает или усиливает боль."
    return ""
