from app.agent.state import ActivityLevel, Goal, Sex, UserProfile
from app.guards.safety import assess_safety, urgent_message_if_needed


def profile(**overrides):
    values = {
        "name": "Тест", "age": 30, "sex": Sex.FEMALE, "height_cm": 165,
        "weight_kg": 60, "goal": Goal.WELLBEING,
        "activity_level": ActivityLevel.LIGHT,
    }
    values.update(overrides)
    return UserProfile(**values)


def test_red_flag_blocks_plan():
    result = assess_safety(profile(), "После тренировки появилась боль в груди")
    assert result.level == "high"
    assert result.can_generate_plan is False


def test_regular_request_is_allowed():
    result = assess_safety(profile(), "Как распределить белок на день?")
    assert result.level == "low"
    assert result.can_generate_plan is True


def test_pregnancy_routes_to_specialist():
    result = assess_safety(profile(is_pregnant=True), "Составь план")
    assert result.level == "medium"
    assert result.can_generate_plan is False


def test_red_flag_is_blocked_before_profile_is_complete():
    assert urgent_message_if_needed("У меня сильная одышка") is not None
    assert urgent_message_if_needed("Хочу составить меню") is None
