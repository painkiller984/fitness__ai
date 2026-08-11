from app.agent.profile_facts import extract_durable_dietary_preferences, extract_profile_facts


def test_extracts_only_explicit_profile_facts() -> None:
    facts = extract_profile_facts("Меня зовут Антон, мне 30 лет, рост 178 см, вес 93 кг, хочу похудеть")

    assert facts == {
        "name": "Антон",
        "age": 30,
        "height_cm": 178,
        "weight_kg": 93.0,
        "goal": "weight_loss",
    }


def test_ordinary_message_does_not_create_profile_facts() -> None:
    assert extract_profile_facts("Я голодный и хочу поужинать") == {}


def test_extracts_natural_activity_description() -> None:
    assert extract_profile_facts("Я мужчина и тренируюсь 3 раза в неделю") == {
        "sex": "male",
        "activity_level": "moderate",
        "training_days_per_week": 3,
    }


def test_extractor_accepts_short_name_with_other_profile_facts() -> None:
    facts = extract_profile_facts("Я Антон, мне 30 лет, я мужчина, рост 178 см, вес 93 кг")
    assert facts["name"] == "Антон"
    assert facts["age"] == 30


def test_extractor_does_not_store_arbitrary_i_am_phrase_as_name() -> None:
    assert "name" not in extract_profile_facts("я новичок")


def test_expected_name_accepts_a_bare_name_but_not_a_greeting() -> None:
    assert extract_profile_facts("Антон", {"name"}) == {"name": "Антон"}
    assert extract_profile_facts("Привет", {"name"}) == {}


def test_expected_body_fields_accept_a_free_form_summary() -> None:
    facts = extract_profile_facts("27, мужчина, 172, 94", {"age", "sex", "height_cm", "weight_kg"})
    assert facts == {"age": 27, "sex": "male", "height_cm": 172, "weight_kg": 94.0}


def test_extracts_english_profile_facts() -> None:
    facts = extract_profile_facts(
        "My name is Alex, I am a 30 years old man, height 178 cm, I weigh 93 kg, "
        "I want to lose weight and train 3 times a week."
    )
    assert facts == {
        "name": "Alex",
        "age": 30,
        "height_cm": 178,
        "weight_kg": 93.0,
        "sex": "male",
        "goal": "weight_loss",
        "activity_level": "moderate",
        "training_days_per_week": 3,
    }


def test_extracts_compact_unlabelled_profile_summary() -> None:
    facts = extract_profile_facts(
        "Антон, 27, мужской, 172, 93, похудение, тренируюсь 3 раза в неделю"
    )
    assert facts == {
        "name": "Антон",
        "age": 27,
        "sex": "male",
        "height_cm": 172,
        "weight_kg": 93.0,
        "goal": "weight_loss",
        "activity_level": "moderate",
        "training_days_per_week": 3,
    }


def test_compact_parser_does_not_guess_without_profile_context() -> None:
    assert extract_profile_facts("Антон, 27, привет, 172, 93") == {}


def test_compact_parser_does_not_store_goal_as_name() -> None:
    facts = extract_profile_facts(
        "похудение, 27, мужской, 172, 94, в основном сижу и тренируюсь 3 раза в неделю"
    )

    assert "name" not in facts
    assert facts == {
        "age": 27,
        "sex": "male",
        "height_cm": 172,
        "weight_kg": 94.0,
        "goal": "weight_loss",
        "activity_level": "moderate",
        "training_days_per_week": 3,
    }


def test_extracts_optional_surname_only_when_explicitly_given() -> None:
    facts = extract_profile_facts("Меня зовут Антон Иванов, мне 30 лет")

    assert facts["name"] == "Антон"
    assert facts["surname"] == "Иванов"


def test_extracts_workout_setup_and_health_screening() -> None:
    facts = extract_profile_facts(
        "Я новичок, тренируюсь дома 3 раза в неделю, есть гантели и резинки. Травм нет"
    )
    assert facts["training_experience"] == "beginner"
    assert facts["training_place"] == "home"
    assert facts["training_days_per_week"] == 3
    assert facts["available_equipment"] == ["dumbbells", "resistance_bands"]
    assert facts["equipment_screened"] is True
    assert facts["health_screened"] is True


def test_unknown_or_full_gym_equipment_counts_as_answer() -> None:
    unknown = extract_profile_facts("Нет травм, не знаю какое оборудование")
    full_access = extract_profile_facts("Наверное всё доступно")

    assert unknown["available_equipment"]
    assert unknown["equipment_screened"] is True
    assert unknown["health_screened"] is True
    assert full_access["available_equipment"]
    assert full_access["equipment_screened"] is True


def test_extracts_experience_duration_without_confusing_age() -> None:
    assert extract_profile_facts("Мне 30 лет, тренируюсь 2 года")["training_experience"] == "advanced"
    assert extract_profile_facts("Тренируюсь 6 месяцев")["training_experience"] == "intermediate"


def test_extracts_only_explicit_durable_food_preferences() -> None:
    assert extract_durable_dietary_preferences("Не люблю гречку, но сегодня хочу шоколад") == ["dislike:гречку"]
    assert extract_durable_dietary_preferences("Ненавижу рис") == ["dislike:рис"]
    assert extract_durable_dietary_preferences("Люблю шоколад") == ["like:шоколад"]
