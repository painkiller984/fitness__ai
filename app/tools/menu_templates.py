from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from app.agent.state import NutritionTargets


@dataclass(frozen=True, slots=True)
class MealOption:
    title: str
    items: str
    kcal: int
    protein: int
    fat: int
    carbs: int
    tags: tuple[str, ...] = ()


MEALS: dict[str, tuple[MealOption, ...]] = {
    "Завтрак": (
        MealOption("Овсянка и яйца", "овсянка 60 г, 2 яйца, ягоды", 430, 24, 16, 49, ("овсянка", "яйца")),
        MealOption("Творожный завтрак", "творог 5% 200 г, банан, цельнозерновой хлеб", 440, 38, 12, 50, ("творог", "молочное")),
        MealOption("Йогурт-боул", "греческий йогурт, мюсли, ягоды, орехи", 425, 31, 15, 48, ("йогурт", "молочное", "орехи")),
    ),
    "Обед": (
        MealOption("Курица с гречкой", "куриная грудка 180 г, гречка, овощи, масло", 560, 52, 17, 53, ("курица", "гречка")),
        MealOption("Индейка с рисом", "филе индейки 180 г, рис, овощи, масло", 555, 50, 16, 56, ("индейка", "рис")),
        MealOption("Рыба с картофелем", "белая рыба 220 г, картофель, салат, масло", 545, 48, 16, 55, ("рыба", "картофель")),
    ),
    "Перекус": (
        MealOption("Творог и фрукты", "творог 5% 180 г, яблоко, 15 г орехов", 330, 31, 13, 30, ("творог", "молочное", "орехи")),
        MealOption("Протеиновый перекус", "протеин 30 г, банан, 20 г арахисовой пасты", 340, 29, 12, 38, ("протеин", "арахис")),
        MealOption("Йогурт с ягодами", "греческий йогурт, ягоды, хлебцы", 315, 28, 7, 37, ("йогурт", "молочное")),
    ),
    "Ужин": (
        MealOption("Рыба с овощами", "лосось 150 г, овощи, рис", 480, 37, 20, 39, ("рыба", "рис")),
        MealOption("Говядина с овощами", "постная говядина 170 г, овощи, картофель", 500, 43, 18, 42, ("говядина", "картофель")),
        MealOption("Омлет с гарниром", "омлет из 3 яиц, овощи, цельнозерновой хлеб", 470, 31, 22, 38, ("яйца", "овощи")),
    ),
}


def build_daily_menu(targets: NutritionTargets, profile: dict[str, Any] | None = None, language: str = "ru") -> str:
    """Build a varied audited menu from a local food library."""
    profile = profile or {}
    choices = {meal: _pick_option(meal, profile) for meal in MEALS}
    totals = _totals(choices.values())
    portion_factor = min(1.35, max(0.70, targets.target_kcal / totals[0]))
    if language == "en":
        return _english_menu(targets, totals, portion_factor)

    lines = [
        "Готовый рацион на день. Он собран из проверенной локальной библиотеки с учётом сохранённых предпочтений.",
        "",
    ]
    for meal, option in choices.items():
        alternatives = [item.title for item in _allowed_options(meal, profile) if item.title != option.title][:2]
        lines.append(f"**{meal} — {option.title}:** {option.items}.")
        if alternatives:
            lines.append("Замены: " + "; ".join(alternatives) + ".")
    kcal, protein, fat, carbs = totals
    lines.extend([
        "",
        f"**Персональные порции:** базовые порции умножены на {portion_factor:.2f} под вашу цель.",
        f"**Итог меню:** {round(kcal * portion_factor)} ккал, Б/Ж/У: {round(protein * portion_factor)}/{round(fat * portion_factor)}/{round(carbs * portion_factor)} г.",
        f"**Цель:** {targets.target_kcal} ккал, Б/Ж/У: {targets.protein_g}/{targets.fat_g}/{targets.carbs_g} г.",
        f"Разница: {_signed(round(kcal * portion_factor) - targets.target_kcal)} ккал, Б {_signed(round(protein * portion_factor) - targets.protein_g)} г, Ж {_signed(round(fat * portion_factor) - targets.fat_g)} г, У {_signed(round(carbs * portion_factor) - targets.carbs_g)} г.",
        "Для неизвестного продукта или бренда Forma уточнит КБЖУ через поиск; эти данные не сохраняются в профиль.",
    ])
    return "\n".join(lines)


