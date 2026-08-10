from app.agent.conversation_intake import ConversationIntake
from app.agent.state import Goal, TrainingPlace


def test_conversation_intake_builds_profile_from_chat_answers() -> None:
    intake = ConversationIntake()
    answers = (
        "хочу снизить вес",
        "Антон",
        "30",
        "мужской",
        "178",
        "78",
        "умеренный",
        "дома и в зале",
        "нет",
        "нет",
        "старую травму колена",
    )

    for answer in answers:
        intake.accept(answer)

    profile = intake.build_profile()
    assert intake.is_complete
    assert profile.goal is Goal.WEIGHT_LOSS
    assert profile.training_place is TrainingPlace.BOTH
    assert profile.injuries == ["старую травму колена"]


def test_conversation_intake_repeats_question_after_invalid_value() -> None:
    intake = ConversationIntake()

    response = intake.accept("хочу просто быть лучше")

    assert "Выберите одну цель" in response
    assert intake.step == 0
