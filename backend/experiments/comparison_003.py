"""Frozen Experiment 003 inputs; JSON replay prints results without writing reports."""

from dataclasses import asdict
import json

from app.scoring import SessionContext
from experiments.baseline_001 import recommend as baseline
from examples.evaluation_001 import EVALUATED_AT, Scenario, candidate
from experiments.comparison_002 import ALL_SCENARIOS
from experiments.policy_002 import recommend as policy_002
from experiments.policy_003 import recommend as policy_003, time_points, TIME_POLICY

APPROACHES = ("linear_plateau", "smooth_plateau", "bounded_parabola")
DURATION_MATRIX = {
    30: (1, 5, 10, 15, 20, 25, 27, 28, 29, 30, 31),
    60: (1, 5, 15, 30, 40, 45, 50, 55, 59, 60, 61),
    120: (1, 15, 30, 45, 60, 90, 100, 108, 115, 119, 120, 121),
}


def boundary_cases():
    cases = []
    for offset in (-1, 0, 1):
        # One minute / 1000 yields a 0.02 time-point change on the rising slope.
        cases.append(Scenario(f"Suitability boundary offset {offset}", SessionContext(1000, "low", "solo", "progression"), (
            candidate(1, "Iron Summit", "Practice the progression drill", 250 + offset, "high", ["progression"], 5, 3, 0, 7),
        ), "", ""))
        cases.append(Scenario(f"Total boundary offset {offset}", SessionContext(1000, "low", "solo", "challenge"), (
            candidate(1, "Moonlit Orchard", "Finish the harvest", 250 + offset, "low", ["chill"], 1, 3, 0, 7),
        ), "", ""))
        cases.append(Scenario(f"Near-tie boundary offset {offset}", SessionContext(1000, "low", "solo", "chill"), (
            candidate(1, "Moonlit Orchard", "Harvest the orchard", 500, "low", ["chill"], 5, 3, 0, 7),
            candidate(2, "Quiet Cartographer", "Map the orchard trail", 350 + offset, "low", ["chill"], 5, 3, 0, 7),
        ), "", ""))
    return tuple(cases)


BOUNDARY_CASES = boundary_cases()


def compare():
    rows = []
    for s in ALL_SCENARIOS + BOUNDARY_CASES:
        b = baseline(s.candidates, s.context, evaluated_at=EVALUATED_AT)
        p2 = policy_002(s.candidates, s.context, evaluated_at=EVALUATED_AT)
        p3 = policy_003(s.candidates, s.context, evaluated_at=EVALUATED_AT)
        assert b.excluded == p2.excluded == p3.excluded
        assert p3 == policy_003(reversed(s.candidates), s.context, evaluated_at=EVALUATED_AT)
        assert p3 == policy_003(s.candidates, s.context, evaluated_at=EVALUATED_AT)
        for a in p3.ranked:
            assert a.scored.score == sum(a.scored.breakdown.values())
            old = next(x for x in p2.ranked if x.scored.candidate == a.scored.candidate)
            assert tuple(f for f in a.scored.factors if f.name != "time_fit") == tuple(
                f for f in old.scored.factors if f.name != "time_fit")
        rows.append((s, b, p2, p3))
    return tuple(rows)


def duration_results():
    rows = []
    for available, estimates in DURATION_MATRIX.items():
        for estimate in estimates:
            c = candidate(1, "Duration Test", "Complete the session goal", estimate, "low", ["chill"], 4, 2, 0, 7)
            context = SessionContext(available, "low", "solo", "chill")
            results = [f([c], context, evaluated_at=EVALUATED_AT) for f in (baseline, policy_002, policy_003)]
            rows.append({"available": available, "estimate": estimate,
                         "eligible": bool(results[0].ranked),
                         "time_points": {name: time_points(estimate, available, name) if estimate <= available else None
                                         for name in APPROACHES},
                         "statuses": ["winner" if results[0].winner else "no_eligible", results[1].status, results[2].status]})
    return tuple(rows)


if __name__ == "__main__":
    print(json.dumps({"time_policy": asdict(TIME_POLICY), "durations": duration_results(),
                      "comparisons": [{"scenario": asdict(s), "baseline": asdict(b),
                                       "002": asdict(p2), "003": asdict(p3)}
                                      for s, b, p2, p3 in compare()]}, indent=2, default=str))
