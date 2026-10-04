"""Transactional session lifecycle; historical evidence never reads live titles."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlaySession, utcnow
from app.database import serialize_postgresql_write
from app.recommendations import evaluate
from app.recommendation_schemas import response_from_result
from app.routes import DB, RecordID, game_or_404, goal_or_404
from app.session_schemas import ReadinessRecommendationSnapshot, SessionFinish, SessionRead, SessionStart

router = APIRouter(prefix="/api/sessions")


def get_operation_time() -> datetime:
    return utcnow()


Clock = Annotated[datetime, Depends(get_operation_time)]


def operation_time(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(409, "Backend operation timestamp must be timezone aware")
    return value.astimezone(timezone.utc)


def get_write_db(request: Request):
    # Set the flag before Session's first SQL statement begins the transaction.
    # SQLite serializes writers before we read/revalidate current library state.
    with request.app.state.engine.connect() as connection:
        if connection.dialect.name == "sqlite":
            connection.info["begin_immediate"] = True
        try:
            with Session(connection, expire_on_commit=False) as db:
                serialize_postgresql_write(db)
                yield db
        finally:
            connection.info.pop("begin_immediate", None)


WriteDB = Annotated[Session, Depends(get_write_db)]


@router.post("/start", response_model=SessionRead, status_code=201)
def start_session(body: SessionStart, db: WriteDB, timestamp: Clock):
    timestamp = operation_time(timestamp)
    active = db.scalar(select(PlaySession).where(PlaySession.finished_at.is_(None)))
    if active:
        raise HTTPException(409, {"message": "Finish the active session before starting another", "active_session_id": active.id})
    game = game_or_404(db, body.game_id)
    goal = goal_or_404(db, body.goal_id)
    if goal.game_id != game.id:
        raise HTTPException(409, "Selected goal does not belong to the selected game")
    if timestamp < max(game.created_at, game.updated_at, goal.created_at, goal.updated_at):
        raise HTTPException(409, "Start timestamp precedes current library state")
    result = evaluate(db, body.situation, evaluated_at=timestamp)
    response = response_from_result(result, body.situation)
    selected = next((item for item in response.recommendations
                     if (item.candidate.game_id, item.candidate.goal_id) == (game.id, goal.id)), None)
    if selected is None:
        raise HTTPException(409, {"message": "Selected pair is no longer a recommendation choice; request a new recommendation",
                                  "recommendation": response.model_dump(mode="json")})
    snapshot = ReadinessRecommendationSnapshot(snapshot_version=2, selected=selected, evaluation=response)
    row = PlaySession(game_id=game.id, goal_id=goal.id, game_title_snapshot=game.title,
                      goal_title_snapshot=goal.title, started_at=timestamp,
                      situation_snapshot=body.situation.model_dump(mode="json"),
                      recommendation_snapshot=snapshot.model_dump(mode="json"))
    db.add(row)
    db.flush()
    validated = SessionRead.model_validate(row)
    db.commit()
    return validated


@router.get("/active", response_model=SessionRead | None)
def active_session(db: DB):
    return db.scalar(select(PlaySession).where(PlaySession.finished_at.is_(None)))


@router.get("", response_model=list[SessionRead])
def history(db: DB):
    return db.scalars(select(PlaySession).where(PlaySession.finished_at.is_not(None))
                      .order_by(PlaySession.finished_at.desc(), PlaySession.id.desc())).all()


@router.get("/{session_id}", response_model=SessionRead)
def session_detail(session_id: RecordID, db: DB):
    row = db.get(PlaySession, session_id)
    if row is None:
        raise HTTPException(404, "Session not found")
    return row


@router.post("/{session_id}/finish", response_model=SessionRead)
def finish_session(session_id: RecordID, body: SessionFinish, db: WriteDB, timestamp: Clock):
    timestamp = operation_time(timestamp)
    row = db.get(PlaySession, session_id)
    if row is None:
        raise HTTPException(404, "Session not found")
    if row.finished_at is not None:
        raise HTTPException(409, "Session is already finished; history cannot be overwritten")
    if timestamp < row.started_at:
        raise HTTPException(409, "Finish timestamp cannot precede session start")
    if body.mark_goal_completed:
        goal = goal_or_404(db, row.goal_id)
        game = game_or_404(db, row.game_id)
        if game.archived_at is not None or goal.status == "archived":
            raise HTTPException(409, "Restore the game and goal before completing the goal; session remains active")
        if timestamp < max(goal.created_at, goal.updated_at):
            raise HTTPException(409, "Finish timestamp precedes current goal state")
        if goal.status != "completed":
            goal.status = "completed"
            goal.completed_at = goal.updated_at = timestamp
    row.finished_at = timestamp
    row.actual_duration_minutes = body.actual_duration_minutes
    row.enjoyment_rating = body.enjoyment_rating
    row.progress = body.progress
    row.notes = body.notes
    db.flush()
    validated = SessionRead.model_validate(row)
    db.commit()
    return validated
