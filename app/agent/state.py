from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class Sex(StrEnum):
    FEMALE = "female"
    MALE = "male"


class Goal(StrEnum):
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"
    WELLBEING = "wellbeing"


class ActivityLevel(StrEnum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class TrainingPlace(StrEnum):
    HOME = "home"
    GYM = "gym"
    BOTH = "both"
    OUTDOORS = "outdoors"


class TrainingExperience(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class UserProfile(BaseModel):
    user_id: UUID | None = None
    name: str = Field(min_length=1, max_length=80)
    surname: str | None = Field(default=None, min_length=1, max_length=80)
    age: int = Field(ge=14, le=100)
    sex: Sex
    height_cm: float = Field(ge=120, le=230)
    weight_kg: float = Field(ge=35, le=350)
    goal: Goal
    activity_level: ActivityLevel
    training_place: TrainingPlace | None = None
    training_experience: TrainingExperience | None = None
    training_days_per_week: int | None = Field(default=None, ge=1, le=7)
    available_equipment: list[str] = Field(default_factory=list)
    equipment_screened: bool = False
    health_screened: bool = False
    dietary_preferences: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    injuries: list[str] = Field(default_factory=list)
    medical_notes: str = Field(default="", max_length=1000)
    is_pregnant: bool = False

    @field_validator("dietary_preferences", "allergies", "injuries", "available_equipment", mode="before")
    @classmethod
    def split_comma_values(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class NutritionTargets(BaseModel):
    bmr_kcal: int
    maintenance_kcal: int
    target_kcal: int
    protein_g: int
    fat_g: int
    carbs_g: int
    warnings: list[str] = Field(default_factory=list)


class SafetyDecision(BaseModel):
    level: str = Field(pattern="^(low|medium|high)$")
    can_generate_plan: bool
    reasons: list[str] = Field(default_factory=list)
    user_message: str | None = None


class JudgeResult(BaseModel):
    verdict: str = Field(pattern="^(approve|revise|block)$")
    violations: list[str] = Field(default_factory=list)
    revision_instructions: list[str] = Field(default_factory=list)


class CoachReply(BaseModel):
    intent: str
    message: str
    targets: NutritionTargets | None = None
    judge: JudgeResult | None = None
    safety: SafetyDecision
    execution_plan: list[str] = Field(default_factory=list)
