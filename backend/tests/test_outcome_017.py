"""Behavioral experiment invariants; no DB, HTTP, private data, or new policy."""
from dataclasses import replace
from datetime import timedelta
import hashlib
from pathlib import Path

import pytest

from app.scoring import recommend
from experiments.outcome_017 import (
    AMPLITUDES, MODELS, NOW, WINDOW, Outcome, Scenario, evaluate,
    game, history, loop, observed, scenarios, signal,
)


@pytest.mark.parametrize("model", MODELS)
def test_repeat_and_input_permutation(model):
    for scenario in scenarios():
        expected = evaluate(scenario, model)
        assert expected == evaluate(scenario, model)
        assert expected == evaluate(replace(scenario, candidates=tuple(reversed(scenario.candidates)),
                                            history=tuple(reversed(scenario.history))), model)


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("amplitude", AMPLITUDES)
def test_neutral_cold_start_and_bounded_adjustment(model, amplitude):
    assert signal((), model, amplitude) == 0
    assert signal(history(1, [3] * 20), model, amplitude) == 0
    for scenario in scenarios():
        result = evaluate(scenario, model, amplitude)
        assert all(abs(row["adjustment"]) <= amplitude for row in result["scores"].values())
        if model == "M0":
            assert all(row["adjustment"] == 0 for row in result["scores"].values())


@pytest.mark.parametrize("model", MODELS)
def test_history_never_changes_eligibility_or_suitability(model):
    for scenario in scenarios():
        control = evaluate(scenario)
        result = evaluate(scenario, model, 10)
        assert result["excluded"] == control["excluded"]
        assert result["base_status"] == control["base_status"]
        assert {key: row["suitability"] for key, row in result["scores"].items()} == {
            key: row["suitability"] for key, row in control["scores"].items()}
        assert all(result["scores"][str(goal)]["suitability"] >= 25
                   for goal in result["base_choices"])
    unsuitable = replace(game(1), energy_required="high", experience_tags=("challenge",))
    abstention = Scenario("abstain", "no suitable activity", (unsuitable,), history(1, [5] * 20))
    assert evaluate(abstention, model, 10)["winner"] is None
    excluded = replace(game(1), social_mode="social")
    assert evaluate(Scenario("empty", "social excluded", (excluded,), history(1, [5] * 20)), model)["winner"] is None


def test_control_matches_frozen_engine():
    for scenario in scenarios():
        candidates = tuple(replace(candidate, last_completed_session_at=max(
            (row.finished_at for row in scenario.history if row.game_id == candidate.game_id
             and row.finished_at is not None), default=None)) for candidate in scenario.candidates)
        original = recommend(candidates, scenario.context, evaluated_at=NOW)
        result = evaluate(scenario)
        assert result["winner"] == (original.winner.candidate.game_id if original.winner else None)
        assert result["scores"] == {str(row.candidate.goal_id): {
            "game": row.candidate.game_id, "base": row.score, "suitability": row.suitability,
            "breakdown": row.breakdown, "adjustment": 0, "experimental_key": row.score}
            for row in original.ranked}


def test_m4_preserves_band_and_refuses_sparse_history():
    for scenario in scenarios():
        control = evaluate(scenario)
        for amplitude in AMPLITUDES:
            result = evaluate(scenario, "M4tie", amplitude)
            assert sorted(result["order"]) == sorted(
                control["scores"][str(goal)]["game"] for goal in control["base_choices"])
    assert signal(history(1, [5, 5]), "M4tie", 10) == 0


def test_confidence_shrinks_single_outcome_and_decays_old_evidence():
    one = history(1, [5], [0])
    assert signal(one, "M1", 3) == 3
    assert signal(one, "M2", 3) == 0.75
    assert signal(one, "M2cap", 3) == pytest.approx(0.6)
    assert signal(one, "M3exp", 3) == 0.75
    assert signal(history(1, [5], [30]), "M3exp", 3) == pytest.approx(3 / 7)
    assert signal(history(1, [5], [90]), "M3linear", 3) == 0
    assert signal(history(1, [5] * 10), "M2", 3) > signal(one, "M2", 3)


def test_selection_window_and_active_future_dates():
    rows = history(1, [4] * 500)
    assert len(observed(rows, 1)) == WINDOW
    assert observed(rows, 1) == observed(tuple(reversed(rows)), 1)
    active = Outcome(1, 1, None, None)
    future = Outcome(2, 1, NOW + timedelta(days=1), 5)
    assert observed((active, future), 1) == ()
    with pytest.raises(ValueError):
        observed((replace(rows[0], finished_at=NOW.replace(tzinfo=None)),), 1)
    with pytest.raises(ValueError):
        observed((replace(rows[0], enjoyment_rating=True),), 1)


def test_equal_time_uses_stable_session_id_and_fixtures_unique():
    rows = tuple(Outcome(i, 1, NOW, 4) for i in range(25))
    assert [row.id for row in observed(rows, 1)] == list(range(24, 4, -1))
    for scenario in scenarios():
        assert len({row.id for row in scenario.history}) == len(scenario.history)


def test_duration_progress_are_not_rating_proxies():
    rows = history(1, [4] * 5)
    changed = tuple(replace(row, actual_duration_minutes=1, available_minutes=120,
                           progress="No goal progress") for row in rows)
    for model in MODELS:
        assert signal(rows, model, 3) == signal(changed, model, 3)


def test_history_shared_by_game_not_multiplied_by_goal_count():
    first = game(1)
    second_goal = replace(first, goal_id=3)
    scenario = Scenario("shared", "two goals", (first, second_goal, game(2)), history(1, [5] * 4))
    rows = evaluate(scenario, "M2")["scores"]
    assert rows["1"]["adjustment"] == rows["3"]["adjustment"]


def test_falsification_context_and_near_tie_feedback_loop():
    by_code = {scenario.code: scenario for scenario in scenarios()}
    assert evaluate(by_code["G"], "M2")["winner"] == 2
    assert evaluate(by_code["G"], "M3exp")["winner"] == 1
    assert evaluate(by_code["P"], "M4tie")["winner"] == 1
    assert evaluate(by_code["P"], "M5context")["winner"] == 2
    assert loop("M0")["B"] == 5
    assert loop("M1")["B"] == 0
    assert loop("M4tie")["longest_run"] == 28
    assert loop("M4tie") == loop("M4tie")
    assert evaluate(by_code["J"], "M3exp", 10)["winner"] == 2
    assert evaluate(by_code["J"], "M4tie", 10)["winner"] == 1


@pytest.mark.parametrize("positive,negative", [(3, 1), (1, 3), (3, 3)])
def test_asymmetric_bounds_and_mean_sparse_counterexamples(positive, negative):
    by_code = {scenario.code: scenario for scenario in scenarios()}
    for scenario in scenarios():
        result = evaluate(scenario, "M3exp", 1, positive_scale=positive, negative_scale=negative)
        assert all(-negative <= row["adjustment"] <= positive for row in result["scores"].values())
    for code in ("S", "T"):
        assert evaluate(by_code[code], "M1")["winner"] == 2
        assert evaluate(by_code[code], "M2")["winner"] == 1
        assert evaluate(by_code[code], "M4tie")["winner"] == 1


def test_production_integrity_and_experiment_not_imported():
    root = Path(__file__).resolve().parents[1]
    assert hashlib.sha256((root / "app/scoring.py").read_bytes()).hexdigest() == (
        "b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a")
    for path in (root / "app").glob("*.py"):
        assert "outcome_017" not in path.read_text()
