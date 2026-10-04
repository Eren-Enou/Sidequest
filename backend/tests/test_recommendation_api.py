"""Recommendation integration uses isolated migrated SQLite files and fixed time."""
from datetime import timedelta
import hashlib
import sqlite3

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app import scoring
from app.main import create_app
from app.recommendations import load_candidates
from app.routes import get_evaluation_time
from test_library_api import library, seed, session_row, NOW, GAME, GOAL

CONTEXT = dict(available_minutes=45, energy="low", social_preference="solo", desired_experience="progression")


def ask(library, **changes):
    client, _, _ = library
    client.app.dependency_overrides[get_evaluation_time] = lambda: NOW
    response = client.post("/api/recommendations", json={**CONTEXT, **changes})
    assert response.status_code == 200, response.text
    return response.json()


def add(client, game_changes=None, goal_changes=None):
    game = client.post("/api/games", json={**GAME, **(game_changes or {})}).json()
    goal = client.post("/api/goals", json={**GOAL, **(goal_changes or {}), "game_id": game["id"]}).json()
    return game, goal


def test_persisted_mapping_and_complete_direct_scorer_parity(library):
    client, engine, _ = library
    game, goal = add(client, {"current_interest": 5, "friction": 2}, {"priority": 3})
    add(client, {"title": "Clockwork Peaks", "energy_required": "high", "experience_tags": ["challenge"]})
    expected = scoring.Candidate(game_id=game["id"], goal_id=goal["id"], game_title=game["title"],
        goal_title=goal["title"], estimated_minutes=30, energy_required="low", social_mode="solo",
        experience_tags=("chill", "progression"), interest=5, goal_priority=3, friction=2)
    with Session(engine) as db:
        candidates = load_candidates(db)
    assert candidates[0] == expected
    direct = scoring.recommend(candidates, scoring.SessionContext(**CONTEXT), evaluated_at=NOW)
    result = ask(library)
    assert result["engine_version"] == "v0.1-final-004"
    assert result["status"] == direct.status
    assert result["context"] == CONTEXT
    assert result["weights"] == vars(direct.weights)
    assert result["minimum_suitability"] == 25 and result["near_tie_margin"] == 3
    assert result["evaluated_at"] == NOW.isoformat().replace("+00:00", "Z")
    assert result["winner"]["candidate"]["goal_id"] == direct.winner.candidate.goal_id
    assert [r["candidate"]["goal_id"] for r in result["recommendations"]] == [r.candidate.goal_id for r in direct.recommendations]
    for actual, expected_score in zip(result["ranked"], direct.ranked, strict=True):
        assert actual["score"] == expected_score.score == sum(actual["breakdown"].values())
        assert actual["breakdown"] == expected_score.breakdown
        assert actual["suitability"] == expected_score.suitability
        assert actual["suitable"] == expected_score.suitable
        assert actual["unsuitable_reasons"] == list(expected_score.unsuitable_reasons)
        for factor, expected_factor in zip(actual["factors"], expected_score.factors, strict=True):
            assert factor["name"] == expected_factor.name
            assert factor["points"] == expected_factor.points
            assert factor["weight"] == expected_factor.weight
            assert factor["reason"] == expected_factor.reason
            # This scenario has no history; JSON converts only tuples to lists.
            assert factor["inputs"] == {k: list(v) if isinstance(v, tuple) else v for k, v in expected_factor.inputs}


@pytest.mark.parametrize("change", [
    {"available_minutes": 0}, {"available_minutes": -1}, {"available_minutes": True},
    {"available_minutes": 30.5}, {"available_minutes": "30"}, {"energy": "extreme"},
    {"social_preference": "both"}, {"desired_experience": "combat"}, {"extra": 1},
    {"energy": None},
])
def test_validation(library, change):
    client, _, _ = library
    assert client.post("/api/recommendations", json={**CONTEXT, **change}).status_code == 422


@pytest.mark.parametrize("missing", list(CONTEXT))
def test_required_fields(library, missing):
    client, _, _ = library
    assert client.post("/api/recommendations", json={k:v for k,v in CONTEXT.items() if k != missing}).status_code == 422


def test_empty_and_game_without_goals(library):
    assert ask(library)["status"] == "no_eligible"
    library[0].post("/api/games", json=GAME)
    result = ask(library)
    assert result["status"] == "no_eligible"
    assert result["winner"] is None
    assert result["ranked"] == result["excluded"] == result["recommendations"] == []


@pytest.mark.parametrize("action", ["game_archive", "goal_archive", "goal_complete", "time", "solo", "social"])
def test_hard_exclusions_preserve_scorer_reasons(library, action):
    client, engine, _ = library
    game, goal = seed(client)
    context = {}
    if action == "game_archive": client.delete(f'/api/games/{game["id"]}')
    if action == "goal_archive": client.delete(f'/api/goals/{goal["id"]}')
    if action == "goal_complete": client.post(f'/api/goals/{goal["id"]}/complete')
    if action == "time": context = {"available_minutes": 29}
    if action == "solo": client.patch(f'/api/games/{game["id"]}', json={"social_mode": "social"})
    if action == "social": context = {"social_preference": "social"}
    result = ask(library, **context)
    with Session(engine) as db:
        direct = scoring.recommend(load_candidates(db), scoring.SessionContext(**{**CONTEXT, **context}), evaluated_at=NOW)
    assert result["status"] == "no_eligible" and result["winner"] is None
    assert result["ranked"] == []
    assert result["excluded"][0]["candidate"]["goal_id"] == goal["id"]
    assert result["excluded"][0]["reasons"] == list(direct.excluded[0].reasons)


