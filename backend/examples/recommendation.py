"""Run from backend with: python -m examples.recommendation"""

import json
from datetime import datetime, timedelta, timezone

from app.scoring import Candidate, SessionContext, recommend


def sample():
    now = datetime(2026, 10, 3, 19, tzinfo=timezone.utc)
    context = SessionContext(45, "low", "solo", "chill")
    candidates = [
        Candidate(1, 1, "Moonlit Orchard", "Harvest autumn crops", 30, "low", "solo",
                  ("chill", "progression"), interest=5, friction=1,
                  last_completed_session_at=now - timedelta(days=7)),
        Candidate(2, 2, "Iron Summit", "Defeat the ridge guardian", 45, "high", "solo",
                  ("challenge", "progression"), interest=4, goal_priority=3, friction=2,
                  last_completed_session_at=now - timedelta(days=1)),
        Candidate(3, 3, "Starship Crew", "Complete a co-op expedition", 40, "medium", "social",
                  ("novelty", "progression"), interest=5, goal_priority=3),
        Candidate(4, 4, "Quiet Cartographer", "Map the lakeside trail", 20, "low", "solo",
                  ("chill", "novelty"), interest=4, goal_priority=1),
    ]
    return recommend(candidates, context, evaluated_at=now)


if __name__ == "__main__":
    result = sample()
    print(json.dumps({
        "engine_version": result.engine_version,
        "status": result.status,
        "recommendations": [item.candidate.game_title for item in result.recommendations],
        "ranked": [{"game": item.candidate.game_title, "goal": item.candidate.goal_title,
                    "score": item.score, "breakdown": item.breakdown,
                    "suitability": item.suitability, "suitable": item.suitable,
                    "unsuitable_reasons": item.unsuitable_reasons,
                    "explanations": [{"factor": f.name, "weight": f.weight,
                                      "inputs": dict(f.inputs), "reason": f.reason}
                                     for f in item.factors]} for item in result.ranked],
        "excluded": [{"game": item.candidate.game_title, "reasons": item.reasons}
                     for item in result.excluded],
    }, indent=2, default=str))
