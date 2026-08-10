import pytest

from app.config import Settings


def test_production_rejects_missing_persistent_storage() -> None:
    settings = Settings(
        app_env="production",
        storage_secret="secure-value",
        ai_provider="gemini",
        ai_api_key="test-key",
        supabase_url="",
        supabase_publishable_key="",
    )
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        settings.validate_production()


def test_production_accepts_complete_configuration() -> None:
    Settings(
        app_env="production",
        storage_secret="secure-value",
        ai_provider="gemini",
        ai_api_key="test-key",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="publishable-key",
    ).validate_production()
