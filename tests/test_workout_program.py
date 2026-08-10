from app.tools.workout_program import build_workout_program


def profile(**overrides):
    data = {
        "goal": "muscle_gain",
        "training_place": "gym",
        "training_experience": "beginner",
        "training_days_per_week": 3,
        "available_equipment": ["machines"],
        "injuries": [],
        "medical_notes": "",
        "is_pregnant": False,
    }
    data.update(overrides)
    return data


def test_beginner_program_uses_conservative_volume() -> None:
    program = build_workout_program(profile())
    assert "уровня «новичок»" in program
    assert "2–3 × 8–12" in program
    assert "3–4 повторения" in program


def test_intermediate_and_advanced_plans_are_different() -> None:
    intermediate = build_workout_program(profile(training_experience="intermediate", training_days_per_week=4))
    advanced = build_workout_program(profile(training_experience="advanced", training_days_per_week=5))
    assert "уровня «средний»" in intermediate
    assert "3 × 6–12" in intermediate
    assert "уровня «продвинутый»" in advanced
    assert "3–4 × 5–15" in advanced


def test_beginner_training_days_are_capped_for_recovery() -> None:
    program = build_workout_program(profile(training_days_per_week=7))
    assert "3 силовых тренировки в неделю из доступных 7" in program


def test_health_note_keeps_conservative_plan_and_referral() -> None:
    program = build_workout_program(profile(medical_notes="Болит колено"))
    assert "врачом" in program


def test_program_uses_english_when_requested() -> None:
    program = build_workout_program(profile(), language="en")
    assert "Beginner plan" in program
    assert "Day 1" in program
