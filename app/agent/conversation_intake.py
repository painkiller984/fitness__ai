from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.agent.state import ActivityLevel, Goal, Sex, TrainingPlace, UserProfile


@dataclass(slots=True)
class ConversationIntake:
    """Collects the minimum safe profile through short chat questions."""

    values: dict[str, object] = field(default_factory=dict)
    step: int = 0

    questions = (
        ("goal", "Какая у вас основная цель: снизить вес, набрать мышечную массу, поддерживать форму или улучшить самочувствие?"),
        ("name", "Как я могу к вам обращаться?"),
        ("age", "Сколько вам лет?"),
        ("sex", "Укажите пол для расчёта: мужской или женский."),
        ("height_cm", "Какой у вас рост в сантиметрах?"),
        ("weight_kg", "Какой сейчас вес в килограммах?"),
        ("activity_level", "Какой у вас обычный уровень активности: низкий, лёгкий, умеренный, высокий или очень высокий?"),
        ("training_place", "Где планируете тренироваться: дома, в зале или и там и там?"),
        ("dietary_preferences", "Есть предпочтения в питании? Если нет — напишите «нет»."),
        ("allergies", "Есть пищевые аллергии? Если нет — напишите «нет»."),
        ("injuries", "Есть травмы или ограничения для тренировок? Если нет — напишите «нет»."),
    )

    @property
    def is_complete(self) -> bool:
        return self.step >= len(self.questions)

    def first_question(self) -> str:
        return self.questions[0][1]

    def accept(self, answer: str) -> str:
        field_name, _ = self.questions[self.step]
        value = self._parse(field_name, answer)
        if value is None:
            return self._clarification(field_name)
        self.values[field_name] = value
        self.step += 1
        if self.is_complete:
            return "Спасибо, профиль собран. Теперь могу делать персональные расчёты и составлять планы. С чего начнём?"
        return self.questions[self.step][1]

    def build_profile(self) -> UserProfile:
        return UserProfile(**self.values)

    @staticmethod
    def _words(answer: str) -> list[str]:
        return [part.strip() for part in answer.split(",") if part.strip()] if answer.casefold().strip() not in {"нет", "не знаю", "-"} else []

    def _parse(self, field_name: str, answer: str) -> object | None:
        text = answer.casefold().strip()
        if field_name == "goal":
            mapping = {
                Goal.WEIGHT_LOSS: ("сниз", "похуд", "вес"),
                Goal.MUSCLE_GAIN: ("набр", "мышц", "мас"),
                Goal.MAINTENANCE: ("поддерж", "форм"),
                Goal.WELLBEING: ("самочув", "здоров"),
            }
            return next((goal for goal, markers in mapping.items() if any(marker in text for marker in markers)), None)
        if field_name == "name":
            return answer.strip() if 1 <= len(answer.strip()) <= 80 and not any(char.isdigit() for char in answer) else None
        if field_name in {"age", "height_cm", "weight_kg"}:
            match = re.search(r"\d+(?:[.,]\d+)?", text)
            if not match:
                return None
            value = float(match.group().replace(",", "."))
            if field_name == "age":
                return int(value) if 14 <= value <= 100 and value.is_integer() else None
            if field_name == "height_cm":
                return value if 120 <= value <= 230 else None
            return value if 35 <= value <= 350 else None
        if field_name == "sex":
            if "муж" in text:
                return Sex.MALE
            if "жен" in text:
                return Sex.FEMALE
            return None
        if field_name == "activity_level":
            mapping = (
                (ActivityLevel.VERY_HIGH, ("очень высок", "физическ")),
                (ActivityLevel.HIGH, ("высок",)),
                (ActivityLevel.MODERATE, ("умерен", "средн")),
                (ActivityLevel.LIGHT, ("лёгк", "легк")),
                (ActivityLevel.SEDENTARY, ("низк", "мало", "сидяч")),
            )
            return next((level for level, markers in mapping if any(marker in text for marker in markers)), None)
        if field_name == "training_place":
            if "зал" in text and ("дом" in text or "оба" in text):
                return TrainingPlace.BOTH
            if "зал" in text:
                return TrainingPlace.GYM
            if "дом" in text:
                return TrainingPlace.HOME
            return None
        return self._words(answer)

    @staticmethod
    def _clarification(field_name: str) -> str:
        clarifications = {
            "goal": "Выберите одну цель: снижение веса, набор мышечной массы, поддержание формы или самочувствие.",
            "name": "Напишите, пожалуйста, имя — без цифр.",
            "age": "Укажите возраст числом от 14 до 100.",
            "sex": "Ответьте «мужской» или «женский».",
            "height_cm": "Укажите рост числом в сантиметрах, например 178.",
            "weight_kg": "Укажите вес числом в килограммах, например 72.5.",
            "activity_level": "Ответьте: низкий, лёгкий, умеренный, высокий или очень высокий.",
            "training_place": "Ответьте: дома, в зале или дома и в зале.",
        }
        return clarifications.get(field_name, "Напишите ответ или «нет», если ограничений нет.")