def is_known_food(message: str) -> bool:
    text = message.casefold()
    return any(tag in text for options in MEALS.values() for option in options for tag in option.tags)


def requested_portion_grams(message: str) -> float | None:
    match = re.search(r"\b(\d{1,4}(?:[.,]\d+)?)\s*(?:г|гр|g)\b", message.casefold())
    return float(match.group(1).replace(",", ".")) if match else None


def build_menu_with_found_food(
    targets: NutritionTargets,
    profile: dict[str, Any],
    *,
    name: str,
    grams: float,
    kcal_per_100g: float,
    protein_per_100g: float,
    fat_per_100g: float,
    carbs_per_100g: float,
    sources: tuple[str, ...],
) -> str:
    """Apply grounded nutrition to the current menu without persisting it."""
    choices = {meal: _pick_option(meal, profile) for meal in MEALS}
    kcal, protein, fat, carbs = _totals(choices.values())
    factor = grams / 100
    extra = (
        round(kcal_per_100g * factor), round(protein_per_100g * factor),
        round(fat_per_100g * factor), round(carbs_per_100g * factor),
    )
    adjusted = tuple(base + addition for base, addition in zip((kcal, protein, fat, carbs), extra))
    return "\n".join([
        build_daily_menu(targets, profile),
        "",
        f"**Учтено дополнительно:** {name}, {grams:g} г — {extra[0]} ккал, Б/Ж/У {extra[1]}/{extra[2]}/{extra[3]} г.",
        f"**Новый итог:** {adjusted[0]} ккал, Б/Ж/У {adjusted[1]}/{adjusted[2]}/{adjusted[3]} г.",
        "Это значение применено только к текущему расчёту и не сохранено в профиль.",
    ])


def _allowed_options(meal: str, profile: dict[str, Any]) -> list[MealOption]:
    blocked = {str(item).casefold() for item in [*profile.get("allergies", []), *profile.get("dietary_preferences", [])]}
    available = [
        option for option in MEALS[meal]
        if not any(_preference_blocks_tag(preference, tag) for preference in blocked for tag in option.tags)
    ]
    return available or list(MEALS[meal])


def _pick_option(meal: str, profile: dict[str, Any]) -> MealOption:
    options = _allowed_options(meal, profile)
    seed = f"{profile.get('name', '')}:{profile.get('goal', '')}:{meal}"
    return options[sum(ord(char) for char in seed) % len(options)]


def _preference_blocks_tag(preference: str, tag: str) -> bool:
    """A small Russian-friendly stem match for saved likes/dislikes such as гречку/гречка."""
    return tag in preference or (len(tag) >= 5 and tag[:5] in preference)


def _totals(options: Any) -> tuple[int, int, int, int]:
    return tuple(sum(getattr(option, field) for option in options) for field in ("kcal", "protein", "fat", "carbs"))


def _english_menu(
    targets: NutritionTargets, totals: tuple[int, int, int, int], portion_factor: float
) -> str:
    kcal, protein, fat, carbs = totals
    return (
        "Ready-made daily menu from Forma's local food library. Each meal has two interchangeable alternatives.\n\n"
        f"Personal portions use a {portion_factor:.2f} multiplier for your target.\n"
        f"Menu total: {round(kcal * portion_factor)} kcal, P/F/C "
        f"{round(protein * portion_factor)}/{round(fat * portion_factor)}/{round(carbs * portion_factor)} g. "
        f"Target: {targets.target_kcal} kcal, P/F/C {targets.protein_g}/{targets.fat_g}/{targets.carbs_g} g.\n\n"
        "For an unknown food or brand, Forma can verify nutrition data through search and use it only for the current calculation."
    )


def _signed(value: int) -> str:
    return f"{value:+d}"
