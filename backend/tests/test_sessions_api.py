"""Isolated lifecycle tests, including real concurrent SQLite writers."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta, timezone
from threading import Barrier

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.main import create_app
from app.models import PlaySession
from app.routes import get_evaluation_time
from app.session_routes import get_operation_time
from app.session_schemas import RecommendationSnapshot
from test_library_api import library, seed, NOW, session_row
from test_recommendation_api import CONTEXT, add

FINISH = dict(actual_duration_minutes=30, enjoyment_rating=4, progress="Harvested crops")


@pytest.fixture
def lifecycle(library, monkeypatch):
    client, engine, path = library
    monkeypatch.setattr("app.routes.utcnow", lambda: NOW-timedelta(days=1))
    client.app.dependency_overrides[get_operation_time] = lambda: NOW
    client.app.dependency_overrides[get_evaluation_time] = lambda: NOW
    return client, engine, path


def start(client, game, goal, **context):
    return client.post("/api/sessions/start", json={"game_id": game["id"], "goal_id": goal["id"],
                       "situation": {**CONTEXT, **context}})


def begun(lifecycle):
    client, _, _ = lifecycle
    game, goal = seed(client)
    response = start(client, game, goal)
    assert response.status_code == 201, response.text
    return game, goal, response.json()


def finish(client, row, **changes):
    client.app.dependency_overrides[get_operation_time] = lambda: NOW+timedelta(minutes=30)
    return client.post(f'/api/sessions/{row["id"]}/finish', json={**FINISH, **changes})


def test_full_loop_snapshot_and_recency(lifecycle):
    client, _, _ = lifecycle
    game, goal = seed(client)
    before = client.post("/api/recommendations", json=CONTEXT).json()
    response = start(client, game, goal)
    assert response.status_code == 201, response.text
    row = response.json()
    assert row["started_at"] == "2026-10-03T19:00:00Z"
    assert row["recommendation_snapshot"]["snapshot_version"] == 1
    assert row["recommendation_snapshot"]["evaluation"] == before
    assert row["recommendation_snapshot"]["selected"] == before["winner"]
    assert client.get("/api/sessions/active").json() == row
    assert client.get("/api/sessions").json() == []
    assert client.post("/api/recommendations", json=CONTEXT).json() == before
    completed = finish(client, row).json()
    assert completed["finished_at"] == "2026-10-03T19:30:00Z"
    assert completed["recommendation_snapshot"] == row["recommendation_snapshot"]
    assert client.get("/api/sessions/active").json() is None
    assert client.get("/api/sessions").json() == [completed]
    client.app.dependency_overrides[get_evaluation_time] = lambda: NOW+timedelta(minutes=30)
    after = client.post("/api/recommendations", json=CONTEXT).json()
    assert before["winner"]["breakdown"]["recent_play"] == 0
    assert after["winner"]["breakdown"]["recent_play"] == -3
    assert after["winner"]["score"] == before["winner"]["score"]-3


def test_near_equivalent_nonwinner_start(lifecycle):
    client, _, _ = lifecycle
    _, first = seed(client)
    game, second = add(client, {"title": "Cloud Harbor"})
    result = client.post("/api/recommendations", json=CONTEXT).json()
    assert result["status"] == "multiple_equivalent"
    assert result["winner"]["candidate"]["goal_id"] == first["id"]
    row = start(client, game, second).json()
    snapshot = row["recommendation_snapshot"]
    assert snapshot["selected"]["candidate"]["goal_id"] == second["id"]
    assert snapshot["evaluation"] == result


@pytest.mark.parametrize("case", ["time", "social", "unsuitable", "game_archive", "goal_archive", "goal_completed", "outside_band"])
def test_unrecommendable_selected_pair(lifecycle, case):
    client, _, _ = lifecycle
    game, goal = seed(client)
    context = {}
    if case == "time": context["available_minutes"] = 29
    if case == "social": context["social_preference"] = "social"
    if case == "unsuitable": client.patch(f'/api/games/{game["id"]}', json={"energy_required": "high", "experience_tags": ["challenge"]})
    if case == "game_archive": client.delete(f'/api/games/{game["id"]}')
    if case == "goal_archive": client.delete(f'/api/goals/{goal["id"]}')
    if case == "goal_completed": client.post(f'/api/goals/{goal["id"]}/complete')
    if case == "outside_band": add(client, {"current_interest": 5}, {"priority": 3})
    response = start(client, game, goal, **context)
    assert response.status_code == 409
    assert "recommendation" in response.json()["detail"]
    assert client.get("/api/sessions/active").json() is None


def test_stale_recommendation_revalidated(lifecycle):
    client, _, _ = lifecycle
    game, goal = seed(client)
    assert client.post("/api/recommendations", json=CONTEXT).json()["winner"]
    client.patch(f'/api/goals/{goal["id"]}', json={"estimated_minutes": 60})
    assert start(client, game, goal).status_code == 409


@pytest.mark.parametrize("case,expected", [("missing_game",404),("missing_goal",404),("mismatch",409)])
def test_start_references(lifecycle, case, expected):
    client, _, _ = lifecycle
    game, goal = seed(client)
    if case == "missing_game": game = {"id": 999}
    if case == "missing_goal": goal = {"id": 999}
    if case == "mismatch": game, _ = add(client, {"title": "Other"})
    assert start(client, game, goal).status_code == expected


def test_second_active_conflict(lifecycle):
    client, _, _ = lifecycle
    game, goal, row = begun(lifecycle)
    response = start(client, game, goal)
    assert response.status_code == 409
    assert response.json()["detail"]["active_session_id"] == row["id"]


def test_concurrent_start(lifecycle):
    client, engine, _ = lifecycle
    game, goal = seed(client)
    barrier = Barrier(2)
    def attempt():
        # Separate client/connection for each writer, using the same file/app.
        with TestClient(client.app) as concurrent:
            barrier.wait(timeout=10)
            return start(concurrent, game, goal).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: attempt(), range(2)))
    assert sorted(statuses) == [201,409]
    with Session(engine) as db:
        assert len(db.scalars(select(PlaySession)).all()) == 1


def test_reopen_active_and_completed(lifecycle):
    client, _, path = lifecycle
    _, _, row = begun(lifecycle)
    fresh_app = create_app(path)
    fresh_app.dependency_overrides[get_operation_time] = lambda: NOW+timedelta(minutes=30)
    with TestClient(fresh_app) as fresh:
        assert fresh.get("/api/sessions/active").json() == row
        done = fresh.post(f'/api/sessions/{row["id"]}/finish', json=FINISH).json()
    with TestClient(create_app(path)) as fresh:
        assert fresh.get("/api/sessions/active").json() is None
        assert fresh.get("/api/sessions").json() == [done]
        assert fresh.get(f'/api/sessions/{row["id"]}').json() == done


@pytest.mark.parametrize("changes", [
    {"actual_duration_minutes":0}, {"actual_duration_minutes":-1}, {"actual_duration_minutes":True},
    {"actual_duration_minutes":1.5}, {"actual_duration_minutes":"30"}, {"actual_duration_minutes":2**63},
    {"enjoyment_rating":0}, {"enjoyment_rating":6}, {"enjoyment_rating":True}, {"enjoyment_rating":"4"},
    {"progress":" "}, {"progress":None}, {"progress":42}, {"notes":42},
    {"mark_goal_completed":"true"}, {"unknown":1},
])
def test_finish_validation(lifecycle, changes):
    client, _, _ = lifecycle
    _, _, row = begun(lifecycle)
    assert finish(client, row, **changes).status_code == 422
    assert client.get("/api/sessions/active").json() == row


@pytest.mark.parametrize("missing", list(FINISH))
def test_required_finish_fields(lifecycle, missing):
    client, _, _ = lifecycle
    _, _, row = begun(lifecycle)
    assert client.post(f'/api/sessions/{row["id"]}/finish', json={k:v for k,v in FINISH.items() if k != missing}).status_code == 422


@pytest.mark.parametrize("notes", [None, "", "Remember seeds"])
def test_notes_and_progress(lifecycle, notes):
    client, _, _ = lifecycle
    _, _, row = begun(lifecycle)
    done = finish(client, row, notes=notes, progress="  Built shed  ").json()
    assert done["notes"] == notes and done["progress"] == "Built shed"


def test_optional_completion_and_duplicate_finish(lifecycle):
    client, _, _ = lifecycle
    _, goal, row = begun(lifecycle)
    done = finish(client, row, mark_goal_completed=True).json()
    updated = client.get(f'/api/goals/{goal["id"]}').json()
    assert updated["status"] == "completed" and updated["completed_at"] == done["finished_at"]
    assert finish(client, row, progress="Overwrite").status_code == 409
    assert client.get(f'/api/sessions/{row["id"]}').json() == done


def test_finish_without_completion(lifecycle):
    client, _, _ = lifecycle
    _, goal, row = begun(lifecycle)
    assert finish(client, row).status_code == 200
    assert client.get(f'/api/goals/{goal["id"]}').json()["status"] == "active"


def test_finish_and_goal_completion_rollback_on_database_failure(lifecycle):
    client, engine, _ = lifecycle
    _, goal, row = begun(lifecycle)
    def fail_finish(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE play_sessions"):
            raise IntegrityError(statement, parameters, Exception("injected write failure"))
    event.listen(engine, "before_cursor_execute", fail_finish)
    try:
        assert finish(client, row, mark_goal_completed=True).status_code == 409
    finally:
        event.remove(engine, "before_cursor_execute", fail_finish)
    assert client.get("/api/sessions/active").json() == row
    assert client.get(f'/api/goals/{goal["id"]}').json()["status"] == "active"


@pytest.mark.parametrize("archived", ["game", "goal"])
def test_archived_goal_completion_conflict_but_plain_finish_allowed(lifecycle, archived):
    client, _, _ = lifecycle
    game, goal, row = begun(lifecycle)
    client.delete(f'/api/{"games" if archived == "game" else "goals"}/{game["id"] if archived == "game" else goal["id"]}')
    assert finish(client, row, mark_goal_completed=True).status_code == 409
    assert client.get("/api/sessions/active").json() == row
    assert finish(client, row).status_code == 200


def test_history_order_and_immutable_evidence(lifecycle):
    client, _, _ = lifecycle
    game, goal, row = begun(lifecycle)
    first = finish(client, row).json()
    # Same finish time deliberately exercises ID-descending tie break.
    client.app.dependency_overrides[get_operation_time] = lambda: NOW+timedelta(minutes=30)
    second_start = start(client, game, goal).json()
    second = finish(client, second_start).json()
    assert [r["id"] for r in client.get("/api/sessions").json()] == [second["id"], first["id"]]
    client.patch(f'/api/games/{game["id"]}', json={"title":"Renamed", "current_interest":1, "friction":5, "experience_tags":["novelty"]})
    client.patch(f'/api/goals/{goal["id"]}', json={"title":"Different", "priority":3, "estimated_minutes":90})
    client.delete(f'/api/games/{game["id"]}')
    client.delete(f'/api/goals/{goal["id"]}')
    assert client.get(f'/api/sessions/{first["id"]}').json() == first
    assert first["recommendation_snapshot"]["evaluation"]["engine_version"] == "v0.1-final-004"


@pytest.mark.parametrize("corruption", ["version", "missing_version", "selected", "score", "factor", "context", "timestamp"])
def test_snapshot_validation(lifecycle, corruption):
    _, _, row = begun(lifecycle)
    snapshot = deepcopy(row["recommendation_snapshot"])
    if corruption == "version": snapshot["snapshot_version"] = 999
    if corruption == "missing_version": del snapshot["snapshot_version"]
    if corruption == "selected": snapshot["selected"]["candidate"]["goal_id"] = 999
    if corruption == "score": snapshot["evaluation"]["ranked"][0]["score"] += 1
    if corruption == "factor": snapshot["evaluation"]["ranked"][0]["factors"][0]["points"] += 1
    if corruption == "context": del snapshot["evaluation"]["context"]["energy"]
    if corruption == "timestamp": snapshot["evaluation"]["evaluated_at"] = "2026-10-03T19:00:00"
    with pytest.raises(ValidationError): RecommendationSnapshot.model_validate(snapshot)


@pytest.mark.parametrize("operation", ["start", "finish"])
def test_impossible_time_rejected(lifecycle, operation):
    client, _, _ = lifecycle
    game, goal = seed(client)
    row = start(client, game, goal).json() if operation == "finish" else None
    client.app.dependency_overrides[get_operation_time] = lambda: NOW-timedelta(days=2)
    response = (start(client, game, goal) if row is None else
                client.post(f'/api/sessions/{row["id"]}/finish', json=FINISH))
    assert response.status_code == 409


def test_offset_time_and_one_capture(lifecycle):
    client, _, _ = lifecycle
    game, goal = seed(client)
    calls = []
    def clock():
        calls.append(1)
        return NOW.astimezone(timezone(timedelta(hours=-7)))
    client.app.dependency_overrides[get_operation_time] = clock
    row = start(client, game, goal).json()
    assert calls == [1]
    assert row["started_at"] == row["recommendation_snapshot"]["evaluation"]["evaluated_at"] == "2026-10-03T19:00:00Z"
    assert client.post(f'/api/sessions/{row["id"]}/finish', json=FINISH).status_code == 200
    assert calls == [1,1]


def test_missing_sessions_and_empty_active(lifecycle):
    client, _, _ = lifecycle
    assert client.get("/api/sessions/active").json() is None
    assert client.get("/api/sessions/999").status_code == 404
    assert client.post("/api/sessions/999/finish", json=FINISH).status_code == 404


def test_composite_foreign_key_still_enforced(lifecycle):
    client, engine, _ = lifecycle
    game, goal = seed(client)
    other, _ = add(client, {"title":"Other"})
    with Session(engine) as db:
        db.add(session_row(other, goal))
        with pytest.raises(IntegrityError): db.commit()


@pytest.mark.parametrize("change", [{"game_id":0}, {"goal_id":True}, {"goal_id":"1"},
    {"situation":{}}, {"recommendation_snapshot":{}}, {"started_at":"2026-10-03T19:00:00Z"}])
def test_start_validation(lifecycle, change):
    client, _, _ = lifecycle
    game, goal = seed(client)
    body = {"game_id":game["id"], "goal_id":goal["id"], "situation":CONTEXT}
    assert client.post("/api/sessions/start", json={**body, **change}).status_code == 422
    assert client.get("/api/sessions/active").json() is None


def test_concurrent_finish_preserves_first_history(lifecycle):
    client, _, _ = lifecycle
    _, _, row = begun(lifecycle)
    client.app.dependency_overrides[get_operation_time] = lambda: NOW+timedelta(minutes=30)
    barrier = Barrier(2)
    def attempt(progress):
        with TestClient(client.app) as concurrent:
            barrier.wait(timeout=10)
            return concurrent.post(f'/api/sessions/{row["id"]}/finish', json={**FINISH, "progress":progress})
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(attempt, ["First harvest", "Second harvest"]))
    assert sorted(r.status_code for r in responses) == [200,409]
    accepted = next(r.json() for r in responses if r.status_code == 200)
    assert client.get(f'/api/sessions/{row["id"]}').json() == accepted


def test_history_reads_saved_policy_without_recomputing(lifecycle, monkeypatch):
    client, _, _ = lifecycle
    _, _, row = begun(lifecycle)
    done = finish(client, row).json()
    def forbid(*args, **kwargs):
        raise AssertionError("History must not recompute scoring")
    monkeypatch.setattr("app.scoring.recommend", forbid)
    assert client.get(f'/api/sessions/{row["id"]}').json() == done
    assert client.get("/api/sessions").json() == [done]


def test_history_newer_finish_precedes_older(lifecycle):
    client, _, _ = lifecycle
    game, goal, row = begun(lifecycle)
    first = finish(client, row).json()
    client.app.dependency_overrides[get_operation_time] = lambda: NOW+timedelta(hours=1)
    second_start = start(client, game, goal).json()
    client.app.dependency_overrides[get_operation_time] = lambda: NOW+timedelta(hours=2)
    second = client.post(f'/api/sessions/{second_start["id"]}/finish', json=FINISH).json()
    assert client.get("/api/sessions").json() == [second,first]
