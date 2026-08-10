from app.agent.state import NutritionTargets
from app.tools.menu_templates import build_daily_menu


def targets() -> NutritionTargets:
    return NutritionTargets(
        bmr_kcal=1600,
        maintenance_kcal=2200,
        target_kcal=1874,
        protein_g=173,
        fat_g=77,
        carbs_g=123,
    )


def test_menu_shows_calculated_total_and_target_delta() -> None:
    menu = build_daily_menu(targets())

    assert "Итог меню" in menu
    assert "Цель" in menu
    assert "Разница" in menu
    assert "1874 ккал" in menu


def test_zephyr_swap_is_exact_and_visible() -> None:
    base = build_daily_menu(targets())
    zephyr = build_daily_menu(targets(), include_zephyr=True)

    assert "Зефир — 30 г" in zephyr
    assert "заменяет 80 г гречки" in zephyr
    assert base != zephyr
    assert "заменить рыбу" not in base
