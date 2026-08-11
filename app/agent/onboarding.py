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
            "вопросам. В конце обязательно попроси пользователя назвать имя; фамилию можно указать по желанию."
        ),
        instruction_en=(
            "React briefly and naturally to the message, but do not proceed to recommendations or later "
            "questions. End by asking for the user's first name; their surname is optional."
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
    if workflow == "workout_plan":
        stages = [
            STAGES[0],
            STAGES[1],
            OnboardingStage(
                key="goal",
                missing_fields=("goal",),
                instruction_ru=(
                    "Коротко отреагируй и спроси только цель: похудение, набор мышечной массы, "
                    "поддержание формы или самочувствие. Не спрашивай общий уровень активности: "
                    "он не нужен для выбора готового шаблона тренировки."
                ),
                instruction_en=(
                    "Respond briefly and ask only for the goal: weight loss, muscle gain, maintenance, "
                    "or wellbeing. Do not ask for usual activity level; it is not needed to choose a "
                    "ready-made workout template."
                ),
            ),
        ]
        stages.append(
            OnboardingStage(
                key="workout_setup",
                missing_fields=(
                    "training_place",
                    "training_experience",
                    "health_screened",
                ),
                instruction_ru=(
                    "Коротко отреагируй, но не составляй программу. Спроси только недостающие данные: "
                    "где заниматься (дом, зал, улица), тренировочный стаж (до месяца, от месяца до года "
                    "или больше года) и есть ли травмы, заболевания или другие ограничения. Не спрашивай "
                    "про общий уровень активности, число тренировок в неделю или оборудование. Если эти "
                    "данные не названы пользователем, предложи безопасный стартовый вариант: 3 тренировки "
                    "в неделю и базовые упражнения для указанного места. Не выдумывай данные."
                ),
                instruction_en=(
                    "Respond briefly but do not create a program yet. Ask only for the missing workout details: "
                    "place, training experience (under one month, one month to one year, or over one year), "
                    "and injuries, health conditions, or other limitations. Do not ask about activity level, "
                    "training days, or equipment. If they were not provided, recommend a safe three-day "
                    "starting plan with basic exercises for the stated location."
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


def onboarding_reply(stage: OnboardingStage, language: str) -> str:
    """Return a deterministic next question so an LLM cannot skip required facts."""
    if language == "en":
        return _onboarding_reply_en(stage)
    return _onboarding_reply_ru(stage)


def _onboarding_reply_ru(stage: OnboardingStage) -> str:
    questions = {
        "name": (
            "Привет! Я Forma — твой фитнес-тренер и консультант по питанию. "
            "Помогу с тренировками, рационом и расчётом калорий. Как тебя зовут?"
        ),
        "body": "Чтобы продолжить, напиши недостающие данные одной фразой: возраст, пол, рост и текущий вес.",
        "goal_activity": "Уточни, пожалуйста, цель и обычный уровень активности.",
        "goal": "Уточни цель: похудение, набор мышечной массы, поддержание формы или улучшение самочувствия.",
        "workout_setup": (
            "Чтобы составить безопасную индивидуальную программу, уточни только недостающие пункты: "
            "где будешь заниматься (дом или зал), какой у тебя опыт (до месяца, от месяца до года "
            "или больше года) и есть ли травмы, заболевания либо ограничения. "
            "Если ограничений нет — так и напиши."
        ),
    }
    return questions.get(stage.key, "Уточни, пожалуйста, недостающие данные.")


def _onboarding_reply_en(stage: OnboardingStage) -> str:
    questions = {
        "name": (
            "Hi! I’m Forma, your fitness coach and nutrition assistant. "
            "I can help with training, nutrition, and calorie targets. What’s your name?"
        ),
        "body": "To continue, send the missing details in one sentence: age, sex, height, and current weight.",
        "goal_activity": "Please clarify your goal and usual activity level.",
        "goal": "Please clarify your goal: weight loss, muscle gain, maintenance, or wellbeing.",
        "workout_setup": (
            "Before I build a safe individual program, tell me only what is still missing: "
            "where you will train (home or gym), your experience (under one month, one month to one year, "
            "or over one year), and any injuries, conditions, or limitations. Say 'none' if there are none."
        ),
    }
    return questions.get(stage.key, "Please clarify the missing details.")
