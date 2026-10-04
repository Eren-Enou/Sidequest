"""Add 12 fictional games / 36 goals through the API of an ISOLATED smoke database.

Usage: python frontend/scripts/seed_smoke_library.py http://127.0.0.1:8016
Creates new records on every run; never run against your personal library.
No product code, database shortcuts, or scoring calculations are used.
"""

import json
import sys
from urllib.request import Request, urlopen


def seed(base_url):
    def request(method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        with urlopen(Request(base_url + path, data=data, method=method,
                             headers={"Content-Type": "application/json"})) as response:
            raw = response.read()
            return json.loads(raw) if raw else None

    # Title, energy, play style, interest, effort, experiences, session chunks.
    games = [
        ("Quiet Harbor", "low", "solo", 4, 0, ["chill", "progression"], [10, 25, 45]),
        ("Cloud Garden", "low", "both", 4, 0, ["chill", "progression"], [15, 30, 45]),
        ("Iron Summit", "high", "solo", 5, 2, ["challenge", "progression"], [20, 45, 90]),
        ("Rift Patrol", "high", "social", 5, 5, ["challenge"], [30, 60, 120]),
        ("Lantern Roads", "medium", "solo", 3, 1, ["novelty", "progression"], [15, 35, 70]),
        ("Moss & Mirrors", "low", "solo", 2, 0, ["novelty", "chill"], [5, 20, 40]),
        ("Star Cartographers", "medium", "both", 4, 3, ["novelty", "challenge"], [20, 50, 100]),
        ("Cozy Caravan", "low", "social", 3, 4, ["chill"], [10, 30, 60]),
        ("Ember Circuit", "high", "both", 4, 1, ["challenge"], [10, 25, 60]),
        ("Clockwork Isles", "medium", "solo", 1, 2, ["progression"], [15, 45, 90]),
        ("Ancient Tides", "medium", "both", 5, 3, ["progression", "novelty"], [20, 40, 80]),
        ("Winter Vault", "high", "social", 2, 5, ["challenge"], [30, 60, 120]),
    ]
    for index, (title, energy, social, interest, effort, tags, chunks) in enumerate(games):
        game = request("POST", "/api/games", {
            "title": title, "energy_required": energy, "social_mode": social,
            "current_interest": interest, "friction": effort, "experience_tags": tags,
            "notes": "Fictional Milestone 6 smoke data",
        })
        for number, minutes in enumerate(chunks):
            goal = request("POST", "/api/goals", {
                "game_id": game["id"], "title": ["Try a short objective", "Advance the next chapter", "Work toward a major milestone"][number],
                "estimated_minutes": minutes, "priority": [1, 3, 2][number],
            })
            if number == 2 and index in (2, 5, 8):
                request("POST", f'/api/goals/{goal["id"]}/complete')
            elif number == 0 and index in (3, 6, 9):
                request("DELETE", f'/api/goals/{goal["id"]}')
        if index in (10, 11):
            request("DELETE", f'/api/games/{game["id"]}')
    print("Created 12 games (2 archived), 36 goals (3 completed, 3 archived).")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    seed(sys.argv[1].rstrip("/"))
