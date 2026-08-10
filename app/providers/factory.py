from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.judges.plan_judge import (
    DeterministicPlanJudge,
    GeminiPlanJudge,
    OpenAICompatiblePlanJudge,
    PlanJudge,
)
from app.providers.deterministic import DeterministicGenerator
from app.providers.conversation import (
    ConversationResponder,
    DeterministicConversationResponder,
    GeminiConversationResponder,
    OpenAICompatibleConversationResponder,
)
from app.providers.gemini import GeminiGenerator
from app.providers.food_search import GeminiFoodSearch
from app.providers.openai_compatible import OpenAICompatibleGenerator


@dataclass(frozen=True, slots=True)
class ProviderBundle:
    generator: object
    judge: PlanJudge
    conversation: ConversationResponder
    food_search: GeminiFoodSearch | None
    label: str


def create_provider_bundle(settings: Settings) -> ProviderBundle:
    provider = settings.ai_provider
    if provider == "deterministic":
        return ProviderBundle(DeterministicGenerator(), DeterministicPlanJudge(), DeterministicConversationResponder(), None, "deterministic")
    if provider == "gemini":
        if not settings.ai_api_key:
            return ProviderBundle(DeterministicGenerator(), DeterministicPlanJudge(), DeterministicConversationResponder(), None, "deterministic")
        return ProviderBundle(
            GeminiGenerator(settings.ai_api_key, settings.ai_model),
            GeminiPlanJudge(settings.ai_api_key, settings.ai_judge_model),
            GeminiConversationResponder(settings.ai_api_key, settings.ai_model),
            GeminiFoodSearch(settings.ai_api_key, settings.ai_model),
            f"gemini:{settings.ai_model}",
        )

    base_url = _resolve_base_url(provider, settings.ai_base_url)
    if not base_url:
        raise ValueError(f"AI_BASE_URL is required for provider '{provider}'.")
    if provider != "ollama" and not settings.ai_api_key:
        return ProviderBundle(DeterministicGenerator(), DeterministicPlanJudge(), DeterministicConversationResponder(), None, "deterministic")
    return ProviderBundle(
        OpenAICompatibleGenerator(base_url, settings.ai_api_key, settings.ai_model),
        OpenAICompatiblePlanJudge(base_url, settings.ai_api_key, settings.ai_judge_model),
        OpenAICompatibleConversationResponder(base_url, settings.ai_api_key, settings.ai_model),
        None,
        f"{provider}:{settings.ai_model}",
    )


def _resolve_base_url(provider: str, configured_url: str) -> str:
    if configured_url:
        return configured_url
    defaults = {
        "openai": "https://api.openai.com/v1",
        "ollama": "http://localhost:11434/v1",
    }
    if provider in {"openai", "openai_compatible", "openrouter", "groq", "together", "deepseek", "ollama"}:
        return defaults.get(provider, "")
    raise ValueError(
        "Unsupported AI_PROVIDER. Use gemini, openai, openai_compatible, openrouter, groq, together, deepseek, ollama, or deterministic."
    )
