"""JSON contract for the frozen scorer; response fields carry its decisions verbatim."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.schemas import Energy, Experience, GoalStatus, SocialMode
from app.scoring import RecommendationResult, ScoredCandidate


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    available_minutes: Annotated[int, Field(strict=True, gt=0)]
    energy: Energy
    social_preference: Literal["solo", "social", "either"]
    desired_experience: Experience


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CandidateRead(ReadModel):
    game_id: int
    goal_id: int
    game_title: str
    goal_title: str
    estimated_minutes: int
    energy_required: Energy
    social_mode: SocialMode
    experience_tags: list[Experience]
    interest: int
    goal_priority: int
    friction: int
    last_completed_session_at: datetime | None
    game_archived: bool
    goal_status: GoalStatus


class FactorRead(ReadModel):
    name: str
    points: float
    weight: int
    inputs: dict[str, Any]
    reason: str


class ScoredCandidateRead(ReadModel):
    candidate: CandidateRead
    score: float
    suitability: float
    suitable: bool
    unsuitable_reasons: list[str]
    breakdown: dict[str, float]
    factors: list[FactorRead]


class ExcludedCandidateRead(ReadModel):
    candidate: CandidateRead
    reasons: list[str]


class RecommendationResponse(ReadModel):
    status: Literal["no_eligible", "no_good_fit", "clear_recommendation", "multiple_equivalent"]
    engine_version: str
    evaluated_at: datetime
    context: RecommendationRequest
    weights: dict[str, int]
    minimum_suitability: int
    near_tie_margin: int
    winner: ScoredCandidateRead | None
    recommendations: list[ScoredCandidateRead]
    ranked: list[ScoredCandidateRead]
    excluded: list[ExcludedCandidateRead]


class ReadinessRecommendationResponse(RecommendationResponse):
    """Current API contract; old snapshots keep RecommendationResponse unchanged."""
    eligibility_version: Literal["goal-readiness-020"]


JSON_INPUTS = TypeAdapter(dict[str, Any])


def scored_response(item: ScoredCandidate) -> ScoredCandidateRead:
    return ScoredCandidateRead(
        candidate=CandidateRead.model_validate(item.candidate), score=item.score,
        suitability=item.suitability, suitable=item.suitable,
        unsuitable_reasons=list(item.unsuitable_reasons), breakdown=item.breakdown,
        factors=[FactorRead(name=f.name, points=f.points, weight=f.weight,
                            inputs=JSON_INPUTS.dump_python(dict(f.inputs), mode="json"), reason=f.reason)
                 for f in item.factors])


def response_from_result(result: RecommendationResult, context: RecommendationRequest) -> ReadinessRecommendationResponse:
    # Projection only: no ranking, acceptance, status inference, or arithmetic here.
    ranked = [scored_response(item) for item in result.ranked]
    by_goal = {item.candidate.goal_id: item for item in ranked}
    return ReadinessRecommendationResponse(
        eligibility_version="goal-readiness-020",
        status=result.status, engine_version=result.engine_version, evaluated_at=result.evaluated_at,
        context=context, weights=vars(result.weights), minimum_suitability=result.minimum_suitability,
        near_tie_margin=result.near_tie_margin,
        winner=by_goal[result.winner.candidate.goal_id] if result.winner else None,
        recommendations=[by_goal[item.candidate.goal_id] for item in result.recommendations],
        ranked=ranked, excluded=[ExcludedCandidateRead.model_validate(item) for item in result.excluded])
