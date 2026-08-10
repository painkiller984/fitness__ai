from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class OnboardingStage:
    key: str
    missing_fields: tuple[str, ...]
    instruction_ru: str
    instruction_en: str


STAGES = (
    OnboardingStage(
        key="name",
        missing_fields=("name",),
        instruction_ru=(
            "Коротко и естественно отреагируй на сообщение, но не переходи к рекомендациям или следующим "
            "вопросам. В конце обязательно попроси пользователя представиться."
        ),
        instruction_en=(
            "React briefly and naturally to the message, but do not proceed to recommendations or later "
            "questions. End by asking the user to introduce themselves."
        ),
    ),
    OnboardingStage(
        key="body",
        missing_fields=("age", "sex", "height_cm", "weight_kg"),
        instruction_ru=(
            "Коротко и естественно отреагируй, затем попроси сообщить только недостающие данные из списка: "
            "возраст, пол, рост и текущий вес. Их можно написать одной свободной фразой. Не спрашивай повторно "
            "уже известные значения и пока не переходи к рекомендациям."
        ),
        instruction_en=(
            "React briefly and naturally, then ask only for the missing items from: age, sex, height, and "
            "current weight. They may be given in one free-form sentence. Do not repeat known questions or "
            "proceed to recommendations yet."
        ),
    ),
    OnboardingStage(
        key="goal_activity",
        missing_fields=("goal", "activity_level"),
        instruction_ru=(
            "Коротко и естественно отреагируй, затем попроси сообщить только недостающие данные: цель и обычный "
            "уровень активности. Не спрашивай повторно уже известное и пока не составляй план."
        ),
        instruction_en=(
            "React briefly and naturally, then ask only for the missing items: goal and usual activity level. "
            "Do not repeat known questions or create a plan yet."
        ),
    ),
)


def current_onboarding_stage(
    profile: dict[str, Any] | None, workflow: str | None = None
) -> OnboardingStage | None:
    data = profile or {}
    stages = list(STAGES)
    if workflow == "workout":
        stages.append(
            OnboardingStage(
                key="workout_setup",
                missing_fields=(
                    "training_place",
                    "training_experience",
                    "training_days_per_week",
                    "equipment_screened",
                    "health_screened",
                ),
                instruction_ru=(
                    "Коротко отреагируй, но не составляй программу. Спроси только недостающие данные для "
                    "безопасной тренировки: где заниматься (дом, зал, улица), уровень (новичок, средний, "
                    "продвинутый), сколько дней в неделю, доступное оборудование и есть ли травмы, "
                    "заболевания или другие ограничения. Не выдумывай эти данные."
                ),
                instruction_en=(
                    "Respond briefly but do not create a program yet. Ask only for the missing workout details: "
                    "place, experience level (beginner, intermediate, advanced), days per week, available "
                    "equipment, and injuries, health conditions, or other limitations. Do not invent them."
                ),
            )
        )
    for stage in stages:
        missing = tuple(field for field in stage.missing_fields if data.get(field) in (None, "", False))
        if missing:
            return OnboardingStage(
                key=stage.key,
                missing_fields=missing,
                instruction_ru=stage.instruction_ru,
                instruction_en=stage.instruction_en,
            )
    return None


def onboarding_context(stage: OnboardingStage, language: str) -> dict[str, Any]:
    return {
        "stage": stage.key,
        "missing_fields": list(stage.missing_fields),
        "mandatory_instruction": stage.instruction_en if language == "en" else stage.instruction_ru,
    }
