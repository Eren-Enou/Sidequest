from dataclasses import replace
from datetime import timedelta

import pytest

from app.scoring import SessionContext
from examples.evaluation_001 import SCENARIOS, EVALUATED_AT, candidate
from experiments.comparison_002 import compare, ADDITIONAL
from experiments.policy_002 import POLICY, recommend


def run_scenario(s):
    return recommend(s.candidates, s.context, evaluated_at=EVALUATED_AT)


def test_all_scenarios_comparable_and_deterministic():
    assert len(compare()) == 19


def test_low_energy_winner_changes():
    result = run_scenario(SCENARIOS[0])
    assert result.winner.scored.candidate.game_title == "Moonlit Orchard"
    assert result.status == "clear_recommendation"


def test_favorite_with_energy_mismatch_still_possible():
    assert run_scenario(ADDITIONAL[0]).winner.scored.candidate.game_title == "Iron Summit"


def test_duration_near_equals_tie():
    result = run_scenario(SCENARIOS[4])
    assert result.status == "multiple_equivalent"
    assert [a.scored.score for a in result.recommendations] == [84.25, 84.25]
    assert result.winner.scored.candidate.goal_id == 1


def test_recent_favorite_not_displaced_by_one_interest_step():
    result = run_scenario(SCENARIOS[5])
    assert result.status == "clear_recommendation"
    assert result.winner.scored.candidate.game_title == "Moonlit Orchard"


@pytest.mark.parametrize("days,penalty", [(0, -3), (3.5, -1.5), (7, 0), (8, 0), (-1, -3), (None, 0)])
def test_recency_boundaries(days, penalty):
    c = candidate(1, "Garden", "Harvest", 30, "low", ["chill"], 4, 2, days=days)
    result = recommend([c], SessionContext(30, "low", "solo", "chill"), evaluated_at=EVALUATED_AT)
    assert result.ranked[0].scored.breakdown["recent_play"] == penalty


def test_friction_remains_unchanged():
    result = run_scenario(SCENARIOS[6])
    assert result.winner.scored.candidate.game_title == "Harbor Builder"
    assert result.ranked[1].scored.breakdown["friction"] == -10


def test_negative_score_has_no_good_fit():
    result = run_scenario(SCENARIOS[11])
    assert result.status == "no_good_fit"
    assert result.winner is None
    assert result.ranked[0].unsuitable_reasons


def test_no_eligible_is_distinct():
    assert run_scenario(SCENARIOS[12]).status == "no_eligible"
    assert recommend([], SCENARIOS[0].context, evaluated_at=EVALUATED_AT).status == "no_eligible"


def test_suitability_gate_is_independent_of_total():
    result = run_scenario(ADDITIONAL[5])
    item = result.ranked[0]
    assert item.scored.score == 48
    assert item.suitability == 8
    # A comfortable estimate raises the total to 50, but the suitability gate still fails.
    c = replace(item.scored.candidate, estimated_minutes=20)
    item = recommend([c], ADDITIONAL[5].context, evaluated_at=EVALUATED_AT).ranked[0]
    assert item.scored.score == POLICY.minimum_total
    assert not item.suitable
    assert len(item.unsuitable_reasons) == 1


def test_total_threshold_inclusive():
    c = candidate(1, "Garden", "Chore", 20, "low", ["chill"], 1, 1)
    context = SessionContext(30, "low", "solo", "challenge")
    assert recommend([c], context, evaluated_at=EVALUATED_AT).status == "no_good_fit"
    # S=40, priority 7.5, interest 6.25, friction 4 => 49.75.
    c = replace(c, interest=2, goal_priority=2, friction=2)
    assert recommend([c], context, evaluated_at=EVALUATED_AT).ranked[0].scored.score == 49.75
    assert recommend([c], context, evaluated_at=EVALUATED_AT).status == "no_good_fit"
    c = replace(c, friction=1)
    assert recommend([c], context, evaluated_at=EVALUATED_AT).status == "clear_recommendation"
    exact = candidate(1, "Garden", "Harvest", 30, "low", ["chill"], 1, 1, 4)
    exact_context = replace(context, desired_experience="chill")
    result = recommend([exact], exact_context, evaluated_at=EVALUATED_AT)
    assert result.winner.scored.score == POLICY.minimum_total


def test_suitability_threshold_inclusive():
    c = candidate(1, "Workshop", "Upgrade", 20, "medium", ["progression"], 5, 3)
    result = recommend([c], SessionContext(30, "low", "solo", "chill"), evaluated_at=EVALUATED_AT)
    assert result.winner.suitability == POLICY.minimum_suitability


def test_near_tie_inclusive_and_anchored_to_best():
    context = SessionContext(30, "low", "solo", "chill")
    best = candidate(1, "Garden", "Harvest", 30, "low", ["chill"], 4, 2, days=7)
    # Three days selected so the recency penalty is 3 and 1.5; friction adds 2.
    edge = replace(best, goal_id=2, game_id=2, last_completed_session_at=EVALUATED_AT)
    outside = replace(best, goal_id=3, game_id=3, friction=1,
                      last_completed_session_at=EVALUATED_AT - timedelta(days=3.5))
    result = recommend([outside, edge, best], context, evaluated_at=EVALUATED_AT)
    assert [a.scored.candidate.goal_id for a in result.recommendations] == [1, 2]
    assert result.ranked[0].scored.score - result.ranked[2].scored.score == 3.5


@pytest.mark.parametrize("minutes,points", [(1, 10), (27, 10), (28, 8), (29, 8), (30, 8)])
def test_time_plateau_and_buffer_boundary(minutes, points):
    s = SCENARIOS[4]
    c = replace(s.candidates[0], estimated_minutes=minutes)
    assert recommend([c], s.context, evaluated_at=EVALUATED_AT).ranked[0].scored.breakdown["time_fit"] == points


def test_exact_tie_and_social_absent():
    result = run_scenario(SCENARIOS[10])
    assert result.status == "multiple_equivalent"
    assert result.winner.scored.candidate.goal_id == 1
    assert all("social_fit" not in a.scored.breakdown for a in result.ranked)


def test_suitable_candidates_only_in_recommendation_group():
    result = run_scenario(ADDITIONAL[4])
    assert len(result.ranked) == 2
    assert all(a.suitable for a in result.recommendations)
    assert any(not a.suitable for a in result.ranked)
