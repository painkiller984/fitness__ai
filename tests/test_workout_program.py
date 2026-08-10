from app.tools.workout_program import build_workout_program


def profile(**overrides):
    data = {
        "training_place": "gym",
        "training_experience": "beginner",
        "injuries": [],
        "medical_notes": "",
        "is_pregnant": False,
    }
    data.update(overrides)
    return data


def test_beginner_template_is_fixed_full_body_for_first_month() -> None:
    program = build_workout_program(profile())

    assert "первые 4 недели" in program
    assert "full body" in program
    assert "3 раза в неделю" in program


def test_intermediate_template_is_the_requested_three_day_split() -> None:
    program = build_workout_program(profile(training_experience="intermediate"))

    assert "грудь и бицепс" in program
    assert "спина и трицепс" in program
    assert "плечи и ноги" in program


def test_advanced_template_adds_progression() -> None:
    program = build_workout_program(profile(training_experience="advanced"))

    assert "Прогрессия" in program
    assert "разгрузку" in program


def test_health_note_keeps_template_and_adds_referral() -> None:
    program = build_workout_program(profile(medical_notes="Болит колено"))

    assert "первые 4 недели" in program
    assert "врачом" in program


def test_non_gym_user_does_not_receive_gym_template() -> None:
    program = build_workout_program(profile(training_place="home"))

    assert "для зала" in program
