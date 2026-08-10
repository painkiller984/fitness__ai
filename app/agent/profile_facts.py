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
}


def extract_profile_facts(message: str) -> dict[str, Any]:
    """Extract only explicitly stated, durable profile facts from a user message."""
    text = message.casefold()
    facts: dict[str, Any] = {}
    name = re.search(r"(?:меня зовут|мо[её] имя)\s+([а-яёa-z][а-яёa-z-]{1,79})\b", message, re.I)
    short_name = re.search(
        r"(?:^|[.!?]\s*)я\s+([а-яёa-z][а-яёa-z-]{1,79})(?=\s*(?:$|[,;.]\s*(?:мне|мой|моя|я)\b))",
        message,
        re.I,
    )
    name = name or short_name
    if name and name.group(1).casefold() not in NON_NAME_WORDS:
        facts["name"] = name.group(1).capitalize()
    age = re.search(r"\b(\d{2})\s*(?:лет|года|год)\b", text)
    if age and 14 <= int(age.group(1)) <= 100:
        facts["age"] = int(age.group(1))
    height = re.search(r"(?:рост|высота)\D{0,12}(\d{3})\b", text)
    if height and 120 <= int(height.group(1)) <= 230:
        facts["height_cm"] = int(height.group(1))
    weight = re.search(r"(?:вес|вешу)\D{0,12}(\d{2,3}(?:[.,]\d+)?)\b", text)
    if weight and 35 <= float(weight.group(1).replace(",", ".")) <= 350:
        facts["weight_kg"] = float(weight.group(1).replace(",", "."))
    if any(word in text for word in ("мужск", "мужчина", "парень")):
        facts["sex"] = "male"
    elif any(word in text for word in ("женск", "женщина", "девушка")):
        facts["sex"] = "female"
    if any(word in text for word in ("похуд", "снизить вес", "снижение веса")):
        facts["goal"] = "weight_loss"
    elif any(word in text for word in ("набрать мышцы", "набор массы", "мышечную массу")):
        facts["goal"] = "muscle_gain"
    elif "поддерж" in text:
        facts["goal"] = "maintenance"
    if any(marker in text for marker in ("1 раз", "2 раза", "лёгк", "легк")):
        facts["activity_level"] = "light"
    elif any(marker in text for marker in ("3 раза", "4 раза", "5 раз", "умерен")):
        facts["activity_level"] = "moderate"
    elif any(marker in text for marker in ("6 раз", "7 раз", "высок")):
        facts["activity_level"] = "high"
    elif any(marker in text for marker in ("не тренир", "сидяч", "малоподвиж")):
        facts["activity_level"] = "sedentary"
    return facts
