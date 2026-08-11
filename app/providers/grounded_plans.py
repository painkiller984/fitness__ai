from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

from app.agent.state import NutritionTargets


@dataclass(frozen=True, slots=True)
class GroundedPlan:
    markdown: str
    sources: tuple[str, ...]
    metadata: dict[str, Any] | None = None

    def render(self, language: str = "ru") -> str:
        return self.markdown


class GeminiGroundedPlanSearch:
    """Build plans with search grounding and a normal Gemini generation fallback."""

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def workout(
        self, profile: dict[str, Any], language: str = "ru"
    ) -> GroundedPlan | None:
        prompt = (
            "Base the recommendations on established guidance such as ACSM, WHO, government health services, "
            "and peer-reviewed sports medicine literature. Create a practical personalized workout plan. "
            "The plan must explicitly use sex, training experience, goal, training location, health limitations, "
            "and available equipment when provided. Do not use the same exercise order for every person. "
            "Use these non-negotiable frameworks while personalizing the exercise selection: a male beginner "
            "starts with full-body; an experienced male uses a three-day split of chest/biceps, back/triceps, "
            "and legs/shoulders; a female plan emphasizes legs and glutes while still training the whole body. "
            "Use search evidence to vary exercises and ordering for the actual profile rather than returning a "
            "fixed stock program. For intermediate and advanced users use suitable volume, progression, and recovery. "
            "Explain warm-up, sets, repetitions, rest, progression, and deload "
            "when appropriate. If pain, injury, pregnancy, or disease is present, advise consulting a relevant "
            "clinician and avoid presenting painful movements as mandatory. Do not diagnose. "
            f"Write the plan in {'English' if language == 'en' else 'Russian'}. "
            "Return JSON only with keys plan_markdown, framework, focus, and days. framework must be one of "
            "full_body, three_day_split, or female_lower_focus. plan_markdown contains the complete Markdown plan. "
            "Do not print citations, links, a sources section, or mention search inside plan_markdown. "
            f"User profile: {json.dumps(_safe_profile(profile), ensure_ascii=False)}"
        )
        return await self._generate(prompt, lambda plan: validate_workout_plan(plan, profile))

    async def menu(
        self,
        profile: dict[str, Any],
        targets: NutritionTargets,
        language: str = "ru",
    ) -> GroundedPlan | None:
        prompt = (
            "Base the menu on reliable nutrition knowledge such as government food databases, national health "
            "services, and reputable dietetic guidance. Create one varied personalized day menu with exact ingredient "
            "weights and 2 alternatives for each meal. Respect allergies, dietary restrictions, saved dislikes, "
            "preferences, goal, and sex. The deterministic nutrition target below is authoritative: keep total calories "
            "within 5 percent and make protein, fat, and carbohydrate totals as close as practical. Show estimated "
            "calories and P/F/C for every meal and the day total. Do not claim medical treatment. "
            f"Write the menu in {'English' if language == 'en' else 'Russian'}. "
            "After the menu, ask which foods the user likes, dislikes, or wants replaced. "
            "Return JSON only with keys plan_markdown, daily_totals, and meals. daily_totals and each item in meals "
            "must contain numeric kcal, protein_g, fat_g, and carbs_g. Each meal must also contain name and a foods "
            "array listing every offered ingredient; daily_totals must equal the sum of meals. "
            "plan_markdown contains the complete Markdown menu. Do not print citations, links, a sources section, "
            "or mention search inside plan_markdown. "
            f"User profile: {json.dumps(_safe_profile(profile), ensure_ascii=False)}. "
            f"Authoritative target: {json.dumps(targets.model_dump(), ensure_ascii=False)}"
        )
        return await self._generate(
            prompt, lambda plan: validate_menu_plan(plan, targets, profile)
        )

    async def _generate(
        self,
        prompt: str,
        validator: Callable[[GroundedPlan], bool] | None = None,
    ) -> GroundedPlan | None:
        """Try grounded search first, then generate with Gemini itself using the same framework."""
        try:
            interaction = await asyncio.to_thread(
                self.client.interactions.create,
                model=self.model,
                input=(
                    "Use Google Search to verify the factual foundation, then follow this specification. "
                    "Keep citations internal and do not include links in the answer.\n\n" + prompt
                ),
                tools=[{"type": "google_search"}],
                generation_config={"thinking_level": "low"},
                store=False,
            )
        except Exception:
            logging.warning("Gemini Google Search grounding failed; trying normal generation", exc_info=True)
        else:
            grounded = parse_grounded_plan(
                interaction.output_text or "", _extract_citations(interaction)
            )
            if grounded and (validator is None or validator(grounded)):
                return grounded

        try:
            interaction = await asyncio.to_thread(
                self.client.interactions.create,
                model=self.model,
                input=prompt,
                generation_config={"thinking_level": "low"},
                store=False,
            )
        except Exception:
            logging.exception("Gemini plan generation failed")
            return None
        generated = parse_generated_plan(interaction.output_text or "")
        if generated and (validator is None or validator(generated)):
            return generated
        return None


