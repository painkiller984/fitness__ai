from __future__ import annotations

from app.agent.state import SafetyDecision


def build_execution_plan(intent: str, safety: SafetyDecision) -> list[str]:
    """Bounded plan: the agent may execute only named, deterministic stages."""
    if not safety.can_generate_plan:
        return ["safety_guard", "specialist_referral"]
    plan = ["safety_guard", "load_profile", "calculate_calorie_macros_tool"]
    if intent in {"meal_plan", "workout_plan", "general_coaching"}:
        plan.append("retrieve_knowledge")
    plan.extend(["generate_response", "validate_response", "plan_judge"])
    return plan
