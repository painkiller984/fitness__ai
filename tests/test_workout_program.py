from app.tools.workout_program import build_workout_program


def profile(**overrides):
    data = {
        "training_place": "gym", "training_experience": "beginner", "training_days_per_week": 3,
        "sex": "male", "injuries": [], "medical_notes": "", "is_pregnant": False,
    }
    data.update(overrides)
    return data


def test_beginner_uses_full_body_for_first_month() -> None:
    program = build_workout_program(profile())
    assert "первые 4 недели" in program
    assert "full-body" in program
    assert "3 тренировки" in program


def test_intermediate_keeps_three_day_split() -> None:
    program = build_workout_program(profile(training_experience="intermediate"))
    assert "грудь и бицепс" in program
    assert "спина и трицепс" in program
    assert "плечи и ноги" in program


def test_advanced_template_adds_planned_deload() -> None:
    program = build_workout_program(profile(training_experience="advanced"))
    assert "Прогрессия" in program
    assert "Каждая 4-я неделя" in program


def test_health_note_keeps_program_and_adds_referral() -> None:
    program = build_workout_program(profile(medical_notes="Болит колено"))
    assert "первые 4 недели" in program
    assert "профильным специалистом" in program


def test_home_user_receives_home_exercise_variants() -> None:
    program = build_workout_program(
        profile(training_place="home", available_equipment=["dumbbells"])
    )
    assert "место: дом" in program
    assert "гоблет-присед" in program


def test_home_user_without_equipment_receives_bodyweight_variants() -> None:
    program = build_workout_program(profile(training_place="home", available_equipment=[]))

    assert "присед с собственным весом" in program
    assert "тяга резины; если её нет" in program


def test_female_default_and_explicit_focus_change_the_accent() -> None:
    female = build_workout_program(profile(sex="female"))
    upper = build_workout_program(profile(sex="female", muscle_focus="верх тела"))
    assert "Акцент: ноги и ягодицы" in female
    assert "Акцент: верх тела" in upper


def test_beginner_order_uses_sex_specific_default_focus() -> None:
    male = build_workout_program(profile(sex="male"))
    female = build_workout_program(profile(sex="female"))

    assert male.index("жим лёжа") < male.index("присед")
    assert female.index("ягодичный мост") < female.index("присед")
