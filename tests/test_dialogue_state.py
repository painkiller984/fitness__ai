from app.agent.dialogue_state import (
    enforce_name_gate,
    filter_profile_facts,
    requested_workflow,
    switch_workflow,
    workflow_choice,
)


def test_quick_command_replaces_unfinished_workflow() -> None:
    state = {"active_workflow": "nutrition_targets", "pending_facts": {"age": 27}}

    switch_workflow(state, requested_workflow("workout_plan"))

    assert state == {"active_workflow": "workout_plan", "pending_facts": {}}


def test_ambiguous_request_cancels_unfinished_workflow() -> None:
    state = {"active_workflow": "meal_plan", "pending_facts": {"age": 27}}

    switch_workflow(state, None)

    assert state == {"active_workflow": None, "pending_facts": {}}


def test_workout_cannot_persist_nutrition_body_fields() -> None:
    extracted = {
        "sex": "male",
        "goal": "weight_loss",
        "weight_kg": 93,
        "training_place": "gym",
        "training_experience": "advanced",
    }

    assert filter_profile_facts(extracted, "workout_plan", "workout_setup") == {
        "sex": "male",
        "goal": "weight_loss",
        "training_place": "gym",
        "training_experience": "advanced",
    }


def test_name_stage_keeps_other_explicit_facts_from_the_same_message() -> None:
    facts = {"name": "Антон", "age": 27, "goal": "weight_loss"}
    assert filter_profile_facts(facts, None, "name") == facts


def test_name_gate_does_not_persist_other_facts_without_a_name() -> None:
    facts = {"age": 27, "goal": "weight_loss"}
    assert filter_profile_facts(facts, None, "name") == {}


def test_name_gate_keeps_natural_reply_and_enforces_question() -> None:
    assert enforce_name_gate("Понимаю, что ты не в настроении.", "ru").endswith("Как тебя зовут?")
    assert enforce_name_gate("Хорошо. Назови своё имя.", "ru") == "Хорошо. Назови своё имя."


def test_after_name_bot_offers_two_independent_workflows() -> None:
    reply = workflow_choice("Антон", "ru")
    assert "КБЖУ" in reply
    assert "план тренировок" in reply
