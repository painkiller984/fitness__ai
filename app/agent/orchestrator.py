from __future__ import annotations

from typing import Protocol

from app.agent.memory import ConversationMemory
from app.agent.plan_execute import build_execution_plan
from app.agent.router import route_intent
from app.agent.state import CoachReply, JudgeResult, NutritionTargets, UserProfile
from app.guards.safety import assess_safety
from app.judges.plan_judge import PlanJudge
from app.knowledge.rag import FitnessKnowledgeRetriever
from app.tools.calorie_macros import calculate_nutrition_targets


class ResponseGenerator(Protocol):
    async def generate(
        self,
        profile: UserProfile,
        message: str,
        targets: NutritionTargets,
        knowledge: list[str],
        history: list[dict[str, str]],
        feedback: list[str] | None = None,
    ) -> str: ...


class FitnessAgent:
    """Bounded agent pipeline: Router → Tools → RAG → Generator → Judge."""

    def __init__(
        self,
        generator: ResponseGenerator,
        judge: PlanJudge,
        retriever: FitnessKnowledgeRetriever,
    ) -> None:
        self.generator = generator
        self.judge = judge
        self.retriever = retriever

    async def respond(
        self, profile: UserProfile, message: str, memory: ConversationMemory | None = None
    ) -> CoachReply:
        intent = route_intent(message)
        safety = assess_safety(profile, message)
        execution_plan = build_execution_plan(intent, safety)
        if not safety.can_generate_plan:
            reply = CoachReply(
                intent=intent,
                message=safety.user_message or "",
                safety=safety,
                execution_plan=execution_plan,
            )
            self._remember(memory, message, reply.message)
            return reply

        targets = calculate_nutrition_targets(profile)
        knowledge = self.retriever.retrieve(message)
        history = memory.recent() if memory else []
        draft = await self.generator.generate(profile, message, targets, knowledge, history)
        judge = await self.judge.judge(profile, message, targets, draft)

        if judge.verdict == "revise":
            draft = await self.generator.generate(
                profile, message, targets, knowledge, history, feedback=judge.revision_instructions
            )
            judge = await self.judge.judge(profile, message, targets, draft)

        if judge.verdict != "approve":
            reply = CoachReply(
                intent=intent,
                message=(
                    "Не удалось безопасно сформировать персональную рекомендацию. "
                    "Уточните ограничения или обратитесь к профильному специалисту."
                ),
                targets=targets,
                judge=judge,
                safety=safety,
                execution_plan=execution_plan,
            )
            self._remember(memory, message, reply.message)
            return reply

        reply = CoachReply(
            intent=intent,
            message=draft,
            targets=targets,
            judge=judge,
            safety=safety,
            execution_plan=execution_plan,
        )
        self._remember(memory, message, reply.message)
        return reply

    @staticmethod
    def _remember(memory: ConversationMemory | None, message: str, reply: str) -> None:
        if memory:
            memory.add("user", message)
            memory.add("assistant", reply)
