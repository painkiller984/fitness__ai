from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgeSnippet:
    topic: str
    keywords: tuple[str, ...]
    text: str


class FitnessKnowledgeRetriever:
    """Small curated MVP knowledge base; replace with Supabase vector search later."""

    def __init__(self) -> None:
        self._snippets = (
            KnowledgeSnippet(
                topic="warmup_recovery",
                keywords=("размин", "восстанов", "трениров", "упражнен"),
                text="Перед тренировкой нужна постепенная разминка; объём и нагрузку повышают постепенно. Боль — повод остановиться и оценить состояние.",
            ),
            KnowledgeSnippet(
                topic="nutrition_basics",
                keywords=("питан", "меню", "бжу", "калори", "белк"),
                text="Суточные калории и БЖУ — ориентир. Рацион должен учитывать предпочтения, аллергии и доступность продуктов.",
            ),
            KnowledgeSnippet(
                topic="progress",
                keywords=("прогресс", "вес", "сон", "объём"),
                text="Оценивайте тренд за несколько недель, а не единичное измерение. Самочувствие, сон и активность — часть прогресса.",
            ),
        )

    def retrieve(self, query: str, limit: int = 2) -> list[str]:
        normalized = query.casefold()
        matches = [
            snippet.text
            for snippet in self._snippets
            if any(keyword in normalized for keyword in snippet.keywords)
        ]
        return matches[:limit]
