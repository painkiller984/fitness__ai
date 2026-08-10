from app.agent.chat_policy import (
    build_complete_profile,
    format_profile_data,
    should_use_bounded_agent,
    target_facts,
)
from app.agent.state import NutritionTargets


COMPLETE = {
    "name": "Антон",
    "age": 30,
    "sex": "male",
    "height_cm": 178,
    "weight_kg": 93,
    "goal": "weight_loss",
    "activity_level": "moderate",
}


def test_complete_profile_enables_bounded_calculation() -> None:
    profile = build_complete_profile(COMPLETE)
    assert profile is not None
    assert should_use_bounded_agent("nutrition_targets", profile)
    assert should_use_bounded_agent("meal_plan", profile)
    assert not should_use_bounded_agent("general_coaching", profile)


def test_incomplete_profile_never_enters_bounded_agent() -> None:
    assert build_complete_profile({"name": "Антон"}) is None
    assert not should_use_bounded_agent("nutrition_targets", None)


def test_targets_are_persistable_and_visible() -> None:
    targets = NutritionTargets(
        bmr_kcal=1800,
        maintenance_kcal=2500,
        target_kcal=2125,
        protein_g=167,
        fat_g=74,
        carbs_g=198,
    )
    stored = {**COMPLETE, **target_facts(targets)}
    text = format_profile_data(stored)
    assert "2125 ккал" in text
    assert "167 г" in text


def test_internal_identifiers_are_not_displayed() -> None:
    text = format_profile_data({**COMPLETE, "user_id": "secret-id"})
    assert "secret-id" not in text
