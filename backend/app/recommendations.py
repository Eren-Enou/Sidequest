"""One read query maps persisted library/history into pure scorer inputs."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import scoring
from app.models import Game, Goal, PlaySession
from app.recommendation_schemas import RecommendationRequest


def load_candidates(db: Session) -> tuple[scoring.Candidate, ...]:
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
    return tuple(scoring.Candidate(
        game_id=game.id, goal_id=goal.id, game_title=game.title, goal_title=goal.title,
        estimated_minutes=goal.estimated_minutes, energy_required=game.energy_required,
        social_mode=game.social_mode, experience_tags=tuple(game.experience_tags),
        interest=game.current_interest, goal_priority=goal.priority, friction=game.friction,
        last_completed_session_at=last_completed, game_archived=game.archived_at is not None,
        goal_status=goal.status)
        for game, goal, last_completed in db.execute(query))


def evaluate(db: Session, context: RecommendationRequest, *, evaluated_at: datetime) -> scoring.RecommendationResult:
    return scoring.recommend(load_candidates(db), scoring.SessionContext(**context.model_dump()),
                             evaluated_at=evaluated_at)