def test_no_good_fit_retains_unsuitable_audit(library):
    add(library[0], {"energy_required": "high", "experience_tags": ["challenge"], "current_interest": 5})
    result = ask(library)
    assert result["status"] == "no_good_fit" and result["winner"] is None
    assert result["recommendations"] == result["excluded"] == []
    assert not result["ranked"][0]["suitable"]
    assert result["ranked"][0]["unsuitable_reasons"]


def test_low_total_suitable_candidate_is_accepted(library):
    add(library[0], {"current_interest": 1, "friction": 5, "experience_tags": ["chill"]}, {"priority": 1})
    result = ask(library)
    assert result["status"] == "clear_recommendation"
    assert result["winner"]["score"] < 50
    assert result["winner"]["suitable"]


def test_unsuitable_raw_leader_is_not_winner(library):
    _, bad = add(library[0], {"energy_required": "high", "experience_tags": ["challenge"], "current_interest": 5}, {"priority": 3})
    _, good = add(library[0], {"current_interest": 1, "experience_tags": ["chill"], "friction": 5}, {"priority": 1})
    result = ask(library)
    assert result["ranked"][0]["candidate"]["goal_id"] == bad["id"]
    assert result["winner"]["candidate"]["goal_id"] == good["id"]


def test_equivalence_and_stable_order(library):
    _, first = add(library[0])
    _, second = add(library[0], {"title": "Another Orchard"})
    result = ask(library)
    assert result["status"] == "multiple_equivalent"
    assert [r["candidate"]["goal_id"] for r in result["recommendations"]] == [first["id"], second["id"]]
    assert ask(library) == result


def complete_row(game, goal, finished):
    return session_row(game, goal, started_at=finished-timedelta(minutes=30), finished_at=finished,
                       actual_duration_minutes=30, enjoyment_rating=4, progress="Harvested")


def test_latest_completed_is_per_game_and_unfinished_ignored(library):
    client, engine, _ = library
    game, goal = seed(client)
    other_goal = client.post("/api/goals", json={**GOAL, "game_id": game["id"], "title": "Build shed"}).json()
    other_game, other = add(client, {"title": "Cloud Harbor"})
    latest = NOW-timedelta(hours=1)
    with Session(engine) as db:
        db.add_all([complete_row(game, other_goal, latest), complete_row(game, goal, NOW-timedelta(days=5)),
                    complete_row(other_game, other, NOW-timedelta(days=10)),
                    session_row(game, goal, started_at=NOW-timedelta(minutes=5))])
        db.commit()
        candidates = load_candidates(db)
    assert [c.last_completed_session_at for c in candidates] == [latest, latest, NOW-timedelta(days=10)]
    result = ask(library)
    assert result["winner"]["candidate"]["game_id"] == other_game["id"]
    for row in result["ranked"]:
        factor = next(f for f in row["factors"] if f["name"] == "recent_play")
        assert factor["inputs"]
        assert row["candidate"]["last_completed_session_at"].endswith("Z")


def test_only_unfinished_history_has_no_recency(library):
    client, engine, _ = library
    game, goal = seed(client)
    with Session(engine) as db:
        db.add(session_row(game, goal)); db.commit()
    winner = ask(library)["winner"]
    assert winner["candidate"]["last_completed_session_at"] is None
    assert winner["breakdown"]["recent_play"] == 0


def test_one_clock_capture_one_scorer_call(library, monkeypatch):
    client, _, _ = library
    seed(client)
    calls = []
    clock_calls = []
    original = scoring.recommend
    def counted(*args, **kwargs):
        calls.append(kwargs["evaluated_at"])
        return original(*args, **kwargs)
    def clock():
        clock_calls.append(NOW)
        return NOW
    monkeypatch.setattr(scoring, "recommend", counted)
    monkeypatch.setattr("app.routes.utcnow", clock)
    assert client.post("/api/recommendations", json=CONTEXT).status_code == 200
    assert calls == clock_calls == [NOW]


def test_read_only_and_reopen_equivalence(library):
    client, engine, path = library
    game, goal = seed(client)
    with Session(engine) as db:
        db.add(complete_row(game, goal, NOW-timedelta(days=2))); db.commit()
    def snapshot():
        with sqlite3.connect(path) as connection:
            return list(connection.iterdump()), hashlib.sha256(path.read_bytes()).hexdigest()
    before = snapshot()
    result = ask(library)
    assert ask(library) == result
    assert snapshot() == before
    engine.dispose()
    fresh_app = create_app(path)
    fresh_app.dependency_overrides[get_evaluation_time] = lambda: NOW
    with TestClient(fresh_app) as fresh:
        assert fresh.post("/api/recommendations", json=CONTEXT).json() == result
    assert snapshot() == before
