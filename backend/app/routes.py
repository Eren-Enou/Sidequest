"""Library and read-only recommendation API; no session lifecycle routes."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Game, Goal, utcnow
from app.database import serialize_postgresql_write
from app.schemas import GameCreate, GamePatch, GameRead, GoalCreate, GoalPatch, GoalRead, GoalStatus, SQLITE_INTEGER_MAX
from app.recommendations import evaluate
from app.recommendation_schemas import RecommendationRequest, RecommendationResponse, response_from_result

router = APIRouter(prefix="/api")


def get_db(request: Request):
    with request.app.state.sessions() as db:
        if request.method != "GET" and request.url.path != "/api/recommendations":
            serialize_postgresql_write(db)
        yield db


DB = Annotated[Session, Depends(get_db)]
RecordID = Annotated[int, Path(gt=0, le=SQLITE_INTEGER_MAX)]


def get_evaluation_time() -> datetime:
    """One backend clock reading per request; tests may override this dependency."""
    return utcnow()


@router.post("/recommendations", response_model=RecommendationResponse)
def recommendation(body: RecommendationRequest, db: DB,
                   evaluated_at: Annotated[datetime, Depends(get_evaluation_time)]):
    result = evaluate(db, body, evaluated_at=evaluated_at)
    return response_from_result(result, body)


def game_or_404(db, game_id):
    game = db.get(Game, game_id)
    if game is None:
        raise HTTPException(404, "Game not found")
    return game


def goal_or_404(db, goal_id):
    goal = db.get(Goal, goal_id)
    if goal is None:
        raise HTTPException(404, "Goal not found")
    return goal


def save(db, record):
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/games", response_model=GameRead, status_code=201)
def create_game(body: GameCreate, db: DB):
    now = utcnow()
    return save(db, Game(**body.model_dump(), created_at=now, updated_at=now))


@router.get("/games", response_model=list[GameRead])
def list_games(db: DB, include_archived: bool = False):
    query = select(Game).order_by(Game.id)
    if not include_archived:
        query = query.where(Game.archived_at.is_(None))
    return db.scalars(query).all()


@router.get("/games/{game_id}", response_model=GameRead)
def get_game(game_id: RecordID, db: DB):
    return game_or_404(db, game_id)


@router.patch("/games/{game_id}", response_model=GameRead)
def edit_game(game_id: RecordID, body: GamePatch, db: DB):
    game = game_or_404(db, game_id)
    changes = body.model_dump(exclude_unset=True)
    if changes:
        for name, value in changes.items():
            setattr(game, name, value)
        game.updated_at = utcnow()
        return save(db, game)
    return game


@router.delete("/games/{game_id}", status_code=204)
def archive_game(game_id: RecordID, db: DB):
    game = game_or_404(db, game_id)
    if game.archived_at is None:
        game.archived_at = game.updated_at = utcnow()
        save(db, game)
    return Response(status_code=204)


@router.post("/games/{game_id}/restore", response_model=GameRead)
def restore_game(game_id: RecordID, db: DB):
    game = game_or_404(db, game_id)
    if game.archived_at is not None:
        game.archived_at = None
        game.updated_at = utcnow()
        return save(db, game)
    return game


@router.post("/goals", response_model=GoalRead, status_code=201)
def create_goal(body: GoalCreate, db: DB):
    game = game_or_404(db, body.game_id)
    if game.archived_at is not None:
        raise HTTPException(409, "Restore the game before adding a goal")
    now = utcnow()
    return save(db, Goal(**body.model_dump(), created_at=now, updated_at=now))


@router.get("/goals", response_model=list[GoalRead])
def list_goals(db: DB, game_id: Annotated[int | None, Query(gt=0, le=SQLITE_INTEGER_MAX)] = None,
               status: GoalStatus | None = None, include_archived: bool = False):
    query = select(Goal).join(Game).order_by(Goal.id)
    if game_id is not None:
        game_or_404(db, game_id)
        query = query.where(Goal.game_id == game_id)
    if status is not None:
        query = query.where(Goal.status == status)
    if not include_archived:
        query = query.where(Goal.status != "archived", Game.archived_at.is_(None))
    return db.scalars(query).all()


@router.get("/goals/{goal_id}", response_model=GoalRead)
def get_goal(goal_id: RecordID, db: DB):
    return goal_or_404(db, goal_id)


@router.patch("/goals/{goal_id}", response_model=GoalRead)
def edit_goal(goal_id: RecordID, body: GoalPatch, db: DB):
    goal = goal_or_404(db, goal_id)
    changes = body.model_dump(exclude_unset=True)
    if changes:
        for name, value in changes.items():
            setattr(goal, name, value)
        goal.updated_at = utcnow()
        return save(db, goal)
    return goal


@router.delete("/goals/{goal_id}", status_code=204)
def archive_goal(goal_id: RecordID, db: DB):
    goal = goal_or_404(db, goal_id)
    if goal.status != "archived":
        goal.status = "archived"
        goal.updated_at = utcnow()
        save(db, goal)
    return Response(status_code=204)


@router.post("/goals/{goal_id}/complete", response_model=GoalRead)
def complete_goal(goal_id: RecordID, db: DB):
    goal = goal_or_404(db, goal_id)
    if goal.status == "archived" or game_or_404(db, goal.game_id).archived_at is not None:
        raise HTTPException(409, "Restore the game and goal before completing it")
    if goal.status != "completed":
        goal.status = "completed"
        goal.completed_at = goal.updated_at = utcnow()
        return save(db, goal)
    return goal


@router.post("/goals/{goal_id}/restore", response_model=GoalRead)
def restore_goal(goal_id: RecordID, db: DB):
    goal = goal_or_404(db, goal_id)
    if game_or_404(db, goal.game_id).archived_at is not None:
        raise HTTPException(409, "Restore the game before restoring the goal")
    if goal.status != "active":
        goal.status = "active"
        goal.completed_at = None
        goal.updated_at = utcnow()
        return save(db, goal)
    return goal
