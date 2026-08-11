from app.providers.grounded_plans import parse_grounded_plan


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
