from __future__ import annotations

import re
from typing import Any


NON_NAME_WORDS = {
    "голодный",
    "голодная",
    "новичок",
    "спортсмен",
    "веган",
    "вегетарианец",
    "вегетарианка",
    "устал",
    "устала",
    "готов",
    "готова",
    "похудение",
    "похудеть",
    "снижение",
    "поддержание",
    "набор",
    "weight-loss",
    "weight_loss",
    "maintenance",
    "привет",
    "здравствуйте",
    "hello",
    "hi",
}


def is_valid_profile_name(value: Any) -> bool:
    """Return whether a stored value looks like an explicitly supplied personal name."""
    if not isinstance(value, str):
        return False
    normalized = value.strip().casefold()
    return bool(re.fullmatch(r"[а-яёa-z][а-яёa-z-]{1,79}", normalized, re.I)) and normalized not in NON_NAME_WORDS


def extract_profile_facts(message: str, expected_fields: set[str] | None = None) -> dict[str, Any]:
    """Extract only explicitly stated, durable profile facts from a user message."""
    text = message.casefold()
    facts: dict[str, Any] = {}
    facts.update(_extract_compact_profile(message))
    name = re.search(
        r"(?:меня зовут|мо[её] имя|my name is)\s+([а-яёa-z][а-яёa-z-]{1,79})\b",
        message,
        re.I,
    )
    short_name = re.search(
        r"(?:^|[.!?]\s*)я\s+([а-яёa-z][а-яёa-z-]{1,79})(?=\s*(?:$|[,;.]\s*(?:мне|мой|моя|я)\b))",
        message,
        re.I,
    )
    name = name or short_name
    if name and is_valid_profile_name(name.group(1)):
        facts["name"] = name.group(1).capitalize()
    elif expected_fields and "name" in expected_fields and is_valid_profile_name(message.strip()):
        facts["name"] = message.strip().capitalize()
    age = re.search(r"\b(\d{2})\s*(?:лет|года|год|years? old)\b", text)
    if age and 14 <= int(age.group(1)) <= 100:
        facts["age"] = int(age.group(1))
    height = re.search(r"(?:рост|высота|height)\D{0,12}(\d{3})\b", text)
    height = height or re.search(r"\b(\d{3})\s*cm\s*tall\b", text)
    if height and 120 <= int(height.group(1)) <= 230:
        facts["height_cm"] = int(height.group(1))
    weight = re.search(r"(?:вес|вешу|weight|weigh)\D{0,12}(\d{2,3}(?:[.,]\d+)?)\b", text)
    weight = weight or re.search(r"\b(\d{2,3}(?:[.,]\d+)?)\s*(?:кг|kg)\b", text)
    if weight and 35 <= float(weight.group(1).replace(",", ".")) <= 350:
        facts["weight_kg"] = float(weight.group(1).replace(",", "."))
    if re.search(r"\b(?:female|woman)\b", text):
        facts["sex"] = "female"
    elif re.search(r"\b(?:male|man)\b", text):
        facts["sex"] = "male"
    elif any(word in text for word in ("мужск", "мужчина", "парень")):
        facts["sex"] = "male"
    elif any(word in text for word in ("женск", "женщина", "девушка")):
        facts["sex"] = "female"
    if any(word in text for word in ("похуд", "снизить вес", "снижение веса", "lose weight", "weight loss")):
        facts["goal"] = "weight_loss"
    elif any(word in text for word in ("набрать мышцы", "набор массы", "мышечную массу", "gain muscle", "muscle gain")):
        facts["goal"] = "muscle_gain"
    elif "поддерж" in text or "maintain" in text:
        facts["goal"] = "maintenance"
    elif any(marker in text for marker in ("wellbeing", "feel better")):
        facts["goal"] = "wellbeing"
    if any(marker in text for marker in ("1 раз", "2 раза", "лёгк", "легк", "1 time", "2 times", "light activity")):
        facts["activity_level"] = "light"
    elif any(marker in text for marker in ("3 раза", "4 раза", "5 раз", "умерен", "3 times", "4 times", "5 times", "moderate")):
        facts["activity_level"] = "moderate"
    elif any(marker in text for marker in ("6 раз", "7 раз", "высок", "6 times", "7 times", "high activity")):
        facts["activity_level"] = "high"
    elif any(marker in text for marker in ("не тренир", "сидяч", "малоподвиж", "sedentary", "don't train", "do not train")):
        facts["activity_level"] = "sedentary"
    if any(marker in text for marker in ("дома", "домашн", "home")):
        facts["training_place"] = "home"
    if any(marker in text for marker in ("зал", "gym")):
        facts["training_place"] = "both" if facts.get("training_place") == "home" else "gym"
    if any(marker in text for marker in ("улиц", "парк", "outdoor")):
        facts["training_place"] = "both" if facts.get("training_place") else "outdoors"
    if any(marker in text for marker in ("нович", "начинающ", "beginner", "никогда не тренир")):
        facts["training_experience"] = "beginner"
    elif any(marker in text for marker in ("продвин", "опытн", "advanced", "больше 3 лет", "более 3 лет")):
        facts["training_experience"] = "advanced"
    elif any(marker in text for marker in ("средн", "intermediate", "около года", "1 год", "2 года", "3 года")):
        facts["training_experience"] = "intermediate"
    days = re.search(
        r"\b([1-7])\s*(?:раза?|дн(?:я|ей)|times?|days?)\s*(?:в|per|a)?\s*(?:недел|week)",
        text,
    )
    if days:
        facts["training_days_per_week"] = int(days.group(1))
    equipment = _extract_equipment(text)
    if equipment is not None:
        facts["available_equipment"] = equipment
        facts["equipment_screened"] = True
    health = _extract_health_screening(message)
    if health is not None:
        facts.update(health)
    if expected_fields and {"age", "sex", "height_cm", "weight_kg"} & expected_fields:
        facts.update(_extract_expected_body_values(message, facts))
    return facts


