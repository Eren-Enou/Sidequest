"""Report 009 regressions at the projection, API, and persisted-read boundary."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import nextafter

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import create_app
from app.models import PlaySession
from app.recommendation_schemas import RecommendationRequest, response_from_result
from app.routes import get_evaluation_time
from app.scoring import Candidate, SessionContext, recommend
from app.session_routes import get_operation_time
from app.session_schemas import RecommendationSnapshot
from test_library_api import library

NOW = datetime(2026, 10, 4, 4, 10, tzinfo=timezone.utc)
CONTEXT = dict(available_minutes=90, energy="high",
               social_preference="either", desired_experience="challenge")
CLOUD_BREAKDOWN = dict(interest=18.75, goal_priority=15.0,
                       time_fit=6.666666666666667, energy_fit=30.0,
                       experience_fit=0.0, friction=0.0, recent_play=0.0)
CLOUD_SCORE = 70.41666666666666


def response(desired="challenge", equivalent=False):
    context = RecommendationRequest(**{**CONTEXT, "desired_experience": desired})
    candidates = [
        Candidate(1, 1, "Iron Summit", "Advance chapter", 45, "high", "solo",
                  ("challenge",), 5, 3, 2),
        Candidate(2, 2, "Cloud Garden", "Advance chapter", 30, "low", "both",
                  ("chill", "progression"), 4, 3, 0),
    ]
    if equivalent:
        candidates.append(Candidate(3, 3, "Cloud Harbor", "Advance chapter", 30,
                                    "low", "both", ("progression",), 4, 3, 0))
    result = recommend(candidates, SessionContext(**context.model_dump()), evaluated_at=NOW)
    return response_from_result(result, context)


def payload(result=None):
    result = result or response()
    return dict(snapshot_version=1, selected=result.winner.model_dump(mode="json"),
                evaluation=result.model_dump(mode="json"))


def change_score(data, goal_id, value):
    # Keep duplicate evidence copies identical so only the arithmetic invariant
    # is exercised, not the independent exact membership/copy invariants.
    evaluation = data["evaluation"]
    items = [data["selected"], evaluation["winner"],
             *evaluation["recommendations"], *evaluation["ranked"]]
    for item in items:
        if item["candidate"]["goal_id"] == goal_id:
            item["score"] = value


def test_exact_report_009_snapshot_without_rewriting_evidence():
    result = response()
    cloud = result.ranked[1]
    assert result.winner.candidate.game_title == "Iron Summit"
    assert result.winner.score == 96.0
    assert cloud.score == CLOUD_SCORE
    assert cloud.breakdown == CLOUD_BREAKDOWN
    assert sum(cloud.breakdown.values()) == 70.41666666666667
    assert cloud.score != sum(cloud.breakdown.values())
    data = payload(result)
    saved = RecommendationSnapshot.model_validate(data)
    assert saved.model_dump(mode="json") == data


@pytest.mark.parametrize("role", ["selected", "equivalent", "audit"])
def test_representation_noise_in_each_candidate_role(role):
    result = response("progression", equivalent=True) if role != "audit" else response()
    goal_id = {"selected": 2, "equivalent": 3, "audit": 2}[role]
    data = payload(result)
    item = next(row for row in data["evaluation"]["ranked"]
                if row["candidate"]["goal_id"] == goal_id)
    change_score(data, goal_id, nextafter(item["score"], float("inf")))
    assert RecommendationSnapshot.model_validate(data).model_dump(mode="json") == data


@pytest.mark.parametrize("goal_id", [1, 2])
@pytest.mark.parametrize("delta", [1e-6, -1e-6, 0.01, -1.0])
def test_material_selected_and_unselected_inconsistency_is_rejected(goal_id, delta):
    data = payload()
    item = next(row for row in data["evaluation"]["ranked"]
                if row["candidate"]["goal_id"] == goal_id)
    change_score(data, goal_id, item["score"] + delta)
    with pytest.raises(ValidationError, match="breakdown must sum to score"):
        RecommendationSnapshot.model_validate(data)


@pytest.mark.parametrize("score", [0.0, 5e-13, -5e-13, 100.0 + 5e-11])
def test_absolute_and_relative_tolerance_accept_only_tiny_noise(score):
    data = payload()
    row = data["evaluation"]["ranked"][1]
    total = 100.0 if score > 1 else 0.0
    row["breakdown"] = {name: total if name == "interest" else 0.0
                        for name in row["breakdown"]}
    for factor in row["factors"]:
        factor["points"] = row["breakdown"][factor["name"]]
    change_score(data, 2, score)
    assert RecommendationSnapshot.model_validate(data).evaluation.ranked[1].score == score


@pytest.mark.parametrize("score,total", [(2e-12, 0.0), (100.0 + 2e-10, 100.0)])
def test_values_outside_absolute_and_relative_tolerance_are_rejected(score, total):
    data = payload()
    row = data["evaluation"]["ranked"][1]
    row["breakdown"] = {name: total if name == "interest" else 0.0
                        for name in row["breakdown"]}
    for factor in row["factors"]:
        factor["points"] = row["breakdown"][factor["name"]]
    change_score(data, 2, score)
    with pytest.raises(ValidationError, match="breakdown must sum to score"):
        RecommendationSnapshot.model_validate(data)


@pytest.mark.parametrize("value", [float("inf"), -float("inf"), float("nan")])
def test_nonfinite_values_are_not_numerical_equivalence(value):
    data = payload()
    row = data["evaluation"]["ranked"][1]
    row["breakdown"]["interest"] = value
    row["factors"][0]["points"] = value
    change_score(data, 2, value)
    with pytest.raises(ValidationError, match="breakdown must sum to score"):
        RecommendationSnapshot.model_validate(data)


def test_factor_copy_validation_remains_exact():
    data = payload()
    data["evaluation"]["ranked"][1]["factors"][0]["points"] += 1e-13
    with pytest.raises(ValidationError, match="factor contributions must match breakdown"):
        RecommendationSnapshot.model_validate(data)


@pytest.fixture
def numeric_library(library, monkeypatch):
    client, engine, path = library
    monkeypatch.setattr("app.routes.utcnow", lambda: NOW - timedelta(days=1))
    client.app.dependency_overrides[get_evaluation_time] = lambda: NOW
    client.app.dependency_overrides[get_operation_time] = lambda: NOW
    pairs = []
    for candidate in response().ranked:
        item = candidate.candidate
        game = client.post("/api/games", json=dict(title=item.game_title,
            energy_required=item.energy_required, social_mode=item.social_mode,
            experience_tags=item.experience_tags, current_interest=item.interest,
            friction=item.friction)).json()
        goal = client.post("/api/goals", json=dict(game_id=game["id"],
            title=item.goal_title, estimated_minutes=item.estimated_minutes,
            priority=item.goal_priority)).json()
        pairs.append((game, goal))
    return client, engine, path, pairs


def begin(client, pairs):
    game, goal = pairs[0]
    result = client.post("/api/sessions/start", json=dict(
        game_id=game["id"], goal_id=goal["id"], situation=CONTEXT))
    assert result.status_code == 201, result.text
    return result.json()


def test_report_009_real_start_persistence_reopen_finish_and_history(numeric_library):
    client, engine, path, pairs = numeric_library
    before = client.post("/api/recommendations", json=CONTEXT).json()
    row = begin(client, pairs)
    evidence = row["recommendation_snapshot"]
    assert evidence["evaluation"] == before
    assert evidence["selected"] == before["winner"]
    assert evidence["selected"]["candidate"]["game_title"] == "Iron Summit"
    assert evidence["selected"]["score"] == 96.0
    cloud = evidence["evaluation"]["ranked"][1]
    assert cloud["score"] == CLOUD_SCORE and cloud["breakdown"] == CLOUD_BREAKDOWN
    assert len(cloud["factors"]) == 7
    with Session(engine) as db:
        persisted = db.get(PlaySession, row["id"])
        assert persisted.recommendation_snapshot == evidence
    fresh_app = create_app(path)
    fresh_app.dependency_overrides[get_operation_time] = lambda: NOW + timedelta(minutes=30)
    with TestClient(fresh_app) as fresh:
        assert fresh.get("/api/sessions/active").json() == row
        assert fresh.get(f'/api/sessions/{row["id"]}').json() == row
        done = fresh.post(f'/api/sessions/{row["id"]}/finish', json=dict(
            actual_duration_minutes=30, enjoyment_rating=4, progress="Advanced chapter",
            notes="Original evidence retained", mark_goal_completed=True))
        assert done.status_code == 200, done.text
        completed = done.json()
        assert completed["recommendation_snapshot"] == evidence
        assert fresh.get(f'/api/goals/{pairs[0][1]["id"]}').json()["status"] == "completed"
    with TestClient(create_app(path)) as fresh:
        assert fresh.get("/api/sessions/active").json() is None
        assert fresh.get("/api/sessions").json() == [completed]
        assert fresh.get(f'/api/sessions/{row["id"]}').json() == completed


def test_integer_exact_snapshot_and_duplicate_conflicts(numeric_library):
    client, _, _, pairs = numeric_library
    row = begin(client, pairs)
    assert row["recommendation_snapshot"]["selected"]["score"] == 96
    game, goal = pairs[0]
    assert client.post("/api/sessions/start", json=dict(game_id=game["id"],
        goal_id=goal["id"], situation=CONTEXT)).status_code == 409
    body = dict(actual_duration_minutes=30, enjoyment_rating=4, progress="Original finish")
    done = client.post(f'/api/sessions/{row["id"]}/finish', json=body)
    assert done.status_code == 200
    duplicate = client.post(f'/api/sessions/{row["id"]}/finish',
                            json={**body, "progress": "Do not overwrite"})
    assert duplicate.status_code == 409
    assert client.get("/api/sessions").json() == [done.json()]


@pytest.mark.parametrize("goal_index", [0, 1])
def test_corrupt_persisted_selected_or_audit_score_rejected(numeric_library, goal_index):
    client, engine, path, pairs = numeric_library
    row = begin(client, pairs)
    with Session(engine) as db:
        saved = db.get(PlaySession, row["id"])
        data = deepcopy(saved.recommendation_snapshot)
        target = data["evaluation"]["ranked"][goal_index]
        change_score(data, target["candidate"]["goal_id"], target["score"] + 0.01)
        saved.recommendation_snapshot = data
        db.commit()
    # Invalid persisted evidence must fail response validation, not be repaired
    # or silently exposed. FastAPI's TestClient raises its validation exception.
    from fastapi.exceptions import ResponseValidationError
    with TestClient(create_app(path)) as fresh:
        with pytest.raises(ResponseValidationError, match="breakdown must sum to score"):
            fresh.get(f'/api/sessions/{row["id"]}')
    with Session(engine) as db:
        assert db.get(PlaySession, row["id"]).recommendation_snapshot == data
