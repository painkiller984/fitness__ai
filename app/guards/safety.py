from __future__ import annotations

from app.agent.state import SafetyDecision, UserProfile
from app.agent.language import response_language


RED_FLAG_PHRASES = {
    "боль в груди",
    "потеря сознания",
    "обморок",
    "кровотечение",
    "не могу дышать",
    "сильная одышка",
    "острая боль",
    "расстройство пищевого поведения",
    "анорексия",
    "булимия",
    "chest pain",
    "loss of consciousness",
    "fainting",
    "bleeding",
    "can't breathe",
    "cannot breathe",
    "severe shortness of breath",
    "acute pain",
    "eating disorder",
    "anorexia",
    "bulimia",
}


def urgent_message_if_needed(message: str) -> str | None:
    """Block medical red flags even before a complete fitness profile exists."""
    normalized = message.casefold()
    if any(phrase in normalized for phrase in RED_FLAG_PHRASES):
        if response_language(message) == "en":
            return (
                "I can’t safely create a plan from this message. If your symptoms are acute "
                "or getting worse, seek urgent medical care."
            )
        return (
            "Я не могу безопасно составить план по этому сообщению. При острых или "
            "ухудшающихся симптомах обратитесь за неотложной медицинской помощью."
        )
    return None


def assess_safety(profile: UserProfile, message: str = "") -> SafetyDecision:
    normalized = message.casefold()
    hits = sorted(phrase for phrase in RED_FLAG_PHRASES if phrase in normalized)
    reasons: list[str] = []

    if hits:
        reasons.append(f"Обнаружены тревожные признаки: {', '.join(hits)}")
    if profile.age < 18:
        reasons.append("Пользователь несовершеннолетний.")
    if profile.is_pregnant:
        reasons.append("Указана беременность.")
    if profile.medical_notes.strip():
        reasons.append("Указано состояние здоровья, требующее индивидуальной оценки.")

    if hits:
        return SafetyDecision(
            level="high",
            can_generate_plan=False,
            reasons=reasons,
            user_message=(
                "Я не могу безопасно составить план по этому сообщению. При острых или "
                "ухудшающихся симптомах обратитесь за неотложной медицинской помощью."
            ),
        )
    if reasons:
        return SafetyDecision(
            level="medium",
            can_generate_plan=False,
            reasons=reasons,
            user_message=(
                "Перед персональным планом обсудите нагрузку и питание с профильным специалистом. "
                "Я могу дать только общую образовательную информацию."
            ),
        )
    return SafetyDecision(level="low", can_generate_plan=True)
