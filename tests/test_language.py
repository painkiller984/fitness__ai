from app.agent.language import response_language


def test_english_input_selects_english() -> None:
    assert response_language("Can you calculate my calories?") == "en"


def test_russian_and_mixed_input_default_to_russian() -> None:
    assert response_language("Рассчитай калории") == "ru"
    assert response_language("Рассчитай calories") == "ru"
