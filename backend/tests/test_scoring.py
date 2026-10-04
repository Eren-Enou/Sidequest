from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.scoring import Candidate, ScoringWeights, SessionContext, recommend
from examples.recommendation import sample

NOW = datetime(2026, 10, 3, 19, tzinfo=timezone.utc)
CONTEXT = SessionContext(30, "low", "solo", "chill")
BASE = Candidate(1, 1, "Sample Garden", "Harvest crops", 30, "low", "solo", ("chill",))


def run(*candidates, context=CONTEXT, **kwargs):
    return recommend(candidates, context, evaluated_at=NOW, **kwargs)


def test_obvious_winner():
    weak = replace(BASE, goal_id=2, interest=1, goal_priority=1,
                   energy_required="high", experience_tags=("challenge",), friction=5,
                   last_completed_session_at=NOW)
    strong = replace(BASE, interest=5, goal_priority=3)
    result = run(weak, strong)
    assert result.winner.candidate == strong
    assert result.winner.score == 100
    assert result.ranked[1].score == 5


def test_time_filter_and_exact_boundary():
    result = run(BASE, replace(BASE, goal_id=2, estimated_minutes=31))
    assert len(result.ranked) == 1
    assert result.ranked[0].breakdown["time_fit"] == 15
    assert result.excluded[0].reasons == ("Needs 31 minutes; only 30 available.",)


@pytest.mark.parametrize("preference,mode,eligible", [
    ("solo", "solo", True), ("solo", "social", False), ("solo", "both", True),
    ("social", "solo", False), ("social", "social", True), ("social", "both", True),
    ("either", "solo", True), ("either", "social", True), ("either", "both", True),
])
def test_social_compatibility(preference, mode, eligible):
    result = run(replace(BASE, social_mode=mode), context=replace(CONTEXT, social_preference=preference))
    assert bool(result.ranked) == eligible
    assert bool(result.excluded) != eligible
    if eligible:
        assert result.winner.breakdown["social_fit"] == 10
    else:
        assert "only" in result.excluded[0].reasons[0]


@pytest.mark.parametrize("available,required,points", [
    ("low", "low", 15), ("low", "medium", 7.5), ("low", "high", 0),
    ("medium", "low", 15), ("medium", "medium", 15), ("medium", "high", 7.5),
    ("high", "low", 15), ("high", "medium", 15), ("high", "high", 15),
])
def test_energy_boundaries(available, required, points):
    result = run(replace(BASE, energy_required=required), context=replace(CONTEXT, energy=available))
    assert result.winner.breakdown["energy_fit"] == points


def test_low_energy_favors_appropriate_activity():
    result = run(replace(BASE, goal_id=2, energy_required="high"), BASE)
    assert result.winner.candidate == BASE
    assert len(result.ranked) == 2


def test_experience_changes_winner():
    challenge = replace(BASE, goal_id=2, experience_tags=("challenge", "progression"))
    assert run(BASE, challenge).winner.candidate == BASE
    assert run(BASE, challenge, context=replace(CONTEXT, desired_experience="challenge")).winner.candidate == challenge


@pytest.mark.parametrize("field,low,high,difference", [
    ("interest", 1, 5, 25), ("goal_priority", 1, 3, 15),
    ("estimated_minutes", 15, 30, 7.5), ("friction", 0, 5, -10),
])
def test_factor_direction_and_range(field, low, high, difference):
    first = run(replace(BASE, **{field: low})).winner.score
    second = run(replace(BASE, **{field: high})).winner.score
    assert second - first == difference


@pytest.mark.parametrize("days,penalty", [(0, -10), (3.5, -5), (7, 0), (20, 0), (-1, -10)])
def test_recent_play_window(days, penalty):
    candidate = replace(BASE, last_completed_session_at=NOW - timedelta(days=days))
    result = run(candidate)
    assert result.winner.breakdown["recent_play"] == penalty
    assert result.winner.score <= run(BASE).winner.score


def test_never_played_has_no_penalty():
    assert run(BASE).winner.breakdown["recent_play"] == 0


