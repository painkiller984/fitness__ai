from types import SimpleNamespace

import asyncio

from app.providers.grounded_plans import (
    GeminiGroundedPlanSearch,
    GroundedPlan,
    _extract_citations,
    parse_generated_plan,
    parse_grounded_plan,
    validate_menu_plan,
    validate_workout_plan,
)
from app.agent.state import NutritionTargets


def test_grounded_plan_parser_accepts_cited_plan() -> None:
    raw = (
        '{"plan_markdown":"Персональный план с разминкой, упражнениями, подходами, '
        'повторениями, отдыхом и понятной прогрессией нагрузки на четыре недели.",'
        '"sources":["https://example.test/guidance"]}'
    )

    result = parse_grounded_plan(raw)

    assert result is not None
    assert "прогрессией" in result.markdown
    assert result.sources == ("https://example.test/guidance",)


def test_grounded_plan_parser_rejects_uncited_or_short_output() -> None:
    assert parse_grounded_plan('{"plan_markdown":"Коротко","sources":["https://example.test"]}') is None
    assert parse_grounded_plan('{"plan_markdown":"Достаточно длинный текст без источника и проверки данных."}') is None


def test_grounded_plan_accepts_plain_markdown_with_api_citations() -> None:
    markdown = (
        "Персональный план тренировки с разминкой, четырьмя упражнениями, "
        "подходами, повторениями, отдыхом и постепенной прогрессией нагрузки."
    )

    result = parse_grounded_plan(markdown, ("https://example.test/research",))

    assert result is not None
    assert result.sources == ("https://example.test/research",)
    assert "https://example.test" not in result.render("ru")


def test_citations_are_extracted_from_interaction_annotations() -> None:
    annotation = SimpleNamespace(type="url_citation", url="https://example.test/source")
    block = SimpleNamespace(annotations=[annotation])
    interaction = SimpleNamespace(steps=[SimpleNamespace(content=[block])])

    assert _extract_citations(interaction) == ("https://example.test/source",)


def test_direct_gemini_generation_accepts_detailed_uncited_plan() -> None:
    raw = (
        "Персональная программа содержит разминку, три тренировочных дня, упражнения, "
        "подходы, повторения, отдых между подходами и постепенную прогрессию нагрузки."
    )

    result = parse_generated_plan(raw)

    assert result is not None
    assert result.sources == ()


def test_generation_falls_back_to_normal_gemini_when_search_has_no_citations() -> None:
    calls: list[dict] = []

    class Interactions:
        def create(self, **kwargs):
            calls.append(kwargs)
            if "tools" in kwargs:
                return SimpleNamespace(output_text="Ответ поиска без подтверждённых ссылок.", steps=[])
            return SimpleNamespace(
                output_text=(
                    "Индивидуальная программа с разминкой, тремя тренировочными днями, "
                    "подходами, повторениями, отдыхом и понятной прогрессией нагрузки."
                )
            )

    provider = GeminiGroundedPlanSearch.__new__(GeminiGroundedPlanSearch)
    provider.client = SimpleNamespace(interactions=Interactions())
    provider.model = "test-model"

    result = asyncio.run(provider._generate("Составь программу по заданному каркасу."))

    assert result is not None
    assert len(calls) == 2
    assert "tools" in calls[0]
    assert "tools" not in calls[1]


def test_menu_validator_accepts_consistent_totals_and_saved_like() -> None:
    targets = NutritionTargets(
        bmr_kcal=1600, maintenance_kcal=2200, target_kcal=2000,
        protein_g=150, fat_g=70, carbs_g=220,
    )
    plan = GroundedPlan(
        "Персональное меню без ссылок с четырьмя приёмами пищи и точными весами продуктов.",
        (),
        {
            "daily_totals": {"kcal": 2000, "protein_g": 150, "fat_g": 70, "carbs_g": 220},
            "meals": [
                {
                    "name": "День",
                    "foods": ["гречка", "курица", "овощи"],
                    "kcal": 2000,
                    "protein_g": 150,
                    "fat_g": 70,
                    "carbs_g": 220,
                }
            ],
        },
    )

    assert validate_menu_plan(plan, targets, {"dietary_preferences": ["like:гречка"]})
    assert not validate_menu_plan(plan, targets, {"dietary_preferences": ["dislike:гречка"]})


def test_menu_validator_rejects_unverified_declared_total() -> None:
    targets = NutritionTargets(
        bmr_kcal=1600, maintenance_kcal=2200, target_kcal=2000,
        protein_g=150, fat_g=70, carbs_g=220,
    )
    plan = GroundedPlan(
        "Персональное меню без ссылок с точными весами продуктов и итоговыми значениями.",
        (),
        {
            "daily_totals": {"kcal": 2000, "protein_g": 150, "fat_g": 70, "carbs_g": 220},
            "meals": [{
                "name": "День", "foods": ["овсянка"], "kcal": 1700,
                "protein_g": 150, "fat_g": 70, "carbs_g": 220,
            }],
        },
    )

    assert not validate_menu_plan(plan, targets, {})


def test_workout_validator_enforces_level_and_safety_framework() -> None:
    markdown = (
        "Разминка 8 минут. Каждое упражнение: 3 подхода по 8–12 повторений, "
        "отдых 90 секунд. Прогрессия нагрузки выполняется постепенно."
    )
    valid = GroundedPlan(
        markdown, (), {"framework": "three_day_split", "focus": "upper", "days": 3}
    )
    wrong = GroundedPlan(
        markdown, (), {"framework": "full_body", "focus": "upper", "days": 3}
    )
    profile = {"sex": "male", "training_experience": "advanced"}

    assert validate_workout_plan(valid, profile)
    assert not validate_workout_plan(wrong, profile)