def parse_grounded_plan(
    raw: str, citations: tuple[str, ...] = ()
) -> GroundedPlan | None:
    try:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(raw[start : end + 1])
            markdown = str(data.get("plan_markdown") or "").strip()
            embedded_sources = tuple(
                str(url).strip()
                for url in data.get("sources", [])
                if str(url).startswith(("https://", "http://"))
            )
        else:
            markdown = raw.strip()
            embedded_sources = ()
            data = {}
        sources = tuple(dict.fromkeys((*citations, *embedded_sources)))
        if len(markdown) < 80 or not sources:
            return None
        return GroundedPlan(markdown, sources, data)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def parse_generated_plan(raw: str) -> GroundedPlan | None:
    """Accept a sufficiently detailed uncited answer produced directly by Gemini."""
    try:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(raw[start : end + 1])
            markdown = str(data.get("plan_markdown") or "").strip()
        else:
            markdown = raw.strip()
            data = {}
        if len(markdown) < 80:
            return None
        return GroundedPlan(markdown, (), data)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _extract_citations(interaction: Any) -> tuple[str, ...]:
    """Read URL citations from Interactions API model-output annotations."""
    urls: list[str] = []
    for step in getattr(interaction, "steps", ()) or ():
        content = getattr(step, "content", ()) or ()
        for block in content:
            for annotation in getattr(block, "annotations", ()) or ():
                kind = getattr(annotation, "type", None)
                url = getattr(annotation, "url", None)
                if kind == "url_citation" and isinstance(url, str) and url.startswith(("https://", "http://")):
                    urls.append(url)
    return tuple(dict.fromkeys(urls))


def _safe_profile(profile: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "name",
        "age",
        "sex",
        "height_cm",
        "weight_kg",
        "goal",
        "activity_level",
        "training_place",
        "training_experience",
        "training_days_per_week",
        "available_equipment",
        "dietary_preferences",
        "allergies",
        "injuries",
        "medical_notes",
        "is_pregnant",
    }
    return {key: value for key, value in profile.items() if key in allowed}


def validate_menu_plan(
    plan: GroundedPlan,
    targets: NutritionTargets,
    profile: dict[str, Any],
) -> bool:
    """Accept a generated menu only when its declared totals are internally consistent."""
    data = plan.metadata or {}
    totals = data.get("daily_totals")
    meals = data.get("meals")
    fields = ("kcal", "protein_g", "fat_g", "carbs_g")
    if not isinstance(totals, dict) or not isinstance(meals, list) or not meals:
        return False
    try:
        declared = {field: float(totals[field]) for field in fields}
        summed = {
            field: sum(float(meal[field]) for meal in meals if isinstance(meal, dict))
            for field in fields
        }
    except (KeyError, TypeError, ValueError):
        return False
    if len([meal for meal in meals if isinstance(meal, dict)]) != len(meals):
        return False
    if any(
        not isinstance(meal.get("foods"), list) or not meal.get("foods")
        for meal in meals
    ):
        return False
    if any(abs(declared[field] - summed[field]) > 3 for field in fields):
        return False
    target_values = {
        "kcal": targets.target_kcal,
        "protein_g": targets.protein_g,
        "fat_g": targets.fat_g,
        "carbs_g": targets.carbs_g,
    }
    tolerances = {
        "kcal": max(50, targets.target_kcal * 0.05),
        "protein_g": max(15, targets.protein_g * 0.12),
        "fat_g": max(10, targets.fat_g * 0.15),
        "carbs_g": max(20, targets.carbs_g * 0.15),
    }
    if any(
        abs(declared[field] - target_values[field]) > tolerances[field]
        for field in fields
    ):
        return False
    if "http://" in plan.markdown.casefold() or "https://" in plan.markdown.casefold():
        return False
    blocked = [str(item) for item in (profile.get("allergies") or [])]
    for item in profile.get("dietary_preferences") or []:
        preference = str(item)
        if preference.casefold().startswith("dislike:"):
            blocked.append(preference.split(":", 1)[1])
        elif not preference.casefold().startswith(("like:", "diet:")):
            blocked.append(preference)
    offered_foods = " ".join(
        str(food)
        for meal in meals
        for food in meal.get("foods", [])
    ).casefold()
    for item in blocked:
        normalized = str(item).casefold().strip()
        for prefix in ("не люблю ", "ненавижу ", "не ем ", "избегаю ", "аллергия на "):
            if normalized.startswith(prefix):
                normalized = normalized.removeprefix(prefix).strip()
        if len(normalized) > 2 and normalized in offered_foods:
            return False
    return True


def validate_workout_plan(plan: GroundedPlan, profile: dict[str, Any]) -> bool:
    """Check the generated program against Forma's non-negotiable framework."""
    data = plan.metadata or {}
    framework = str(data.get("framework") or "")
    sex = profile.get("sex")
    experience = profile.get("training_experience")
    expected = (
        "female_lower_focus"
        if sex == "female"
        else "full_body" if experience == "beginner" else "three_day_split"
    )
    if framework != expected:
        return False
    try:
        days = int(data.get("days"))
    except (TypeError, ValueError):
        return False
    if not 2 <= days <= 6:
        return False
    text = plan.markdown.casefold()
    if "http://" in text or "https://" in text:
        return False
    required_groups = (
        ("подход", "set"),
        ("повтор", "rep"),
        ("отдых", "rest"),
        ("прогресс", "progress"),
        ("размин", "warm-up", "warmup"),
    )
    if any(not any(marker in text for marker in group) for group in required_groups):
        return False
    has_health_context = bool(
        profile.get("injuries")
        or str(profile.get("medical_notes") or "").strip()
        or profile.get("is_pregnant")
    )
    if has_health_context and not any(
        marker in text for marker in ("врач", "специалист", "doctor", "clinician")
    ):
        return False
    return True