def test_breakdown_and_explanation_complete():
    item = run(replace(BASE, estimated_minutes=17, last_completed_session_at=NOW - timedelta(hours=11))).winner
    assert item.score == sum(item.breakdown.values())
    assert set(item.breakdown) == set(vars(ScoringWeights()))
    for factor in item.factors:
        assert factor.reason
        assert factor.inputs
        assert abs(factor.points) <= factor.weight


def test_ties_use_priority_then_goal_id_independent_of_input_order():
    # Zero priority weight allows equal total scores with different priorities.
    weights = ScoringWeights(goal_priority=0)
    low = replace(BASE, goal_id=1, goal_priority=1)
    high_a = replace(BASE, goal_id=3, goal_priority=3)
    high_b = replace(BASE, goal_id=2, goal_priority=3)
    result = run(low, high_a, high_b, weights=weights)
    assert [x.candidate.goal_id for x in result.ranked] == [2, 3, 1]
    assert result == run(high_b, high_a, low, weights=weights)


def test_identical_inputs_repeat_and_do_not_mutate():
    candidates = [BASE, replace(BASE, goal_id=2, friction=3)]
    original = candidates.copy()
    assert run(*candidates) == run(*candidates)
    assert candidates == original


@pytest.mark.parametrize("changes", [{"game_archived": True}, {"goal_status": "completed"}, {"goal_status": "archived"}])
def test_inactive_candidates_excluded(changes):
    result = run(replace(BASE, **changes))
    assert result.winner is None
    assert result.excluded[0].reasons


def test_empty_and_multiple_exclusion_reasons():
    assert run().winner is None
    bad = replace(BASE, goal_id=2, game_archived=True, goal_status="completed",
                  estimated_minutes=40, social_mode="social")
    result = run(bad, replace(bad, goal_id=1))
    assert len(result.excluded[0].reasons) == 4
    assert [x.candidate.goal_id for x in result.excluded] == [1, 2]


@pytest.mark.parametrize("changes", [
    {"estimated_minutes": 0}, {"estimated_minutes": True}, {"game_id": -1},
    {"goal_id": 1.5}, {"interest": 0}, {"interest": 6}, {"friction": -1},
    {"friction": 6}, {"goal_priority": 4}, {"energy_required": "extreme"},
    {"social_mode": "either"}, {"experience_tags": ()}, {"experience_tags": ("invalid",)},
    {"experience_tags": "chill"}, {"game_title": " "}, {"goal_status": "unknown"},
    {"game_archived": 1}, {"last_completed_session_at": datetime(2026, 1, 1)},
])
def test_invalid_candidates(changes):
    with pytest.raises(ValueError):
        replace(BASE, **changes)


@pytest.mark.parametrize("changes", [
    {"available_minutes": 0}, {"available_minutes": 1.5}, {"available_minutes": True},
    {"energy": "invalid"}, {"social_preference": "both"}, {"desired_experience": "invalid"},
])
def test_invalid_context(changes):
    with pytest.raises(ValueError):
        replace(CONTEXT, **changes)


def test_invalid_weights_clock_and_duplicate_ids():
    with pytest.raises(ValueError):
        ScoringWeights(interest=-1)
    with pytest.raises(ValueError):
        ScoringWeights(interest=True)
    with pytest.raises(ValueError):
        recommend([BASE], CONTEXT, evaluated_at=datetime(2026, 1, 1))
    with pytest.raises(ValueError, match="Duplicate goal_id"):
        run(BASE, BASE)


def test_timezone_conversion_and_tag_normalization():
    local_now = NOW.astimezone(timezone(timedelta(hours=-7)))
    local_candidate = replace(BASE, experience_tags=["progression", "chill", "chill"],
                              last_completed_session_at=local_now - timedelta(days=3.5))
    assert local_candidate.experience_tags == ("chill", "progression")
    assert recommend([local_candidate], CONTEXT, evaluated_at=local_now).winner.breakdown["recent_play"] == -5
    assert recommend([BASE], CONTEXT, evaluated_at=local_now) == run(BASE)


def test_fictional_example():
    result = sample()
    assert result.winner.candidate.game_title == "Moonlit Orchard"
    assert result.winner.score == 85.5
    assert len(result.ranked) == 3
    assert result.excluded[0].candidate.game_title == "Starship Crew"
