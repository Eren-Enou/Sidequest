"""Fictional progression comparisons; no persistence, network, or production wiring.

Run from backend: python -m experiments.progression_019
Planning labels are explicit authored facts, never inferred from titles/notes.
Every scoring calculation uses the unchanged production scorer.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json

from app.scoring import Candidate, SessionContext, recommend

NOW = datetime(2026, 10, 4, 19, tzinfo=timezone.utc)
MODELS = ("M0", "M1", "M2", "M3", "M4", "M5")


@dataclass(frozen=True)
class Plan:
    candidate: Candidate
    current: bool = True
    position: int = 1
    prerequisites: tuple[int, ...] = ()


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    goals: tuple[Plan, ...]
    context: SessionContext = SessionContext(60, "medium", "solo", "progression")


def goal(number, title, minutes=30, priority=2, *, current=True, position=1,
         prerequisites=(), status="active", game=1):
    return Plan(Candidate(game, number, "Fictional RPG" if game == 1 else "Fictional MMO",
                          title, minutes, "low", "solo", ("progression", "challenge"),
                          interest=4, goal_priority=priority, goal_status=status),
                current, position, prerequisites)


def scenarios():
    return (
        Scenario("A", "Linear RPG chapters", (
            goal(1, "Chapter 2", position=1),
            goal(2, "Chapter 3", priority=3, current=False, position=2, prerequisites=(1,)),
            goal(3, "Chapter 4", current=False, position=3, prerequisites=(2,)),
            goal(4, "Finish story", current=False, position=4, prerequisites=(3,)))),
        Scenario("B", "Parallel MMO goals", tuple(
            goal(i, title, position=i, game=2) for i, title in enumerate(
                ("Leveling", "Farm gold", "Practice PvP", "Train professions"), 1))),
        Scenario("C", "Repeatable practice", (goal(1, "Practice PvP", position=1),
            goal(2, "Explore new map", position=2))),
        Scenario("D", "One-shot final boss", (goal(1, "Defeat final boss", priority=3),)),
        Scenario("E", "Choose one faction", (goal(1, "Faction A campaign", position=1),
            goal(2, "Faction B campaign", position=2))),
        Scenario("F", "Main and optional objectives", (
            goal(1, "Main story", position=1), goal(2, "Companion quest", position=2),
            goal(3, "Optional dungeon", position=3))),
        Scenario("G", "Vague objective", (goal(1, "Improve gear"),)),
        Scenario("H", "Backlog game without goals", ()),
        Scenario("I", "All planned goals completed", (
            goal(1, "Chapter 2", status="completed"),
            goal(2, "Chapter 3", status="completed", position=2))),
        Scenario("J", "Change direction", (
            goal(1, "Reach level 40", priority=3, current=False, position=1, game=2),
            goal(2, "Craft equipment", position=2, game=2))),
        Scenario("K", "Same-game similar scores", (
            goal(1, "Story checkpoint", 30, position=1),
            goal(2, "Companion checkpoint", 45, position=2))),
        Scenario("L", "Partial progress leaves goal active", (goal(1, "Finish chapter 2"),)),
        Scenario("M", "Goal completed with time remaining", (
            goal(1, "Chapter 2", status="completed", position=1),
            goal(2, "Chapter 3", 20, current=False, position=2, prerequisites=(1,))),
            SessionContext(25, "medium", "solo", "progression")),
        Scenario("N", "Long current versus short later", (
            goal(1, "Current long encounter", 120),
            goal(2, "Later short task", 20, priority=3, current=False, position=2,
                 prerequisites=(1,))), SessionContext(30, "low", "solo", "progression")),
    )


def evaluate(scenario, model):
    """Compare eligibility concepts, not implemented persistence/UI models.

    M1 orders display only. M3 exposes the first active goal per game, skipping
    completed/archived; it models a queue head, not a tuned recommendation.
    M4 requires all named prerequisites completed; it has no XOR semantics.
    M5 keeps current eligibility unchanged; its proposed workflow is qualitative.
    """
    if model not in MODELS:
        raise ValueError("Unknown research model")
    by_id = {p.candidate.goal_id: p for p in scenario.goals}
    ordered = sorted(scenario.goals, key=lambda p: (p.position, p.candidate.goal_id))
    heads = {}
    for p in ordered:
        if p.candidate.goal_status == "active":
            heads.setdefault(p.candidate.game_id, p.candidate.goal_id)
    included, withheld = [], []
    for p in ordered:
        c = p.candidate
        reason = None
        if c.goal_status == "active":
            if model == "M2" and not p.current:
                reason = "Explicitly later"
            elif model == "M3" and heads[c.game_id] != c.goal_id:
                reason = "Not queue head"
            elif model == "M4" and not all(
                    by_id[i].candidate.goal_status == "completed" for i in p.prerequisites):
                reason = "Uncompleted prerequisite"
        if reason:
            withheld.append({"goal_id": c.goal_id, "reason": reason})
        else:
            included.append(c)
    result = recommend(included, scenario.context, evaluated_at=NOW)
    return {
        "model": model, "status": result.status,
        "choices": [r.candidate.goal_id for r in result.recommendations],
        "first_display_choice": result.winner.candidate.goal_id if result.winner else None,
        "withheld": withheld,
        "excluded": [{"goal_id": r.candidate.goal_id, "reasons": r.reasons} for r in result.excluded],
        "ranked": [{"goal_id": r.candidate.goal_id, "score": r.score,
                    "suitability": r.suitability, "breakdown": r.breakdown} for r in result.ranked],
    }


def complete(scenario, goal_id):
    """Hypothetical explicit completion only; never parse session progress."""
    return replace(scenario, goals=tuple(
        replace(p, candidate=replace(p.candidate, goal_status="completed"))
        if p.candidate.goal_id == goal_id else p for p in scenario.goals))


def main():
    rows = [{"key": s.key, "title": s.title, "context": vars(s.context),
             "goals": [{"candidate": vars(p.candidate), "current": p.current,
                        "position": p.position, "prerequisites": p.prerequisites} for p in s.goals],
             "results": [evaluate(s, m) for m in MODELS]} for s in scenarios()]
    print(json.dumps(rows, indent=2, default=str))


if __name__ == "__main__":
    main()
