"""Research probes: fictional facts and unchanged production API behavior."""
from dataclasses import replace

import pytest

from experiments.progression_019 import MODELS, complete, evaluate, scenarios
from test_library_api import library, GAME, GOAL
from test_sessions_api import lifecycle, start, finish


@pytest.mark.parametrize("scenario", scenarios(), ids=lambda s: s.key)
def test_research_comparison_preserves_scores_and_is_order_independent(scenario):
    baseline = evaluate(scenario, "M0")
    scores = {r["goal_id"]: r for r in baseline["ranked"]}
    for model in MODELS:
        result = evaluate(scenario, model)
        assert result == evaluate(replace(scenario, goals=tuple(reversed(scenario.goals))), model)
        for row in result["ranked"]:
            assert row == scores[row["goal_id"]]
            assert row["score"] == sum(row["breakdown"].values())
    assert baseline == {**evaluate(scenario, "M1"), "model": "M0"}
    assert baseline == {**evaluate(scenario, "M5"), "model": "M0"}


def scenario(key):
    return next(s for s in scenarios() if s.key == key)


def test_future_priority_can_displace_current_but_readiness_is_not_priority():
    s = scenario("A")
    assert evaluate(s, "M0")["choices"] == [2]
    assert evaluate(s, "M2")["choices"] == [1]
    low = replace(s, goals=tuple(replace(p, candidate=replace(p.candidate, goal_priority=1))
                                for p in s.goals))
    assert evaluate(low, "M2")["choices"] == [1]


def test_parallel_current_goals_falsify_one_head_queue():
    assert evaluate(scenario("B"), "M2")["choices"] == [1, 2, 3, 4]
    assert evaluate(scenario("B"), "M3")["choices"] == [1]
    assert evaluate(scenario("C"), "M3")["choices"] == [1]


def test_remaining_time_exposes_manual_promotion_cost():
    assert evaluate(scenario("M"), "M2")["status"] == "no_eligible"
    assert evaluate(scenario("M"), "M3")["choices"] == [2]
    assert evaluate(scenario("M"), "M4")["choices"] == [2]


def test_long_current_is_not_automatically_replaced_by_later():
    s = scenario("N")
    assert evaluate(s, "M0")["choices"] == [2]
    result = evaluate(s, "M2")
    assert result["status"] == "no_eligible"
    assert result["excluded"][0]["goal_id"] == 1
    assert result["withheld"][0]["goal_id"] == 2


def test_dependency_edges_do_not_resolve_exclusive_branches():
    assert evaluate(scenario("E"), "M4")["choices"] == [1, 2]
    assert evaluate(complete(scenario("A"), 1), "M4")["choices"] == [2]
    assert evaluate(complete(scenario("A"), 1), "M2")["status"] == "no_eligible"


def test_actual_api_does_not_parse_titles_notes_or_priority_as_readiness(library):
    client, _, _ = library
    game = client.post("/api/games", json=GAME).json()
    for priority in (1, 3):
        response = client.post("/api/goals", json={**GOAL, "game_id": game["id"],
            "title": "Later: chapter 3", "notes": "Requires unfinished chapter 2", "priority": priority})
        assert response.status_code == 201
    result = client.post("/api/recommendations", json=vars(scenario("A").context)).json()
    assert len(result["ranked"]) == 2 and not result["excluded"]
    assert result["winner"]["candidate"]["goal_priority"] == 3


@pytest.mark.parametrize("mark_complete", [False, True])
def test_actual_finish_records_progress_without_inference_or_next_goal(lifecycle, mark_complete):
    client, _, _ = lifecycle
    game = client.post("/api/games", json=GAME).json()
    goal = client.post("/api/goals", json={**GOAL, "game_id": game["id"],
                                          "notes": "Private fictional planning note"}).json()
    response = start(client, game, goal)
    assert response.status_code == 201
    row = response.json()
    saved = row["recommendation_snapshot"]
    response = finish(client, row, mark_goal_completed=mark_complete, progress="Chapter complete")
    assert response.status_code == 200
    current = client.get(f'/api/goals/{goal["id"]}').json()
    assert current["status"] == ("completed" if mark_complete else "active")
    assert len(client.get("/api/goals").json()) == 1
    history = client.get("/api/sessions").json()[0]
    assert history["recommendation_snapshot"] == saved
    assert "mark_goal_completed" not in history
    assert "notes" not in saved["selected"]["candidate"]
