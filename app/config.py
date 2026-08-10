from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Forma")
    app_env: str = os.getenv("APP_ENV", "development")
    storage_secret: str = os.getenv("APP_STORAGE_SECRET", "local-dev-only")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))
    supabase_url: str = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_publishable_key: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    ai_provider: str = os.getenv("AI_PROVIDER", "gemini").strip().casefold()
    ai_model: str = os.getenv(
        "AI_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    )
    ai_judge_model: str = os.getenv(
        "AI_JUDGE_MODEL", os.getenv("GEMINI_JUDGE_MODEL", "gemini-3.5-flash-lite")
    )
    ai_api_key: str = os.getenv("AI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    ai_base_url: str = os.getenv("AI_BASE_URL", "").rstrip("/")

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_publishable_key)

    @property
    def ai_enabled(self) -> bool:
        return self.ai_provider != "deterministic" and (
            bool(self.ai_api_key) or self.ai_provider == "ollama"
        )

    def validate_production(self) -> None:
        if self.app_env != "production":
            return
        missing: list[str] = []
        if not self.supabase_enabled:
            missing.extend(["SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY"])
        if not self.ai_enabled:
            missing.append("AI_API_KEY")
        if self.storage_secret in {"", "local-dev-only", "change-me-before-deploy"}:
            missing.append("APP_STORAGE_SECRET")
        if missing:
            raise RuntimeError(
                "Production configuration is incomplete: " + ", ".join(dict.fromkeys(missing))
            )


settings = Settings()
