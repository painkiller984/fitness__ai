from app.agent.state import ActivityLevel, Goal, Sex, UserProfile
from app.tools.calorie_macros import calculate_nutrition_targets, validate_targets


def profile(**overrides):
    values = {
        "name": "Тест", "age": 30, "sex": Sex.MALE, "height_cm": 180,
        "weight_kg": 80, "goal": Goal.WEIGHT_LOSS,
        "activity_level": ActivityLevel.MODERATE,
    }
    values.update(overrides)
    return UserProfile(**values)


def test_calculation_is_internally_consistent():
    targets = calculate_nutrition_targets(profile())
    assert targets.target_kcal < targets.maintenance_kcal
    assert targets.protein_g == 144
    assert validate_targets(targets) == []


def test_muscle_gain_has_surplus():
    targets = calculate_nutrition_targets(profile(goal=Goal.MUSCLE_GAIN))
    assert targets.target_kcal > targets.maintenance_kcal
