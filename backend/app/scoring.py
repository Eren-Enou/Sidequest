"""Deterministic scoring of active game/goal pairs using only the standard library.

Callers supply the evaluation clock and the last completed play time per game.
Scores are additive, unrounded points (not probabilities or percentages).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from typing import Iterable

ENGINE_VERSION = "v0.1-final-004"
ENERGY_LEVELS = {"low": 1, "medium": 2, "high": 3}
EXPERIENCES = frozenset({"progression", "chill", "challenge", "novelty"})
RATING_MIN = 1
RATING_MAX = 5
PRIORITY_MIN = 1
PRIORITY_MAX = 3
FRICTION_MAX = 5
RECENT_PLAY_WINDOW_DAYS = 7
SECONDS_PER_DAY = 86_400
ENERGY_MULTIPLIERS = (1, 0.5, 0)
PREFERRED_DURATION_START = Fraction(1, 2)
PREFERRED_DURATION_END = Fraction(9, 10)
FULL_WINDOW_TIME_FRACTION = Fraction(4, 5)
SUITABILITY_FACTORS = ("time_fit", "energy_fit", "experience_fit")
MINIMUM_SUITABILITY = 25  # Provisional heuristic, not calibrated confidence.
NEAR_TIE_MARGIN = 3  # Provisional presentation convention.


def _integer(name: str, value: int, minimum: int, maximum: int | None = None):
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        limit = f"{minimum}–{maximum}" if maximum is not None else f">= {minimum}"
        raise ValueError(f"{name} must be an integer {limit}")


def _choice(name: str, value: str, options):
    if not isinstance(value, str) or value not in options:
        raise ValueError(f"{name} must be one of {', '.join(sorted(options))}")


def _aware(name: str, value: datetime):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


@dataclass(frozen=True)
class ScoringWeights:
    interest: int = 25
    goal_priority: int = 15
    time_fit: int = 10
    energy_fit: int = 30
    experience_fit: int = 20
    friction: int = 10
    recent_play: int = 3

    def __post_init__(self):
        for name, value in vars(self).items():
            _integer(name, value, 0)


DEFAULT_WEIGHTS = ScoringWeights()


@dataclass(frozen=True)
class SessionContext:
    available_minutes: int
    energy: str
    social_preference: str
    desired_experience: str

    def __post_init__(self):
        _integer("available_minutes", self.available_minutes, 1)
        _choice("energy", self.energy, ENERGY_LEVELS)
        _choice("social_preference", self.social_preference, {"solo", "social", "either"})
        _choice("desired_experience", self.desired_experience, EXPERIENCES)


@dataclass(frozen=True)
class Candidate:
    game_id: int
    goal_id: int
    game_title: str
    goal_title: str
    estimated_minutes: int
    energy_required: str
    social_mode: str
    experience_tags: tuple[str, ...]
    interest: int = 3
    goal_priority: int = 2
    friction: int = 0
    last_completed_session_at: datetime | None = None
    game_archived: bool = False
    goal_status: str = "active"

    def __post_init__(self):
        for name in ("game_id", "goal_id", "estimated_minutes"):
            _integer(name, getattr(self, name), 1)
        for name in ("game_title", "goal_title"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be nonempty text")
        _choice("energy_required", self.energy_required, ENERGY_LEVELS)
        _choice("social_mode", self.social_mode, {"solo", "social", "both"})
        _choice("goal_status", self.goal_status, {"active", "completed", "archived"})
        if type(self.game_archived) is not bool:
            raise ValueError("game_archived must be a boolean")
        if not isinstance(self.experience_tags, (tuple, list)) or not self.experience_tags:
            raise ValueError("experience_tags must be a nonempty list or tuple")
        for tag in self.experience_tags:
            _choice("experience tag", tag, EXPERIENCES)
        object.__setattr__(self, "experience_tags", tuple(sorted(set(self.experience_tags))))
        _integer("interest", self.interest, RATING_MIN, RATING_MAX)
        _integer("goal_priority", self.goal_priority, PRIORITY_MIN, PRIORITY_MAX)
        _integer("friction", self.friction, 0, FRICTION_MAX)
        if self.last_completed_session_at is not None:
            _aware("last_completed_session_at", self.last_completed_session_at)


@dataclass(frozen=True)
class Factor:
    name: str
    points: float
    weight: int
    inputs: tuple[tuple[str, object], ...]
    reason: str


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: Candidate
    factors: tuple[Factor, ...]

    @property
    def breakdown(self) -> dict[str, float]:
        return {factor.name: factor.points for factor in self.factors}

    @property
    def score(self) -> float:
        return sum(self.breakdown.values())

    @property
    def suitability(self) -> float:
        return sum(self.breakdown[name] for name in SUITABILITY_FACTORS)

    @property
    def suitable(self) -> bool:
        return self.suitability >= MINIMUM_SUITABILITY

    @property
    def unsuitable_reasons(self) -> tuple[str, ...]:
        return () if self.suitable else (
            f"Situational suitability {self.suitability} is below {MINIMUM_SUITABILITY}.",)


@dataclass(frozen=True)
class ExcludedCandidate:
    candidate: Candidate
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RecommendationResult:
    ranked: tuple[ScoredCandidate, ...]
    excluded: tuple[ExcludedCandidate, ...]
    evaluated_at: datetime
    weights: ScoringWeights
    recommendations: tuple[ScoredCandidate, ...]
    status: str
    minimum_suitability: int = MINIMUM_SUITABILITY
    near_tie_margin: int = NEAR_TIE_MARGIN
    engine_version: str = ENGINE_VERSION

    @property
    def winner(self) -> ScoredCandidate | None:
        """First display choice; multiple_equivalent has no uniquely better winner."""
        return self.recommendations[0] if self.recommendations else None


def time_fit_fraction(estimated_minutes: int, available_minutes: int) -> Fraction:
    """Continuous utilization ramp, comfort plateau, and gradual buffer deduction."""
    _integer("estimated_minutes", estimated_minutes, 1)
    _integer("available_minutes", available_minutes, 1)
    if estimated_minutes > available_minutes:
        raise ValueError("Estimated minutes exceed the available window")
    ratio = Fraction(estimated_minutes, available_minutes)
    if ratio < PREFERRED_DURATION_START:
        return ratio / PREFERRED_DURATION_START
    if ratio <= PREFERRED_DURATION_END:
        return Fraction(1)
    return 1 - (1 - FULL_WINDOW_TIME_FRACTION) * (
        ratio - PREFERRED_DURATION_END) / (1 - PREFERRED_DURATION_END)


def _exclusions(candidate: Candidate, context: SessionContext) -> tuple[str, ...]:
    reasons = []
    if candidate.game_archived:
        reasons.append("Game is archived; restore it to recommend this goal.")
    if candidate.goal_status != "active":
        reasons.append(f"Goal is {candidate.goal_status}; only active goals are eligible.")
    if candidate.estimated_minutes > context.available_minutes:
        reasons.append(f"Needs {candidate.estimated_minutes} minutes; only {context.available_minutes} available.")
    if (context.social_preference != "either" and candidate.social_mode != "both"
            and candidate.social_mode != context.social_preference):
        reasons.append(f"Activity is {candidate.social_mode}-only; preference is {context.social_preference}.")
    return tuple(reasons)


def _score(candidate: Candidate, context: SessionContext, evaluated_at: datetime,
           weights: ScoringWeights) -> ScoredCandidate:
    factors = []

    def add(name, fraction, reason, **inputs):
        weight = getattr(weights, name)
        factors.append(Factor(name, weight * fraction, weight, tuple(inputs.items()), reason))

    add("interest", (candidate.interest - RATING_MIN) / (RATING_MAX - RATING_MIN),
        "Higher current interest earns more points.", interest=candidate.interest)
    add("goal_priority", (candidate.goal_priority - PRIORITY_MIN) / (PRIORITY_MAX - PRIORITY_MIN),
        "Higher goal priority earns more points.", priority=candidate.goal_priority)
    # Compute the weighted rational term before conversion, matching Experiment 003.
    time_fraction = time_fit_fraction(candidate.estimated_minutes, context.available_minutes)
    factors.append(Factor("time_fit", float(weights.time_fit * time_fraction), weights.time_fit,
                          (("estimated_minutes", candidate.estimated_minutes),
                           ("available_minutes", context.available_minutes),
                           ("preferred_start", float(PREFERRED_DURATION_START)),
                           ("preferred_end", float(PREFERRED_DURATION_END)),
                           ("full_window_fraction", float(FULL_WINDOW_TIME_FRACTION))),
                          "Ramp to half the session, full points from 50% to 90%, gradual decline at full time."))
    energy_gap = max(0, ENERGY_LEVELS[candidate.energy_required] - ENERGY_LEVELS[context.energy])
    add("energy_fit", ENERGY_MULTIPLIERS[energy_gap],
        "Full points when energy is sufficient; half for one level above, zero for two.",
        required=candidate.energy_required, available=context.energy, gap=energy_gap)
    add("experience_fit", int(context.desired_experience in candidate.experience_tags),
        "Full points for a matching experience tag; otherwise zero.",
        desired=context.desired_experience, tags=candidate.experience_tags)
    add("friction", -candidate.friction / FRICTION_MAX,
        "Higher setup or coordination friction subtracts more points.", friction=candidate.friction)
    days_since_play = None
    if candidate.last_completed_session_at is not None:
        elapsed = evaluated_at - candidate.last_completed_session_at.astimezone(timezone.utc)
        days_since_play = max(0, elapsed.total_seconds() / SECONDS_PER_DAY)
    penalty_fraction = 0 if days_since_play is None else max(0, 1 - days_since_play / RECENT_PLAY_WINDOW_DAYS)
    add("recent_play", -penalty_fraction,
        "Recent play penalty fades linearly to zero over seven days; never played has no penalty.",
        last_completed_session_at=candidate.last_completed_session_at,
        days_since_play=days_since_play, window_days=RECENT_PLAY_WINDOW_DAYS)
    return ScoredCandidate(candidate, tuple(factors))


def recommend(candidates: Iterable[Candidate], context: SessionContext, *,
              evaluated_at: datetime, weights: ScoringWeights = DEFAULT_WEIGHTS) -> RecommendationResult:
    """Rank by raw score descending, priority descending, goal ID then game ID ascending.

    Duplicate goal IDs are invalid. Input ordering never affects output. Future last-play
    timestamps are treated as just played. No implicit current-time lookup is performed.
    """
    _aware("evaluated_at", evaluated_at)
    evaluated_at = evaluated_at.astimezone(timezone.utc)
    ranked, excluded = [], []
    seen = set()
    for candidate in candidates:
        if candidate.goal_id in seen:
            raise ValueError(f"Duplicate goal_id: {candidate.goal_id}")
        seen.add(candidate.goal_id)
        reasons = _exclusions(candidate, context)
        if reasons:
            excluded.append(ExcludedCandidate(candidate, reasons))
        else:
            ranked.append(_score(candidate, context, evaluated_at, weights))
    ranked.sort(key=lambda item: (-item.score, -item.candidate.goal_priority,
                                  item.candidate.goal_id, item.candidate.game_id))
    excluded.sort(key=lambda item: (item.candidate.goal_id, item.candidate.game_id))
    suitable = [item for item in ranked if item.suitable]
    recommendations = tuple(item for item in suitable
                            if suitable[0].score - item.score <= NEAR_TIE_MARGIN)
    status = ("no_eligible" if not ranked else "no_good_fit" if not suitable else
              "multiple_equivalent" if len(recommendations) > 1 else "clear_recommendation")
    return RecommendationResult(tuple(ranked), tuple(excluded), evaluated_at, weights,
                                recommendations, status)
