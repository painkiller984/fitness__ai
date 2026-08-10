from __future__ import annotations

import re


def response_language(message: str) -> str:
    """Use English only for clearly English input; Russian remains the default."""
    has_cyrillic = bool(re.search(r"[а-яё]", message, re.I))
    has_latin = bool(re.search(r"[a-z]", message, re.I))
    return "en" if has_latin and not has_cyrillic else "ru"
