import asyncio

from app.agent.orchestrator import FitnessAgent
from app.agent.memory import ConversationMemory
from app.agent.router import route_intent
from app.agent.state import ActivityLevel, Goal, Sex, UserProfile
from app.judges.plan_judge import DeterministicPlanJudge
from app.knowledge.rag import FitnessKnowledgeRetriever
from app.providers.deterministic import DeterministicGenerator


def test_router():
    assert route_intent("Составь меню на день") == "meal_plan"
    assert route_intent("Какие упражнения делать дома?") == "workout_plan"


def test_orchestrator_uses_verified_targets():
    profile = UserProfile(
        name="Тест", age=30, sex=Sex.MALE, height_cm=180, weight_kg=80,
        goal=Goal.MAINTENANCE, activity_level=ActivityLevel.MODERATE,
    )
    reply = asyncio.run(
        FitnessAgent(
            DeterministicGenerator(), DeterministicPlanJudge(), FitnessKnowledgeRetriever()
        ).respond(profile, "Рассчитай калории")
    )
    assert reply.targets is not None
    assert str(reply.targets.target_kcal) in reply.message
    assert reply.judge and reply.judge.verdict == "approve"
    assert "calculate_calorie_macros_tool" in reply.execution_plan


def test_agent_keeps_short_session_memory():
    profile = UserProfile(
        name="Тест", age=30, sex=Sex.MALE, height_cm=180, weight_kg=80,
        goal=Goal.MAINTENANCE, activity_level=ActivityLevel.MODERATE,
    )
    memory = ConversationMemory()
    agent = FitnessAgent(
        DeterministicGenerator(), DeterministicPlanJudge(), FitnessKnowledgeRetriever()
    )
    asyncio.run(agent.respond(profile, "Как считать БЖУ?", memory))
    assert [item["role"] for item in memory.recent()] == ["user", "assistant"]
