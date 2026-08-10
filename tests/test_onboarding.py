from app.agent.onboarding import current_onboarding_stage, onboarding_context


def test_onboarding_requires_name_first() -> None:
    stage = current_onboarding_stage({"goal": "weight_loss"})
    assert stage is not None
    assert stage.key == "name"
    assert stage.missing_fields == ("name",)


def test_onboarding_requests_only_missing_body_values() -> None:
    stage = current_onboarding_stage({"name": "Антон", "age": 27, "sex": "male"})
    assert stage is not None
    assert stage.key == "body"
    assert stage.missing_fields == ("height_cm", "weight_kg")


def test_onboarding_moves_to_goal_and_activity() -> None:
    stage = current_onboarding_stage(
        {"name": "Антон", "age": 27, "sex": "male", "height_cm": 172, "weight_kg": 94}
    )
    assert stage is not None
    assert stage.key == "goal_activity"


def test_onboarding_is_complete_after_required_profile() -> None:
    stage = current_onboarding_stage(
        {
            "name": "Антон",
            "age": 27,
            "sex": "male",
            "height_cm": 172,
            "weight_kg": 94,
            "goal": "weight_loss",
            "activity_level": "moderate",
        }
    )
    assert stage is None


def test_onboarding_context_uses_requested_language() -> None:
    stage = current_onboarding_stage({})
    assert stage is not None
    assert "introduce" in onboarding_context(stage, "en")["mandatory_instruction"]
