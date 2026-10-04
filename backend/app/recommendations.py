"""One read query maps persisted library/history into pure scorer inputs."""

from datetime import datetime
from dataclasses import replace

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import scoring
from app.models import Game, Goal, PlaySession
from app.recommendation_schemas import RecommendationRequest


def _load_pairs(db: Session) -> tuple[tuple[scoring.Candidate, str], ...]:
    completed = (select(PlaySession.game_id,
                        func.max(PlaySession.finished_at).label("last_completed_session_at"))
                 .where(PlaySession.finished_at.is_not(None))
                 .group_by(PlaySession.game_id).subquery())
    query = (select(Game, Goal, completed.c.last_completed_session_at)
             .join(Goal, Goal.game_id == Game.id)
             .outerjoin(completed, completed.c.game_id == Game.id)
             .order_by(Goal.id))
    # Include inactive pairs so the frozen scorer can explain lifecycle exclusions.
    # Games without any goals have no candidate; no synthetic goal is invented.
    return tuple((scoring.Candidate(
        game_id=game.id, goal_id=goal.id, game_title=game.title, goal_title=goal.title,
        estimated_minutes=goal.estimated_minutes, energy_required=game.energy_required,
        social_mode=game.social_mode, experience_tags=tuple(game.experience_tags),
        interest=game.current_interest, goal_priority=goal.priority, friction=game.friction,
        last_completed_session_at=last_completed, game_archived=game.archived_at is not None,
        goal_status=goal.status), goal.readiness)
        for game, goal, last_completed in db.execute(query))


def _is_later(candidate, readiness):
    # Lifecycle exclusions remain owned by the frozen scorer.
    return candidate.goal_status == "active" and not candidate.game_archived and readiness == "later"


def load_candidates(db: Session) -> tuple[scoring.Candidate, ...]:
    """Only current active pairs proceed to scoring; inactive pairs remain auditable."""
    return tuple(c for c, readiness in _load_pairs(db) if not _is_later(c, readiness))


def evaluate(db: Session, context: RecommendationRequest, *, evaluated_at: datetime) -> scoring.RecommendationResult:
    pairs = _load_pairs(db)
    withheld = tuple(scoring.ExcludedCandidate(c, (
        "Goal is planned for later and is not currently considered; make it current to recommend it.",))
        for c, readiness in pairs if _is_later(c, readiness))
    result = scoring.recommend((c for c, readiness in pairs if not _is_later(c, readiness)),
                               scoring.SessionContext(**context.model_dump()), evaluated_at=evaluated_at)
    # No scores, thresholds, ranking or outcomes are changed here.
    return replace(result, excluded=tuple(sorted((*result.excluded, *withheld),
                   key=lambda item: (item.candidate.goal_id, item.candidate.game_id))))
