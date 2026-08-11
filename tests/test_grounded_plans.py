from types import SimpleNamespace

from app.providers.grounded_plans import _extract_citations, parse_grounded_plan


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
