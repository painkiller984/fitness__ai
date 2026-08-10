from app.config import Settings
from app.providers.factory import create_provider_bundle


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "ai_provider": "deterministic",
        "ai_model": "test-model",
        "ai_judge_model": "test-judge",
        "ai_api_key": "",
        "ai_base_url": "",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_deterministic_provider_is_explicit() -> None:
    bundle = create_provider_bundle(make_settings())

    assert bundle.label == "deterministic"


def test_gemini_uses_configured_model_without_network_call() -> None:
    bundle = create_provider_bundle(
        make_settings(ai_provider="gemini", ai_api_key="test-key", ai_model="gemini-test")
    )

    assert bundle.label == "gemini:gemini-test"


def test_ollama_does_not_require_an_api_key() -> None:
    bundle = create_provider_bundle(make_settings(ai_provider="ollama", ai_model="qwen2.5:7b"))

    assert bundle.label == "ollama:qwen2.5:7b"
    assert bundle.generator.client.endpoint == "http://localhost:11434/v1/chat/completions"


def test_keyed_provider_without_key_falls_back_to_deterministic() -> None:
    bundle = create_provider_bundle(make_settings(ai_provider="openai"))

    assert bundle.label == "deterministic"
