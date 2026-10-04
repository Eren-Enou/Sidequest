"""Descriptive completed-session evidence; never recommendation inputs."""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import Energy, Experience


class OutcomeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RatingCount(OutcomeModel):
    rating: Annotated[int, Field(strict=True, ge=1, le=5)]
    count: Annotated[int, Field(ge=0)]


class RatingSummary(OutcomeModel):
    completed_session_count: Annotated[int, Field(ge=0)]
    average_enjoyment: Annotated[float, Field(ge=1, le=5)] | None
    rating_distribution: list[RatingCount]


class ExperienceOutcomes(RatingSummary):
    desired_experience: Experience | None


class EnergyOutcomes(RatingSummary):
    energy: Energy | None


class RecentOutcome(OutcomeModel):
    session_id: int
    goal_title_snapshot: str
    finished_at: datetime
    enjoyment_rating: Annotated[int, Field(strict=True, ge=1, le=5)]
    desired_experience: Experience | None
    energy: Energy | None


class GameOutcomes(RatingSummary):
    game_id: int
    recent_sessions: list[RecentOutcome]
    by_desired_experience: list[ExperienceOutcomes]
    by_energy: list[EnergyOutcomes]
