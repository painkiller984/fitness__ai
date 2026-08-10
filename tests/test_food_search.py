from app.providers.food_search import parse_grounded_food


def test_grounded_food_parser_accepts_valid_cited_json() -> None:
    result = parse_grounded_food(
        '{"name":"Chocolate","kcal_per_100g":550,"protein_per_100g":7,"fat_per_100g":35,"carbs_per_100g":50,"sources":["https://example.test"]}'
    )
    assert result and result.kcal_per_100g == 550


def test_grounded_food_parser_rejects_uncited_or_incomplete_data() -> None:
    assert parse_grounded_food('{"name":"Chocolate"}') is None
