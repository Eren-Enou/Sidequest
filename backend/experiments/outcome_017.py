"""Synthetic outcome investigation only; never imported by production code.

Run from backend: python -m experiments.outcome_017
The fixed clock and fictional records require no database or network.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import json
from statistics import mean, pvariance

from app.scoring import Candidate, SessionContext, recommend, NEAR_TIE_MARGIN

NOW = datetime(2026, 10, 4, 19, tzinfo=timezone.utc)
WINDOW = 20
PRIOR = 3
HALF_LIFE = 30
LINEAR_DAYS = 90
MIN_TIE_SAMPLES = 3
AMPLITUDES = (1, 2, 3, 5, 8, 10)
MODELS = ("M0", "M1", "M2", "M2cap", "M3exp", "M3linear", "M4tie", "M5context")
CONTEXT = SessionContext(60, "low", "solo", "progression")


@dataclass(frozen=True)
class Outcome:
    id: int
    game_id: int
    finished_at: datetime | None
    enjoyment_rating: int | None
    available_minutes: int = 60
    actual_duration_minutes: int = 30
    energy: str = "low"
    desired_experience: str = "progression"
    progress: str = "Fictional session progress"


@dataclass(frozen=True)
class Scenario:
    code: str
    purpose: str
    candidates: tuple[Candidate, ...]
    history: tuple[Outcome, ...] = ()
    context: SessionContext = CONTEXT


def game(number, interest=4, priority=2, friction=0, **fields):
    return Candidate(number, number, ("Sky Orchard", "Ember Expedition")[number - 1],
                     "Advance one chapter", 30, "low", "solo", ("progression",),
                     interest=interest, goal_priority=priority, friction=friction, **fields)


def history(game_id, ratings, days=None, **fields):
    days = list(days) if days is not None else list(range(1, len(ratings) + 1))
    if len(ratings) != len(days):
        raise ValueError("ratings and dates must align")
    return tuple(Outcome(game_id * 1000 + i, game_id, NOW - timedelta(days=day), rating,
                         **fields) for i, (rating, day) in enumerate(zip(ratings, days)))


def observed(rows, game_id, now=NOW):
    selected = []
    for row in rows:
        if row.finished_at is None or row.finished_at > now or row.game_id != game_id:
            continue
        if row.finished_at.tzinfo is None or type(row.enjoyment_rating) is not int or not 1 <= row.enjoyment_rating <= 5:
            raise ValueError("completed outcomes need aware dates and ratings 1..5")
        selected.append(row)
    return tuple(sorted(selected, key=lambda row: (row.finished_at, row.id), reverse=True)[:WINDOW])


def signal(rows, model, amplitude, context=CONTEXT, now=NOW):
    if amplitude < 0 or model not in MODELS:
        raise ValueError("invalid experiment configuration")
    if model == "M5context":
        rows = tuple(row for row in rows if row.energy == context.energy
                     and row.desired_experience == context.desired_experience)
    n = len(rows)
    if not rows or model == "M0" or (model == "M4tie" and n < MIN_TIE_SAMPLES):
        return 0.0
    values = [(row.enjoyment_rating - 3) / 2 for row in rows]
    if model == "M1":
        return amplitude * mean(values)
    if model in {"M2", "M2cap"}:
        confidence = n / (n + PRIOR) if model == "M2" else min(1, n / 5)
        return amplitude * mean(values) * confidence
    ages = [(now - row.finished_at).total_seconds() / 86400 for row in rows]
    weights = ([max(0, 1 - age / LINEAR_DAYS) for age in ages]
               if model == "M3linear" else [2 ** (-age / HALF_LIFE) for age in ages])
    return amplitude * sum(v * w for v, w in zip(values, weights)) / (sum(weights) + PRIOR)


def evaluate(scenario, model="M0", amplitude=3, now=NOW):
    candidates = tuple(replace(candidate, last_completed_session_at=max(
        (row.finished_at for row in scenario.history if row.game_id == candidate.game_id
         and row.finished_at is not None and row.finished_at <= now), default=None))
        for candidate in scenario.candidates)
    baseline = recommend(candidates, scenario.context, evaluated_at=now)
    eligible = {item.candidate.goal_id: item for item in baseline.ranked}
    suitable = [item for item in baseline.ranked if item.suitable]
    additions = {item.candidate.goal_id: signal(observed(scenario.history, item.candidate.game_id, now),
                 model, amplitude, scenario.context, now) for item in suitable}
    if model == "M4tie":
        # Preserve the original score, choice membership, status and abstention.
        # Only reorder the already accepted band by a bounded experimental key.
        band = list(baseline.recommendations)
        orderable = band
    else:
        orderable = suitable
    orderable.sort(key=lambda item: (-(item.score + additions[item.candidate.goal_id]),
                   -item.candidate.goal_priority, item.candidate.goal_id, item.candidate.game_id))
    order = [item.candidate.game_id for item in orderable]
    scores = {str(key): {"game": item.candidate.game_id, "base": item.score,
              "suitability": item.suitability, "breakdown": item.breakdown,
              "adjustment": additions.get(key, 0),
              "experimental_key": item.score + additions.get(key, 0)}
              for key, item in eligible.items()}
    return {"base_status": baseline.status, "base_choices": [x.candidate.goal_id for x in baseline.recommendations],
            "order": order, "winner": order[0] if order else None, "scores": scores,
            "excluded": [x.candidate.goal_id for x in baseline.excluded]}


def scenarios():
    strong = (game(1, 5, 3), game(2, 3, 2))
    # Equal preference; 2 friction points separate the frozen totals.
    close = (game(1), game(2, friction=1))
    return (
        Scenario("A", "No history: high interest/priority versus moderate", strong),
        Scenario("B", "One bad session for the strong favorite", strong, history(1, [1])),
        Scenario("C", "Eight bad recent sessions for the strong favorite", strong, history(1, [1] * 8)),
        Scenario("D", "One excellent session for the moderate alternative", strong, history(2, [5])),
        Scenario("E", "Eight excellent sessions for the moderate alternative", strong, history(2, [5] * 8)),
        Scenario("F", "Mixed 5/1/5/1/5 versus consistently neutral", close,
                 history(1, [5, 1, 5, 1, 5]) + history(2, [3] * 5)),
        Scenario("G", "Old bad, recent good versus no history", close,
                 history(1, [5] * 3 + [1] * 10, [1, 2, 3] + list(range(120, 130)))),
        Scenario("H", "Old good, recent bad versus no history", close,
                 history(1, [1] * 3 + [5] * 10, [1, 2, 3] + list(range(120, 130)))),
        Scenario("I", "100 mildly positive versus 2 excellent sessions", close,
                 history(1, [4] * 100) + history(2, [5, 5])),
        Scenario("J", "Strong explicit preference versus opposing repeated outcomes", strong,
                 history(1, [1] * 8) + history(2, [5] * 8)),
        Scenario("K", "Near tie with three bad versus three excellent sessions", close,
                 history(1, [1] * 3) + history(2, [5] * 3)),
        Scenario("L", "Initial state of 30 recommendation/play feedback cycles", close),
        Scenario("M", "Frequently played legitimate favorite", strong,
                 history(1, [5] * 20, [i / 2 for i in range(20)])),
        Scenario("N", "Duration anomalies: 20/120 versus 100/60; identical enjoyment", close,
                 history(1, [4], available_minutes=120, actual_duration_minutes=20)
                 + history(2, [4], available_minutes=60, actual_duration_minutes=100)),
        Scenario("O", "Enjoyable no-progress versus unenjoyable completed-goal narrative", close,
                 history(1, [5] * 4, progress="No measurable progress; relaxed")
                 + history(2, [1] * 4, progress="Finished objective; disliked session")),
        Scenario("P", "Context confounding: challenge good, current progression bad", close,
                 history(1, [1] * 3) + history(1, [5] * 10, range(4, 14),
                 energy="high", desired_experience="challenge")),
        Scenario("Q", "Unsuitable favorite stays unsuitable despite perfect outcomes",
                 (replace(game(1, 5, 3), energy_required="high", experience_tags=("challenge",)), game(2)),
                 history(1, [5] * 8)),
        Scenario("R", "Time-filtered favorite stays excluded despite perfect outcomes",
                 (replace(game(1, 5, 3), estimated_minutes=120), game(2)), history(1, [5] * 8)),
    )


def loop(model, amplitude=3, cycles=30):
    scenario = Scenario("L", "closed loop", (game(1), game(2, friction=1)))
    choices = []
    for index in range(cycles):
        now = NOW + timedelta(days=index)
        winner = evaluate(scenario, model, amplitude, now)["winner"]
        choices.append(winner)
        outcome = Outcome(10000 + index, winner, now, 5)
        scenario = replace(scenario, history=scenario.history + (outcome,))
    longest = run = 0
    previous = None
    for choice in choices:
        run = run + 1 if choice == previous else 1
        longest = max(longest, run)
        previous = choice
    return {"A": choices.count(1), "B": choices.count(2), "longest_run": longest, "choices": choices}


def results():
    return {"clock": NOW.isoformat(), "scenario_count": len(scenarios()),
            "scenarios": {scenario.code: {"purpose": scenario.purpose,
                "models": {model: evaluate(scenario, model) for model in MODELS},
                "sweep": {str(amp): {model: evaluate(scenario, model, amp)["winner"]
                          for model in MODELS} for amp in AMPLITUDES}}
                for scenario in scenarios()},
            "loops": {str(amp): {model: loop(model, amp) for model in MODELS} for amp in AMPLITUDES}}


if __name__ == "__main__":
    print(json.dumps(results(), sort_keys=True, indent=2))