def _extract_equipment(text: str) -> list[str] | None:
    if any(marker in text for marker in ("без оборудования", "ничего нет", "только свой вес", "no equipment", "bodyweight only")):
        return []
    markers = {
        "dumbbells": ("гантел", "dumbbell"),
        "barbell": ("штанг", "barbell"),
        "resistance_bands": ("резин", "эспандер", "band"),
        "pull_up_bar": ("турник", "pull-up bar", "pull up bar"),
        "machines": ("тренаж", "machine"),
        "bench": ("скам", "bench"),
        "kettlebells": ("гиря", "гири", "kettlebell"),
    }
    found = [name for name, keywords in markers.items() if any(keyword in text for keyword in keywords)]
    return found or None


def _extract_health_screening(message: str) -> dict[str, Any] | None:
    text = message.casefold()
    if any(marker in text for marker in (
        "травм нет", "нет травм", "ограничений нет", "ничего не болит", "проблем со здоровьем нет",
        "no injuries", "no health issues",
    )):
        return {"health_screened": True, "injuries": [], "medical_notes": ""}
    if any(marker in text for marker in (
        "травм", "болит", "боль", "грыж", "давлен", "диабет", "астм", "беремен", "операц",
        "injury", "pain", "condition", "pregnan",
    )):
        facts: dict[str, Any] = {"health_screened": True, "medical_notes": message.strip()[:1000]}
        if any(marker in text for marker in ("травм", "болит", "боль", "injury", "pain")):
            facts["injuries"] = [message.strip()[:300]]
        if "беремен" in text or "pregnan" in text:
            facts["is_pregnant"] = True
        return facts
    return None


def _extract_expected_body_values(message: str, existing: dict[str, Any]) -> dict[str, Any]:
    """Read an ordered free-form body summary while the onboarding flow expects it."""
    result: dict[str, Any] = {}
    numbers = [float(value.replace(",", ".")) for value in re.findall(r"\b\d{2,3}(?:[.,]\d+)?\b", message)]
    for field in ("age", "height_cm", "weight_kg"):
        if field in existing:
            try:
                numbers.remove(float(existing[field]))
            except (TypeError, ValueError):
                pass
    if "age" not in existing:
        age = next((value for value in numbers if 14 <= value <= 100), None)
        if age is not None:
            result["age"] = int(age)
            numbers.remove(age)
    if "height_cm" not in existing:
        height = next((value for value in numbers if 120 <= value <= 230), None)
        if height is not None:
            result["height_cm"] = int(height)
            numbers.remove(height)
    if "weight_kg" not in existing:
        weight = next((value for value in numbers if 35 <= value <= 350), None)
        if weight is not None:
            result["weight_kg"] = weight
    return result


def _extract_compact_profile(message: str) -> dict[str, Any]:
    """Recognize a natural ordered summary such as: Anton, 27, male, 172, 93, weight loss."""
    parts = [part.strip() for part in message.split(",") if part.strip()]
    if len(parts) < 5:
        return {}
    joined = " ".join(parts).casefold()
    has_sex = bool(
        re.search(r"\b(?:male|female|man|woman)\b", joined)
        or any(marker in joined for marker in ("мужск", "мужчина", "женск", "женщина"))
    )
    has_goal = any(
        marker in joined
        for marker in (
            "похуд",
            "снижение веса",
            "набрать мышцы",
            "набор массы",
            "поддерж",
            "lose weight",
            "weight loss",
            "gain muscle",
            "muscle gain",
            "maintain",
        )
    )
    if not (has_sex and has_goal):
        return {}

    result: dict[str, Any] = {}
    if is_valid_profile_name(parts[0]):
        result["name"] = parts[0].capitalize()
    numeric_parts: list[float] = []
    for part in parts[1:]:
        match = re.fullmatch(r"(\d{2,3}(?:[.,]\d+)?)\s*(?:лет|года|год|см|кг|years?|cm|kg)?", part, re.I)
        if match:
            numeric_parts.append(float(match.group(1).replace(",", ".")))

    if numeric_parts and 14 <= numeric_parts[0] <= 100:
        result["age"] = int(numeric_parts.pop(0))
    height_index = next((i for i, value in enumerate(numeric_parts) if 120 <= value <= 230), None)
    if height_index is not None:
        result["height_cm"] = int(numeric_parts.pop(height_index))
    weight_index = next((i for i, value in enumerate(numeric_parts) if 35 <= value <= 350), None)
    if weight_index is not None:
        result["weight_kg"] = numeric_parts[weight_index]
    return result
