"""All-time descriptive aggregation over existing, immutable session evidence."""
from collections import Counter

from fastapi import HTTPException
from sqlalchemy import select

from app.models import PlaySession
from app.outcome_schemas import GameOutcomes

RECENT_LIMIT = 5
EXPERIENCES = ("progression", "chill", "challenge", "novelty")
ENERGIES = ("low", "medium", "high")


def rating_summary(ratings):
    counts = Counter(ratings)
    return {
        "completed_session_count": len(ratings),
        "average_enjoyment": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "rating_distribution": [{"rating": rating, "count": counts[rating]} for rating in range(1, 6)],
    }


def recorded_context(snapshot, field, allowed):
    value = snapshot.get(field) if isinstance(snapshot, dict) else None
    return value if isinstance(value, str) and value in allowed else None


def summarize_game(db, game_id):
    # One projection query, no lazy relationships or full recommendation snapshots.
    rows = db.execute(select(
        PlaySession.id, PlaySession.goal_title_snapshot, PlaySession.finished_at,
        PlaySession.enjoyment_rating, PlaySession.situation_snapshot,
    ).where(PlaySession.game_id == game_id, PlaySession.finished_at.is_not(None))
        .order_by(PlaySession.finished_at.desc(), PlaySession.id.desc())).all()
    ratings, recent = [], []
    experience_groups, energy_groups = {}, {}
    for row in rows:
        rating = row.enjoyment_rating
        if type(rating) is not int or not 1 <= rating <= 5:
            # Database constraints normally prevent this; never invent/drop ratings.
            raise HTTPException(409, "Completed session has invalid enjoyment data; insights unavailable")
        experience = recorded_context(row.situation_snapshot, "desired_experience", EXPERIENCES)
        energy = recorded_context(row.situation_snapshot, "energy", ENERGIES)
        ratings.append(rating)
        experience_groups.setdefault(experience, []).append(rating)
        energy_groups.setdefault(energy, []).append(rating)
        if len(recent) < RECENT_LIMIT:
            recent.append(dict(session_id=row.id, goal_title_snapshot=row.goal_title_snapshot,
                               finished_at=row.finished_at, enjoyment_rating=rating,
                               desired_experience=experience, energy=energy))
    return GameOutcomes(
        game_id=game_id, **rating_summary(ratings), recent_sessions=recent,
        by_desired_experience=[dict(desired_experience=value, **rating_summary(experience_groups[value]))
                               for value in (*EXPERIENCES, None) if value in experience_groups],
        by_energy=[dict(energy=value, **rating_summary(energy_groups[value]))
                   for value in (*ENERGIES, None) if value in energy_groups],
    )
