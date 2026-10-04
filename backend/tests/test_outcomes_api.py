"""Read-only descriptive evidence on migrated temporary SQLite databases."""
from datetime import timedelta, timezone
import hashlib
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import PlaySession
from app.outcomes import summarize_game
from app.routes import get_evaluation_time
from app.session_routes import get_operation_time
from test_library_api import library, seed, session_row, NOW
from test_recommendation_api import add, ask, CONTEXT


def completed(engine, game, goal, ratings, **fields):
    with Session(engine) as db:
        rows = [session_row(game, goal, finished_at=NOW + timedelta(minutes=30),
                            actual_duration_minutes=30, enjoyment_rating=rating,
                            progress="No measurable progress; relaxed", **fields) for rating in ratings]
        db.add_all(rows)
        db.commit()
        return [row.id for row in rows]


def outcomes(client, game):
    response = client.get(f'/api/games/{game["id"]}/outcomes')
    assert response.status_code == 200, response.text
    return response.json()


def test_empty_and_typed_contract(library):
    client, _, _ = library
    game, _ = seed(client)
    assert outcomes(client, game) == {
        "game_id": game["id"], "completed_session_count": 0, "average_enjoyment": None,
        "rating_distribution": [{"rating": r, "count": 0} for r in range(1, 6)],
        "recent_sessions": [], "by_desired_experience": [], "by_energy": [],
    }
    operation = client.get("/openapi.json").json()["paths"][f'/api/games/{{game_id}}/outcomes']
    assert set(operation) == {"get"}
    assert operation["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("GameOutcomes")


@pytest.mark.parametrize("rating", range(1, 6))
def test_single_rating_including_historical_three(library, rating):
    client, engine, _ = library
    game, goal = seed(client)
    ids = completed(engine, game, goal, [rating])
    result = outcomes(client, game)
    assert result["completed_session_count"] == 1
    assert result["average_enjoyment"] == rating
    assert result["rating_distribution"] == [{"rating": r, "count": int(r == rating)} for r in range(1, 6)]
    assert result["recent_sessions"][0] == dict(session_id=ids[0], goal_title_snapshot=goal["title"],
        finished_at="2026-10-03T19:30:00Z", enjoyment_rating=rating, desired_experience="chill", energy="low")


def test_all_time_distribution_not_just_recent_and_equal_timestamp_order(library):
    client, engine, _ = library
    game, goal = seed(client)
    ids = completed(engine, game, goal, [1, 2, 3, 4, 5, 5, 5])
    result = outcomes(client, game)
    assert result["completed_session_count"] == 7
    assert result["average_enjoyment"] == 3.57
    assert [r["count"] for r in result["rating_distribution"]] == [1, 1, 1, 1, 3]
    assert [r["session_id"] for r in result["recent_sessions"]] == ids[::-1][:5]
    assert outcomes(client, game) == result


def test_active_excluded_and_other_games_and_goals_do_not_mix(library):
    client, engine, _ = library
    game, goal = seed(client)
    other, other_goal = add(client, {"title": "Other game"})
    second = client.post("/api/goals", json={"game_id": game["id"], "title": "Second quest", "estimated_minutes": 30}).json()
    completed(engine, game, goal, [1])
    completed(engine, game, second, [5])
    completed(engine, other, other_goal, [2, 2, 2])
    with Session(engine) as db:
        db.add(session_row(game, goal))
        db.commit()
    result = outcomes(client, game)
    assert result["completed_session_count"] == 2
    assert result["average_enjoyment"] == 3
    assert {r["goal_title_snapshot"] for r in result["recent_sessions"]} == {goal["title"], second["title"]}
    assert outcomes(client, other)["average_enjoyment"] == 2


def test_context_counts_and_distribution_use_snapshots(library):
    client, engine, _ = library
    game, goal = seed(client)
    completed(engine, game, goal, [1, 3])
    completed(engine, game, goal, [5], situation_snapshot={"desired_experience": "challenge", "energy": "high"})
    client.patch(f'/api/games/{game["id"]}', json={"experience_tags": ["novelty"], "energy_required": "medium", "title": "Changed"})
    client.patch(f'/api/goals/{goal["id"]}', json={"title": "Changed goal"})
    result = outcomes(client, game)
    assert [(r["desired_experience"], r["completed_session_count"], r["average_enjoyment"])
            for r in result["by_desired_experience"]] == [("chill", 2, 2), ("challenge", 1, 5)]
    assert [(r["energy"], r["completed_session_count"], r["average_enjoyment"])
            for r in result["by_energy"]] == [("low", 2, 2), ("high", 1, 5)]
    assert [r["count"] for r in result["by_desired_experience"][0]["rating_distribution"]] == [1, 0, 1, 0, 0]
    assert all(r["goal_title_snapshot"] == goal["title"] for r in result["recent_sessions"])


@pytest.mark.parametrize("snapshot", [{}, {"energy": 2, "desired_experience": "relaxing"}])
def test_missing_or_malformed_context_is_explicitly_unknown_not_dropped(library, snapshot):
    client, engine, _ = library
    game, goal = seed(client)
    completed(engine, game, goal, [3], situation_snapshot=snapshot)
    result = outcomes(client, game)
    assert result["completed_session_count"] == 1
    assert result["by_desired_experience"][0]["desired_experience"] is None
    assert result["by_energy"][0]["energy"] is None
    assert result["by_energy"][0]["completed_session_count"] == 1
    assert result["recent_sessions"][0]["energy"] is None


@pytest.mark.parametrize("snapshot", [None, [], "invalid"])
def test_nonobject_context_is_rejected_by_existing_database_constraints(library, snapshot):
    client, engine, _ = library
    game, goal = seed(client)
    with pytest.raises(IntegrityError):
        completed(engine, game, goal, [3], situation_snapshot=snapshot)
    assert outcomes(client, game)["completed_session_count"] == 0


def test_each_context_dimension_validated_independently(library):
    client, engine, _ = library
    game, goal = seed(client)
    completed(engine, game, goal, [4], situation_snapshot={"energy": "medium"})
    result = outcomes(client, game)
    assert result["by_energy"][0]["energy"] == "medium"
    assert result["by_desired_experience"][0]["desired_experience"] is None


def test_archive_and_goal_completion_preserve_evidence(library):
    client, engine, _ = library
    game, goal = seed(client)
    completed(engine, game, goal, [3, 5])
    before = outcomes(client, game)
    client.post(f'/api/goals/{goal["id"]}/complete')
    assert outcomes(client, game) == before
    client.delete(f'/api/goals/{goal["id"]}')
    client.delete(f'/api/games/{game["id"]}')
    assert outcomes(client, game) == before
    client.post(f'/api/games/{game["id"]}/restore')
    assert outcomes(client, game) == before


@pytest.mark.parametrize("game_id,status", [(999, 404), (0, 422), (-1, 422), (2**63, 422), ("abc", 422)])
def test_missing_or_invalid_game(library, game_id, status):
    client, _, _ = library
    assert client.get(f"/api/games/{game_id}/outcomes").status_code == status


def test_finish_time_not_insert_order_and_utc_normalization(library):
    client, engine, _ = library
    game, goal = seed(client)
    later = completed(engine, game, goal, [5], started_at=NOW)[0]
    with Session(engine) as db:
        row = db.get(PlaySession, later)
        row.finished_at = NOW + timedelta(hours=2)
        db.commit()
    completed(engine, game, goal, [1], started_at=NOW.astimezone(timezone(timedelta(hours=-7))))
    result = outcomes(client, game)
    assert result["recent_sessions"][0]["session_id"] == later
    assert result["recent_sessions"][0]["finished_at"] == "2026-10-03T21:00:00Z"


def test_get_is_read_only_two_queries_and_never_scores(library, monkeypatch):
    client, engine, path = library
    game, goal = seed(client)
    completed(engine, game, goal, [3, 4])
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    def forbidden(*args, **kwargs):
        pytest.fail("Insights must never call recommendation scoring")
    monkeypatch.setattr("app.scoring.recommend", forbidden)
    statements = []
    def track(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(engine, "before_cursor_execute", track)
    try:
        outcomes(client, game)
    finally:
        event.remove(engine, "before_cursor_execute", track)
    assert len([s for s in statements if s.lstrip().startswith("SELECT")]) == 2
    assert all(s.lstrip().startswith("SELECT") or s == "BEGIN" for s in statements)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_recommendation_unchanged_after_insights_and_rating_only_changes(library):
    client, engine, _ = library
    game, goal = seed(client)
    completed(engine, game, goal, [1])
    before = ask(library)
    outcomes(client, game)
    assert ask(library) == before
    with Session(engine) as db:
        row = db.scalar(select(PlaySession))
        row.enjoyment_rating = 5
        db.commit()
    assert outcomes(client, game)["average_enjoyment"] == 5
    assert ask(library) == before


def test_real_session_finish_becomes_evidence_without_rewriting_snapshots(library, monkeypatch):
    client, _, _ = library
    monkeypatch.setattr("app.routes.utcnow", lambda: NOW - timedelta(days=1))
    client.app.dependency_overrides[get_operation_time] = lambda: NOW
    client.app.dependency_overrides[get_evaluation_time] = lambda: NOW
    game, goal = seed(client)
    response = client.post("/api/sessions/start", json={"game_id": game["id"], "goal_id": goal["id"], "situation": CONTEXT})
    assert response.status_code == 201, response.text
    active = response.json()
    assert outcomes(client, game)["completed_session_count"] == 0
    client.app.dependency_overrides[get_operation_time] = lambda: NOW + timedelta(minutes=30)
    response = client.post(f'/api/sessions/{active["id"]}/finish', json={
        "actual_duration_minutes": 30, "enjoyment_rating": 3, "progress": "Relaxed without measurable progress"})
    assert response.status_code == 200, response.text
    result = outcomes(client, game)
    assert result["completed_session_count"] == 1
    assert result["average_enjoyment"] == 3
    assert result["by_desired_experience"][0]["desired_experience"] == "progression"
    assert client.get("/api/sessions").json() == [response.json()]
    assert response.json()["recommendation_snapshot"] == active["recommendation_snapshot"]


@pytest.mark.parametrize("rating", [None, 0, 6, True, "3"])
def test_invalid_completed_rating_refuses_fabricated_summary(rating):
    row = SimpleNamespace(enjoyment_rating=rating)
    db = SimpleNamespace(execute=lambda query: SimpleNamespace(all=lambda: [row]))
    with pytest.raises(HTTPException) as error:
        summarize_game(db, 1)
    assert error.value.status_code == 409
    assert error.value.detail == "Completed session has invalid enjoyment data; insights unavailable"
