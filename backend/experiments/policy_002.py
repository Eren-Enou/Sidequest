"""Experiment 002: explicit suitability gates plus additive preference ranking.

Uses baseline domain validation and eligibility only; baseline scores are not used.
All experimental formulas and decision thresholds are centralized here.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from app.scoring import Candidate, SessionContext, ScoredCandidate, Factor, ExcludedCandidate
from app.scoring import ENERGY_LEVELS, RATING_MIN, RATING_MAX, PRIORITY_MIN, PRIORITY_MAX
from app.scoring import FRICTION_MAX, SECONDS_PER_DAY
from experiments.baseline_001 import recommend as baseline_recommend

POLICY_VERSION = "experiment-002"


@dataclass(frozen=True)
class Policy:
    interest: int = 25
    goal_priority: int = 15
    energy_fit: int = 30
    experience_fit: int = 20
    time_fit: int = 10
    friction: int = 10
    recent_play: int = 3
    energy_multipliers: tuple[float, ...] = (1, 0.5, 0)
    comfortable_fraction: float = 0.9
    tight_time_multiplier: float = 0.8
    recency_days: int = 7
    minimum_suitability: int = 25
    minimum_total: int = 50
    near_tie_margin: int = 3


POLICY = Policy()


@dataclass(frozen=True)
class Assessment:
    scored: ScoredCandidate
    suitability: float
    unsuitable_reasons: tuple[str, ...]

    @property
    def suitable(self):
        return not self.unsuitable_reasons


@dataclass(frozen=True)
class Result:
    status: str
    ranked: tuple[Assessment, ...]
    recommendations: tuple[Assessment, ...]
    excluded: tuple[ExcludedCandidate, ...]
    evaluated_at: datetime
    policy: Policy = POLICY
    version: str = POLICY_VERSION

    @property
    def winner(self):
        """First display choice; multiple_equivalent means it is not a sole winner."""
        return self.recommendations[0] if self.recommendations else None


def recommend(candidates: Iterable[Candidate], context: SessionContext, *, evaluated_at: datetime) -> Result:
    # Delegation guarantees identical hard filters and clock/duplicate-ID validation.
    # Never change or override the production function or its default weights.
    baseline = baseline_recommend(candidates, context, evaluated_at=evaluated_at)
    p = POLICY
    assessments = []
    for eligible in baseline.ranked:
        c = eligible.candidate
        factors = []

        def add(name, fraction, reason, **inputs):
            weight = getattr(p, name)
            factors.append(Factor(name, fraction * weight, weight, tuple(inputs.items()), reason))

        add("interest", (c.interest - RATING_MIN) / (RATING_MAX - RATING_MIN),
            "Preference: current interest on the unchanged 1-5 scale.", interest=c.interest)
        add("goal_priority", (c.goal_priority - PRIORITY_MIN) / (PRIORITY_MAX - PRIORITY_MIN),
            "Preference: goal priority on the unchanged 1-3 scale.", priority=c.goal_priority)
        comfortable = c.estimated_minutes <= context.available_minutes * p.comfortable_fraction
        add("time_fit", 1 if comfortable else p.tight_time_multiplier,
            "Suitability: comfortable plateau; a small deduction inside the final 10% of the window.",
            estimated_minutes=c.estimated_minutes, available_minutes=context.available_minutes,
            comfortable_fraction=p.comfortable_fraction)
        gap = max(0, ENERGY_LEVELS[c.energy_required] - ENERGY_LEVELS[context.energy])
        add("energy_fit", p.energy_multipliers[gap],
            "Suitability: sufficient energy earns 30, one-level shortfall 15, severe shortfall 0.",
            required=c.energy_required, available=context.energy, gap=gap)
        add("experience_fit", int(context.desired_experience in c.experience_tags),
            "Suitability: full points for a matching experience tag.", desired=context.desired_experience,
            tags=c.experience_tags)
        add("friction", -c.friction / FRICTION_MAX,
            "Unchanged setup/coordination friction penalty.", friction=c.friction)
        days = None if c.last_completed_session_at is None else max(
            0, (baseline.evaluated_at - c.last_completed_session_at).total_seconds() / SECONDS_PER_DAY)
        add("recent_play", 0 if days is None else -max(0, 1 - days / p.recency_days),
            "Weak variety nudge, not an inferred continuation signal.", days_since_play=days,
            window_days=p.recency_days)
        scored = ScoredCandidate(c, tuple(factors))
        suitability = sum(scored.breakdown[name] for name in ("time_fit", "energy_fit", "experience_fit"))
        reasons = []
        if suitability < p.minimum_suitability:
            reasons.append(f"Situational suitability {suitability} is below {p.minimum_suitability}.")
        if scored.score < p.minimum_total:
            reasons.append(f"Total score {scored.score} is below {p.minimum_total}.")
        assessments.append(Assessment(scored, suitability, tuple(reasons)))
    assessments.sort(key=lambda a: (-a.scored.score, -a.scored.candidate.goal_priority,
                                    a.scored.candidate.goal_id, a.scored.candidate.game_id))
    suitable = [a for a in assessments if a.suitable]
    recommendations = tuple(a for a in suitable if suitable[0].scored.score - a.scored.score <= p.near_tie_margin)
    status = ("no_eligible" if not assessments else "no_good_fit" if not suitable else
              "multiple_equivalent" if len(recommendations) > 1 else "clear_recommendation")
    return Result(status, tuple(assessments), recommendations, baseline.excluded, baseline.evaluated_at)
