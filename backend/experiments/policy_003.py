"""Experiment 003 changes only the time contribution of Experiment 002.

Reuse the previous experiment as a frozen research dependency; never select this
module from the production engine. Alternative curves are evaluation functions.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from fractions import Fraction
from typing import Iterable

from app.scoring import Candidate, SessionContext, Factor, ScoredCandidate
from experiments.policy_002 import POLICY as PREVIOUS_POLICY, Assessment, Result
from experiments.policy_002 import recommend as previous_recommend

POLICY_VERSION = "experiment-003"


@dataclass(frozen=True)
class TimePolicy:
    preferred_start: Fraction = Fraction(1, 2)
    preferred_end: Fraction = Fraction(9, 10)
    full_window_fraction: Fraction = Fraction(4, 5)
    parabola_peak: Fraction = Fraction(7, 10)


TIME_POLICY = TimePolicy()


def time_points(estimated_minutes: int, available_minutes: int, approach="linear_plateau") -> float:
    """Continuous curves on eligible integer durations; invalid/ineligible times raise.

    Fraction calculations keep exact breakpoint/threshold cases free of incidental
    binary rounding in the duration term; returned contributions are plain floats.
    """
    if (type(estimated_minutes) is not int or type(available_minutes) is not int
            or not 0 < estimated_minutes <= available_minutes):
        raise ValueError("Duration must be positive integer minutes within the available window")
    r = Fraction(estimated_minutes, available_minutes)
    t = TIME_POLICY
    if approach == "bounded_parabola":
        fraction = 1 - ((r - t.parabola_peak) / t.parabola_peak) ** 2
    elif approach in ("linear_plateau", "smooth_plateau"):
        if r < t.preferred_start:
            fraction = r / t.preferred_start
            if approach == "smooth_plateau":
                fraction = 3 * fraction ** 2 - 2 * fraction ** 3
        elif r <= t.preferred_end:
            fraction = Fraction(1)
        else:
            position = (r - t.preferred_end) / (1 - t.preferred_end)
            if approach == "smooth_plateau":
                position = 3 * position ** 2 - 2 * position ** 3
            fraction = 1 - (1 - t.full_window_fraction) * position
    else:
        raise ValueError(f"Unknown time approach: {approach}")
    return float(PREVIOUS_POLICY.time_fit * fraction)


def recommend(candidates: Iterable[Candidate], context: SessionContext, *, evaluated_at: datetime) -> Result:
    previous = previous_recommend(candidates, context, evaluated_at=evaluated_at)
    assessments = []
    p = PREVIOUS_POLICY
    for old in previous.ranked:
        c = old.scored.candidate
        time = Factor("time_fit", time_points(c.estimated_minutes, context.available_minutes), p.time_fit,
                      (("estimated_minutes", c.estimated_minutes), ("available_minutes", context.available_minutes),
                       ("preferred_start", float(TIME_POLICY.preferred_start)),
                       ("preferred_end", float(TIME_POLICY.preferred_end)),
                       ("full_window_fraction", float(TIME_POLICY.full_window_fraction))),
                      "Ramp to half the session, full points from 50% to 90%, gradual decline to 8 at 100%.")
        scored = ScoredCandidate(c, tuple(time if f.name == "time_fit" else f for f in old.scored.factors))
        suitability = sum(scored.breakdown[name] for name in ("time_fit", "energy_fit", "experience_fit"))
        reasons = []
        if suitability < p.minimum_suitability:
            reasons.append(f"Situational suitability {suitability} is below {p.minimum_suitability}.")
        if scored.score < p.minimum_total:
            reasons.append(f"Total score {scored.score} is below {p.minimum_total}.")
        assessments.append(Assessment(scored, suitability, tuple(reasons)))
    assessments.sort(key=lambda a: (-a.scored.score, -a.scored.candidate.goal_priority,
                                    a.scored.candidate.goal_id, a.scored.candidate.game_id))
    qualified = [a for a in assessments if a.suitable]
    recommendations = tuple(a for a in qualified if qualified[0].scored.score - a.scored.score <= p.near_tie_margin)
    status = ("no_eligible" if not assessments else "no_good_fit" if not qualified else
              "multiple_equivalent" if len(recommendations) > 1 else "clear_recommendation")
    return replace(previous, ranked=tuple(assessments), recommendations=recommendations,
                   status=status, version=POLICY_VERSION)
