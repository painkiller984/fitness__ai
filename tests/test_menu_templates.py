from app.agent.state import NutritionTargets
from app.tools.menu_templates import build_daily_menu, build_menu_with_found_food


def targets() -> NutritionTargets:
    return NutritionTargets(
        bmr_kcal=1600, maintenance_kcal=2200, target_kcal=1874,
        protein_g=173, fat_g=77, carbs_g=123,
    )


def test_menu_shows_auditable_total_target_and_replacements() -> None:
    menu = build_daily_menu(targets())

    assert "Итог меню" in menu
    assert "Цель" in menu
    assert "Разница" in menu
    assert "Замены:" in menu


def test_menu_excludes_a_saved_dislike_when_an_alternative_exists() -> None:
    menu = build_daily_menu(targets(), {"name": "Антон", "dietary_preferences": ["не люблю гречку"]})

    assert "Курица с гречкой" not in menu


def test_grounded_food_is_added_only_to_current_calculation() -> None:
    menu = build_menu_with_found_food(
        targets(), {}, name="Шоколад", grams=20,
        kcal_per_100g=550, protein_per_100g=7, fat_per_100g=35, carbs_per_100g=50,
        sources=("https://example.test/chocolate",),
    )

    assert "Учтено дополнительно" in menu
    assert "110 ккал" in menu
    assert "https://example.test/chocolate" in menu
