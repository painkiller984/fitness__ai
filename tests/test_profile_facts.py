from app.agent.profile_facts import extract_profile_facts


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
    }


def test_extractor_accepts_short_name_with_other_profile_facts() -> None:
    facts = extract_profile_facts("Я Антон, мне 30 лет, я мужчина, рост 178 см, вес 93 кг")
    assert facts["name"] == "Антон"
    assert facts["age"] == 30


def test_extractor_does_not_store_arbitrary_i_am_phrase_as_name() -> None:
    assert "name" not in extract_profile_facts("я новичок")


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
    }
