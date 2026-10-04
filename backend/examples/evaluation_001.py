"""Frozen inputs for report 001. Print current results without writing any report.

Run from backend: python -m examples.evaluation_001
Future experiments should use new numbered fixtures and reports.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json

from app.scoring import Candidate, SessionContext
from experiments.baseline_001 import recommend

EVALUATED_AT = datetime(2026, 10, 3, 19, tzinfo=timezone.utc)


def candidate(number, game, goal, minutes, energy, tags, interest=3, priority=2,
              friction=0, days=None, mode="solo"):
    return Candidate(number, number, game, goal, minutes, energy, mode, tuple(tags),
                     interest, priority, friction,
                     None if days is None else EVALUATED_AT - timedelta(days=days))


@dataclass(frozen=True)
class Scenario:
    title: str
    context: SessionContext
    candidates: tuple[Candidate, ...]
    interpretation: str
    concern: str


SCENARIOS = (
    Scenario("Low energy + short session + progression", SessionContext(20, "low", "solo", "progression"), (
        candidate(1, "Moonlit Orchard", "Upgrade the watering can", 15, "low", ["progression", "chill"], 4, 2, 1, 7),
        candidate(2, "Iron Summit", "Clear the training arena", 20, "high", ["progression", "challenge"], 5, 3, 1, 7),
    ), "Iron Summit wins: +6.25 interest, +7.5 priority, and +3.75 time fit outweigh its -15 energy-fit disadvantage by 2.5 points.",
       "A high-energy activity can win in a low-energy context. Energy is soft, so this is policy behavior, not an eligibility bug."),
    Scenario("High energy + long session + challenge", SessionContext(120, "high", "solo", "challenge"), (
        candidate(1, "Iron Summit", "Conquer the summit boss", 120, "high", ["challenge"], 5, 3, 2, 7),
        candidate(2, "Clockwork Duel", "Complete a ranked ladder run", 60, "medium", ["challenge"], 4, 3, 0, 7),
        candidate(3, "Moonlit Orchard", "Expand the orchard", 90, "low", ["progression", "chill"], 5, 3, 0, 7),
    ), "Iron Summit beats Clockwork Duel by 9.75: +6.25 interest and +7.5 time fit offset -4 friction. It beats the orchard by 19.75, principally through the matching challenge tag.",
       "High energy gives all energy requirements full points. It does not itself favor demanding activities; challenge tags supply that preference."),
    Scenario("Strong interest in a poor situational fit", SessionContext(30, "low", "solo", "chill"), (
        candidate(1, "Iron Summit", "Practice a boss phase", 30, "high", ["challenge"], 5, 3, 0, 7),
        candidate(2, "Quiet Cartographer", "Sketch the lakeside trail", 20, "low", ["chill"], 2, 2, 0, 7),
    ), "Quiet Cartographer wins by 3.75. Its +15 energy and +20 experience advantages overcome -18.75 interest, -7.5 priority, and -5 time fit.",
       "A modest change in priority or recency could reverse this narrow win. Poor fit remains eligible if time and social mode fit."),
    Scenario("Lower interest with a perfect situational fit", SessionContext(30, "low", "solo", "chill"), (
        candidate(1, "Moonlit Orchard", "Finish the evening harvest", 30, "low", ["chill"], 2, 3, 0, 7),
        candidate(2, "Iron Summit", "Practice a boss phase", 30, "high", ["challenge"], 5, 3, 0, 7),
    ), "Moonlit Orchard wins by 16.25: its +35 combined energy/experience advantage exceeds the favorite's +18.75 interest advantage. Both fit the time window exactly.",
       "Perfect fit does not imply a score of 100: low interest still limits the score. Compare scenario 3 to see how the fitted candidate's priority and duration affect the margin."),
    Scenario("Two nearly identical candidates", SessionContext(30, "medium", "solo", "progression"), (
        candidate(1, "Harbor Builder", "Construct the west pier", 29, "medium", ["progression"], 4, 2, 0, 7),
        candidate(2, "Forest Foundry", "Construct the sawmill", 30, "medium", ["progression"], 4, 2, 0, 7),
    ), "Forest Foundry wins by 0.5, entirely from the extra estimated minute: 15 versus 14.5 time points. Lower ID does not override a higher score.",
       "One minute of estimation noise can determine the winner. There is no confidence band or near-tie treatment."),
    Scenario("Recently played favorite versus less-recent alternative", SessionContext(30, "low", "solo", "chill"), (
        candidate(1, "Moonlit Orchard", "Harvest the greenhouse", 30, "low", ["chill"], 5, 2, 0, 0),
        candidate(2, "Quiet Cartographer", "Map the old village", 30, "low", ["chill"], 4, 2, 0, 7),
    ), "Quiet Cartographer wins by 3.75. Avoiding the favorite's -10 recent-play penalty outweighs the favorite's +6.25 interest advantage.",
       "The engine discourages repeating a favorite even when repetition was enjoyable. Enjoyment and a desire to continue are not inputs."),
    Scenario("High-friction favorite versus low-friction alternative", SessionContext(30, "medium", "solo", "progression"), (
        candidate(1, "Starship Workshop", "Install the engine upgrade", 30, "medium", ["progression"], 5, 2, 5, 7),
        candidate(2, "Harbor Builder", "Upgrade the fishing dock", 30, "medium", ["progression"], 4, 2, 0, 7),
    ), "Harbor Builder wins by 3.75: avoiding -10 friction outweighs the favorite's +6.25 interest advantage.",
       "Friction is only a point penalty, not minutes. A 30-minute goal remains eligible in a 30-minute window even with maximum setup friction."),
    Scenario("Candidate excluded by available time", SessionContext(30, "high", "solo", "challenge"), (
        candidate(1, "Iron Summit", "Finish the full boss encounter", 31, "high", ["challenge"], 5, 3, 0, 7),
        candidate(2, "Clockwork Duel", "Play one ranked match", 30, "high", ["challenge"], 3, 2, 0, 7),
    ), "Clockwork Duel is the sole eligible candidate. The 31-minute favorite gets no score; interest and priority cannot override the time filter.",
       "The cutoff is abrupt at one minute beyond the window, while exact fits have no buffer for setup or overrun."),
    Scenario("Candidate excluded by solo/social requirements", SessionContext(45, "medium", "social", "progression"), (
        candidate(1, "Harbor Builder", "Upgrade the solo town", 45, "medium", ["progression"], 5, 3, 0, 7),
        candidate(2, "Starship Crew", "Complete a co-op expedition", 45, "medium", ["progression"], 4, 2, 1, 7, "social"),
        candidate(3, "Trail Partners", "Restore the shared campsite", 30, "low", ["progression"], 3, 2, 0, 7, "both"),
    ), "The solo-only town goal is excluded. Starship Crew beats Trail Partners by 9.25: +6.25 interest and +5 time fit offset -2 friction. Social-only and both receive identical social points.",
       "Social compatibility does not establish that friends are available. A both-mode game is not preferred over social-only. Explicit solo rejecting social-only is covered by the existing test matrix."),
    Scenario("Multiple conflicting factors", SessionContext(60, "medium", "either", "novelty"), (
        candidate(1, "Starship Crew", "Explore the new nebula", 60, "high", ["novelty", "challenge"], 5, 3, 4, 0, "social"),
        candidate(2, "Quiet Cartographer", "Explore the desert atlas", 40, "low", ["novelty", "chill"], 3, 2, 0, 7),
        candidate(3, "Harbor Builder", "Complete the harbor expansion", 60, "medium", ["progression"], 4, 3, 1, 3.5),
    ), "Quiet Cartographer wins by 0.5 over Starship Crew. Against the favorite it loses 12.5 interest, 7.5 priority, and 5 time points, but gains 7.5 energy, 8 friction, and 10 recency points. Harbor Builder loses mainly because it lacks novelty.",
       "A 0.5-point win is mathematically decisive but not strong evidence of better enjoyment. Either permits a social recommendation without any coordination readiness input."),
    Scenario("Supplement: exact tie and stable order", SessionContext(30, "low", "solo", "chill"), (
        candidate(2, "Quiet Cartographer", "Sketch the river bend", 30, "low", ["chill"], 4, 2, 0, 7),
        candidate(1, "Moonlit Orchard", "Harvest the river plot", 30, "low", ["chill"], 4, 2, 0, 7),
    ), "Both score 86.25 and have priority 2. Moonlit Orchard wins only because goal ID 1 precedes ID 2, despite being supplied second.",
       "An exact tie can systematically favor older IDs. The final game-ID key cannot resolve any additional tie because duplicate goal IDs are rejected."),
    Scenario("Supplement: negative-score eligible candidate", SessionContext(60, "low", "solo", "chill"), (
        candidate(1, "Iron Summit", "Do a one-minute combat drill", 1, "high", ["challenge"], 1, 1, 5, 0),
    ), "Iron Summit is the sole eligible candidate and wins with -9.75 points: 10 social + 0.25 time - 10 friction - 10 recency. There is no minimum-score gate.",
       "The engine will recommend an eligible activity despite low apparent suitability. The exact default lower bound is greater than -10, not -20 as the earlier PROJECT.md range suggests, because every eligible candidate earns +10 social points and a strictly positive time contribution."),
    Scenario("Supplement: no eligible candidate", SessionContext(15, "low", "solo", "chill"), (
        candidate(1, "Starship Crew", "Complete a co-op expedition", 30, "medium", ["progression"], 5, 3, 0, 7, "social"),
    ), "No winner is returned. The only candidate has both time and social exclusions; neither is relaxed.",
       "No best-effort fallback is provided. The future UI must make the exclusions actionable instead of presenting an unexplained empty result."),
)


def evaluate():
    results = []
    for scenario in SCENARIOS:
        result = recommend(scenario.candidates, scenario.context, evaluated_at=EVALUATED_AT)
        assert result == recommend(reversed(scenario.candidates), scenario.context, evaluated_at=EVALUATED_AT)
        assert result == recommend(scenario.candidates, scenario.context, evaluated_at=EVALUATED_AT)
        assert all(item.score == sum(item.breakdown.values()) for item in result.ranked)
        results.append(result)
    return tuple(results)


if __name__ == "__main__":
    print(json.dumps([{"scenario": s.title, "context": asdict(s.context),
                       "inputs": [asdict(c) for c in s.candidates],
                       "result": asdict(r)}
                      for s, r in zip(SCENARIOS, evaluate())], indent=2, default=str))
