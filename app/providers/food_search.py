from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GroundedFoodResult:
    name: str
    kcal_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    sources: tuple[str, ...]


class GeminiFoodSearch:
    """Google-grounded nutrition lookup used only for foods absent from Forma's library."""

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def lookup(self, food_request: str) -> GroundedFoodResult | None:
        prompt = (
            "Find nutrition facts for this food or brand using reliable public sources. "
            "Return JSON only with keys name, kcal_per_100g, protein_per_100g, fat_per_100g, "
            "carbs_per_100g and sources (an array of source URLs). If the product variant is ambiguous, return {}. "
            f"Food request: {food_request}"
        )
        interaction = await asyncio.to_thread(
            self.client.interactions.create,
            model=self.model,
            input=prompt,
            tools=[{"type": "google_search"}],
            generation_config={"thinking_level": "minimal"},
            store=False,
        )
        return parse_grounded_food(interaction.output_text or "")


def parse_grounded_food(raw: str) -> GroundedFoodResult | None:
    """Validate model output before it can be used in a calorie calculation."""
    try:
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start : end + 1])
        values = [float(data[key]) for key in ("kcal_per_100g", "protein_per_100g", "fat_per_100g", "carbs_per_100g")]
        if not data.get("name") or values[0] <= 0 or any(value < 0 for value in values[1:]):
            return None
        sources = tuple(str(url) for url in data.get("sources", []) if str(url).startswith("http"))
        if not sources:
            return None
        return GroundedFoodResult(str(data["name"]), *values, sources)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
