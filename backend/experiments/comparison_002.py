"""Print side-by-side JSON; never write or overwrite historical reports."""

from dataclasses import asdict
import json

from app.scoring import SessionContext
from experiments.baseline_001 import recommend as baseline
from examples.evaluation_001 import SCENARIOS, Scenario, candidate, EVALUATED_AT
from experiments.policy_002 import recommend as proposed

ADDITIONAL = (
    Scenario("Energy mismatch favorite still possible", SessionContext(30, "low", "solo", "progression"), (
        candidate(1, "Iron Summit", "Train the new combat skill", 30, "high", ["progression"], 5, 3, 0, 7),
        candidate(2, "Moonlit Orchard", "Grow a basic crop", 30, "low", ["progression"], 1, 1, 0, 7),
    ), "", ""),
    Scenario("Time buffer band boundary", SessionContext(30, "medium", "solo", "progression"), (
        candidate(1, "Forest Foundry", "Build the workshop", 28, "medium", ["progression"], 4, 2, 0, 7),
        candidate(2, "Harbor Builder", "Build the dock", 27, "medium", ["progression"], 4, 2, 0, 7),
    ), "", ""),
    Scenario("Very short goal in a long window", SessionContext(120, "low", "solo", "chill"), (
        candidate(1, "Moonlit Orchard", "Water one plant", 1, "low", ["chill"], 4, 2, 0, 7),
        candidate(2, "Quiet Cartographer", "Map the whole forest", 90, "low", ["chill"], 4, 2, 0, 7),
    ), "", ""),
    Scenario("Recent-play ordering with equal interest", SessionContext(30, "low", "solo", "chill"), (
        candidate(1, "Moonlit Orchard", "Harvest the orchard", 30, "low", ["chill"], 4, 2, 0, 0),
        candidate(2, "Quiet Cartographer", "Map the orchard trail", 30, "low", ["chill"], 4, 2, 0, 7),
    ), "", ""),
    Scenario("Total threshold across priority step", SessionContext(30, "low", "solo", "challenge"), (
        candidate(1, "Moonlit Orchard", "Complete a peaceful chore", 30, "low", ["chill"], 1, 2, 0, 7),
        candidate(2, "Quiet Cartographer", "Finish the peaceful atlas", 30, "low", ["chill"], 1, 3, 0, 7),
    ), "", ""),
    Scenario("Suitability gate rejects a high-total mismatch", SessionContext(30, "low", "solo", "chill"), (
        candidate(1, "Iron Summit", "Fight the boss again", 30, "high", ["challenge"], 5, 3, 0, 7),
    ), "", ""),
)
ALL_SCENARIOS = SCENARIOS + ADDITIONAL


def compare():
    comparisons = []
    for s in ALL_SCENARIOS:
        b = baseline(s.candidates, s.context, evaluated_at=EVALUATED_AT)
        p = proposed(s.candidates, s.context, evaluated_at=EVALUATED_AT)
        assert b.excluded == p.excluded
        assert p == proposed(reversed(s.candidates), s.context, evaluated_at=EVALUATED_AT)
        assert p == proposed(s.candidates, s.context, evaluated_at=EVALUATED_AT)
        assert all(a.scored.score == sum(a.scored.breakdown.values()) for a in p.ranked)
        comparisons.append((s, b, p))
    return tuple(comparisons)


if __name__ == "__main__":
    print(json.dumps([{"scenario": asdict(s), "baseline": asdict(b), "proposed": asdict(p)}
                      for s, b, p in compare()], indent=2, default=str))
