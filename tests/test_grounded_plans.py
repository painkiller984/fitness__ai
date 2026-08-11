from types import SimpleNamespace

import asyncio

from app.providers.grounded_plans import (
    GeminiGroundedPlanSearch,
    _extract_citations,
    normalize_plan_markdown,
    parse_generated_plan,
    parse_grounded_plan,
)


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


def test_outer_markdown_fence_is_removed() -> None:
    plan = "```markdown\n# Меню\n\n**Завтрак:** омлет\n```"

    assert normalize_plan_markdown(plan) == "# Меню\n\n**Завтрак:** омлет"


def test_generated_plan_removes_outer_markdown_fence() -> None:
    raw = "```markdown\n# Персональное меню\n\n" + ("Подробный рацион. " * 8) + "\n```"

    result = parse_generated_plan(raw)

    assert result is not None
    assert result.markdown.startswith("# Персональное меню")
    assert "```" not in result.markdown


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
