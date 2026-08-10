from __future__ import annotations

from typing import Any


LEVELS = {
    "beginner": {"sets": "2–3", "reps": "8–12", "rir": "3–4", "max_days": 3},
    "intermediate": {"sets": "3", "reps": "6–12", "rir": "2–3", "max_days": 4},
    "advanced": {"sets": "3–4", "reps": "5–15", "rir": "1–3", "max_days": 5},
}


EXERCISES = {
    "gym": {
        "squat": "присед со штангой или жим ногами",
        "hinge": "румынская тяга",
        "push": "жим лёжа или в тренажёре",
        "pull": "тяга горизонтального блока",
        "vertical": "тяга верхнего блока",
        "core": "планка или Pallof press",
    },
    "home": {
        "squat": "приседания или сплит-приседания",
        "hinge": "ягодичный мост или румынская тяга с доступным весом",
        "push": "отжимания",
        "pull": "тяга гантели, резинки или наполненного рюкзака",
        "vertical": "жим гантелей/резинки вверх или pike-отжимания",
        "core": "планка или dead bug",
    },
    "outdoors": {
        "squat": "приседания или выпады",
        "hinge": "одноногая румынская тяга",
        "push": "отжимания от подходящей опоры",
        "pull": "подтягивания или горизонтальная тяга на низкой перекладине",
        "vertical": "pike-отжимания",
        "core": "планка или подъёмы коленей",
    },
}


def build_workout_program(profile: dict[str, Any], language: str = "ru") -> str:
    """Return a conservative, evidence-informed resistance plan from declared workout data."""
    level = str(profile["training_experience"])
    settings = LEVELS[level]
    available_days = int(profile["training_days_per_week"])
    planned_days = min(available_days, int(settings["max_days"]))
    place = str(profile["training_place"])
    exercises = EXERCISES["gym" if place == "both" else place]
    sessions = _sessions(planned_days, exercises, settings)
    if language == "en":
        return _build_english_workout(profile, settings, planned_days, available_days, sessions)

    goal_text = {
        "weight_loss": "сохранение мышц во время снижения веса",
        "muscle_gain": "рост мышечной массы",
        "maintenance": "поддержание силы и формы",
        "wellbeing": "самочувствие, силу и повседневную активность",
    }[str(profile["goal"])]
    header = (
        f"План для уровня «{_level_label(level)}»: цель — {goal_text}. "
        f"{planned_days} силовых тренировки в неделю"
        + (f" из доступных {available_days}." if planned_days < available_days else ".")
    )
    lines = [header, "", "Разминка: 5–10 минут лёгкой активности и 1–3 разминочных подхода первого упражнения."]
    for index, exercises_for_day in enumerate(sessions, start=1):
        lines.append(f"День {index}: " + "; ".join(exercises_for_day) + ".")
    lines.extend(
        [
            "",
            f"Работайте с запасом {settings['rir']} повторения до отказа; отдыхайте 2–3 минуты после базовых упражнений и 1–2 минуты после остальных.",
            "Прогрессия: когда верхняя граница повторений получается во всех подходах с чистой техникой, добавьте 1 повторение или 2–5% веса.",
        ]
    )
    if profile.get("medical_notes") or profile.get("injuries") or profile.get("is_pregnant"):
        lines.extend(
            [
                "",
                "Перед началом согласуйте нагрузку с врачом или профильным специалистом. Не выполняйте движения, вызывающие боль или ухудшение симптомов.",
            ]
        )
    return "\n".join(lines)


def _sessions(days: int, exercises: dict[str, str], settings: dict[str, Any]) -> list[list[str]]:
    item = lambda key: f"{exercises[key]} — {settings['sets']} × {settings['reps']}"
    full_a = [item("squat"), item("push"), item("pull"), item("hinge"), item("core")]
    full_b = [item("hinge"), item("vertical"), item("pull"), item("squat"), item("core")]
    if days <= 3:
        return [full_a if day % 2 else full_b for day in range(1, days + 1)]
    upper = [item("push"), item("pull"), item("vertical"), item("core")]
    lower = [item("squat"), item("hinge"), item("core")]
    return [upper if day % 2 else lower for day in range(1, days + 1)]


def _level_label(level: str) -> str:
    return {"beginner": "новичок", "intermediate": "средний", "advanced": "продвинутый"}[level]


def _build_english_workout(
    profile: dict[str, Any],
    settings: dict[str, Any],
    planned_days: int,
    available_days: int,
    sessions: list[list[str]],
) -> str:
    goal = {
        "weight_loss": "preserve muscle while losing weight",
        "muscle_gain": "build muscle",
        "maintenance": "maintain strength and fitness",
        "wellbeing": "improve wellbeing, strength, and daily activity",
    }[str(profile["goal"])]
    level = {"beginner": "beginner", "intermediate": "intermediate", "advanced": "advanced"}[
        str(profile["training_experience"])
    ]
    lines = [
        f"{level.title()} plan — goal: {goal}. {planned_days} strength sessions per week"
        + (f" (out of {available_days} available days)." if planned_days < available_days else "."),
        "",
        "Warm up for 5–10 minutes and do 1–3 lighter sets before the first exercise.",
    ]
    for index, exercises_for_day in enumerate(sessions, start=1):
        lines.append(f"Day {index}: " + "; ".join(exercises_for_day) + ".")
    lines.extend(
        [
            "",
            f"Keep {settings['rir']} reps in reserve; rest 2–3 minutes after compound exercises and 1–2 minutes after the others.",
            "Progression: when you reach the top of the rep range in every set with good technique, add one repetition or 2–5% load.",
        ]
    )
    if profile.get("medical_notes") or profile.get("injuries") or profile.get("is_pregnant"):
        lines.extend(
            [
                "",
                "Discuss exercise with an appropriate clinician before starting. Stop movements that cause pain or worsen symptoms.",
            ]
        )
    return "\n".join(lines)
