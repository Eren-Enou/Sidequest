"""Explicit session contracts and versioned, validated start-time evidence."""
from datetime import datetime
from math import isclose, isfinite
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.recommendation_schemas import RecommendationRequest, RecommendationResponse, ScoredCandidateRead
from app.schemas import PositiveInt

# Projection coerces mixed integer/float factors to floats. Allow representation
# noise only (at 100 points, at most ~1e-10); never round or rewrite saved evidence.
SCORE_REL_TOL = 1e-12
SCORE_ABS_TOL = 1e-12


class SessionStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    game_id: PositiveInt
    goal_id: PositiveInt
    situation: RecommendationRequest


class SessionFinish(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actual_duration_minutes: PositiveInt
    enjoyment_rating: Annotated[int, Field(strict=True, ge=1, le=5)]
    progress: Annotated[str, Field(strict=True, min_length=1)]
    notes: Annotated[str, Field(strict=True)] | None = None
    mark_goal_completed: Annotated[bool, Field(strict=True)] = False

    @field_validator("progress", mode="before")
    @classmethod
    def trim_progress(cls, value):
        return value.strip() if isinstance(value, str) else value


class RecommendationSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_version: Literal[1]
    selected: ScoredCandidateRead
    evaluation: RecommendationResponse

    @model_validator(mode="after")
    def consistent_evidence(self):
        result = self.evaluation
        if result.status not in ("clear_recommendation", "multiple_equivalent"):
            raise ValueError("A start snapshot must contain accepted recommendations")
        if self.selected not in result.recommendations or not self.selected.suitable:
            raise ValueError("Selected candidate must be an accepted choice")
        if not result.recommendations or result.winner != result.recommendations[0]:
            raise ValueError("Winner must match the first recommendation choice")
        for item in result.ranked:
            if not isfinite(item.score) or not isclose(
                    item.score, sum(item.breakdown.values()),
                    rel_tol=SCORE_REL_TOL, abs_tol=SCORE_ABS_TOL):
                raise ValueError("Snapshot breakdown must sum to score")
            if {f.name: f.points for f in item.factors} != item.breakdown:
                raise ValueError("Snapshot factor contributions must match breakdown")
        if any(item not in result.ranked for item in result.recommendations):
            raise ValueError("Choices must be present in the saved ranking")
        if result.evaluated_at.tzinfo is None or result.evaluated_at.utcoffset() is None:
            raise ValueError("Snapshot timestamp must be aware")
        return self


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    game_id: int
    goal_id: int
    game_title_snapshot: str
    goal_title_snapshot: str
    started_at: datetime
    finished_at: datetime | None
    actual_duration_minutes: int | None
    enjoyment_rating: int | None
    progress: str | None
    notes: str | None
    situation_snapshot: RecommendationRequest
    recommendation_snapshot: RecommendationSnapshot

    @model_validator(mode="after")
    def consistent_session(self):
        snapshot = self.recommendation_snapshot
        candidate = snapshot.selected.candidate
        if (self.game_id, self.goal_id, self.game_title_snapshot, self.goal_title_snapshot) != (
                candidate.game_id, candidate.goal_id, candidate.game_title, candidate.goal_title):
            raise ValueError("Session identity/titles must match its saved selected candidate")
        if self.situation_snapshot != snapshot.evaluation.context or self.started_at != snapshot.evaluation.evaluated_at:
            raise ValueError("Session context/time must match saved evaluation")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("Finish cannot precede start")
        return self
