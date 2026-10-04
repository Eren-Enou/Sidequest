# Sidequest

A personal gaming session recommendation web application answering: **What should I play right now, and what should I accomplish during this session?**

## Current status

Milestones 1-3 are complete: the frozen production scoring policy `v0.1-final-004`, synchronous SQLite persistence, the FastAPI game/goal library API, and a read-only recommendation endpoint. Session lifecycle endpoints and React remain pending. Milestone 4 requires a separate instruction.

## Stack and layout

Python 3.12, FastAPI, Pydantic, synchronous SQLAlchemy, and SQLite are implemented. React/JavaScript/Vite remain planned.

```text
backend/
  app/          # Library API, database, schemas/models, migration runner, pure scoring
  migrations/   # Explicit numbered SQL migrations
  examples/     # Fictional scoring example
  experiments/  # Frozen baseline and historical comparison policies
  tests/        # Scoring, historical policy, library/API, persistence checks
  data/         # Local SQLite database, ignored by Git
frontend/src/   # Placeholder only
reports/        # Immutable numbered reports and mutable index
PROJECT.md
IMPLEMENTATION_PLAN.md
```

## Local backend setup

From the repository root in PowerShell:

```powershell
py -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
Set-Location backend
.venv/Scripts/python.exe -m app.migrate
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1
```

For a runtime-only installation use `requirements.txt`; `requirements-dev.txt` includes runtime dependencies plus pytest and the TestClient HTTP dependency. Tested direct versions are pinned. Interactive API documentation is at [localhost:8000/docs](http://127.0.0.1:8000/docs). There is no frontend server yet.

The default database is `backend/data/sidequest.sqlite3`, independent of the shell's working directory. Set `SIDEQUEST_DB_PATH` to use a different file. Relative configured paths are resolved against `backend/`:

```powershell
$env:SIDEQUEST_DB_PATH = 'data/my-library.sqlite3'
.venv/Scripts/python.exe -m app.migrate
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1
```

Alternatively migrate a named file using `python -m app.migrate --database PATH`; configure the API to use that same path. API startup checks the migration history and fails with setup guidance if migrations are missing or mismatched. It never auto-creates schema tables.

## Library API

| Method | Route | Behavior |
| --- | --- | --- |
| POST | /api/games | Create a game (201) |
| GET | /api/games | List games; `include_archived=true` includes archived records |
| GET | /api/games/{id} | Retrieve any game, including archived |
| PATCH | /api/games/{id} | Edit title, notes, interest, friction, energy, social mode, tags |
| DELETE | /api/games/{id} | Archive, preserving goals/history (204) |
| POST | /api/games/{id}/restore | Restore an archived game |
| POST | /api/goals | Create a goal linked to an existing active game (201) |
| GET | /api/goals | List; optional `game_id`, `status`, `include_archived` filters |
| GET | /api/goals/{id} | Retrieve any goal, including archived/completed |
| PATCH | /api/goals/{id} | Edit title, notes, estimated_minutes, priority |
| DELETE | /api/goals/{id} | Archive, preserving history (204) |
| POST | /api/goals/{id}/complete | Explicitly mark complete |
| POST | /api/goals/{id}/restore | Restore/reopen as active; clear completed_at |

Default goal lists exclude archived goals and goals of archived games; completed goals remain visible unless filtered. To query archived status, also pass `include_archived=true`. Archiving a game preserves each goal's status. Direct retrieval and metadata edits still work for archived records. Restore the parent game before creating/restoring/completing its goals. Repeated archive/restore/completion requests are idempotent for the existing state.

Titles are trimmed, experience tags are validated and canonicalized, integer ranges are strict, and unknown fields are rejected. PATCH omits unchanged fields; `notes: null` clears notes. Other writable fields cannot be explicitly null. Goal game_id is immutable after creation, preserving session relationships. Lifecycle fields and timestamps are server-owned. Validation errors return 422, missing records 404, relationship/state conflicts 409, and a busy SQLite writer 503. DELETE is always soft archive.

Example game body:

```json
{
  "title": "Moonlit Orchard",
  "current_interest": 4,
  "friction": 1,
  "energy_required": "low",
  "social_mode": "solo",
  "experience_tags": ["chill", "progression"]
}
```

Example goal body (use the created game's ID):

```json
{
  "game_id": 1,
  "title": "Harvest autumn crops",
  "estimated_minutes": 30,
  "priority": 2
}
```

## Recommendation API

`POST /api/recommendations` accepts:

```json
{"available_minutes":45,"energy":"low","social_preference":"solo","desired_experience":"progression"}
```

Minutes must be a positive integer. Energy accepts low/medium/high, social preference solo/social/either, and experience progression/chill/challenge/novelty. All four fields are required; unknown fields and invalid values return 422.

The response includes `status`, `engine_version`, UTC `evaluated_at`, echoed `context`, weights and heuristic thresholds, `winner`, `recommendations`, `ranked`, and `excluded`. Each scored item contains its candidate, score, suitability, suitability decision/reasons, complete breakdown, and factor inputs/weights/explanations. `ranked` includes every eligible candidate, including unsuitable audit entries; display choices come from `recommendations`. For near ties, `multiple_equivalent` retains a deterministic first choice without claiming a uniquely better winner. Both abstention outcomes have a null winner and empty recommendation choices.

With the example game and goal above and no completed history, the request returns `clear_recommendation`: Harvest autumn crops scores **84.25**, with suitability **60**. Contributions are interest 18.75, priority 7.5, time 10, energy 30, experience 20, friction -2, recency 0.

One query loads game/goal pairs and the latest completed session finish per game. Archived games and inactive goals are passed to the scorer for explicit exclusions; games without goals produce no candidate. Unfinished sessions do not affect recency. One backend timestamp is captured per evaluation. Requests never save a recommendation or modify library/history records. No schema migration is needed for Milestone 3.

## Migrations and local data

`python -m app.migrate` applies pending numbered SQL files in one explicit SQLite transaction under a writer lock. `schema_migrations` records version, filename, normalized-content SHA-256, and applied UTC time. Running again is a no-op. Applied migrations are immutable: add the next numbered SQL file rather than editing the initial migration. Foreign keys are enabled on every application/migration connection. The runner refuses unknown future history and unversioned nonempty databases.

This is a small forward-only runner, without autogeneration or downgrade commands. Stop the API and copy the SQLite file to back it up; restore a saved file only with compatible migration history. Personal databases are excluded from Git. Session tables exist for later milestones, but no session operations are exposed yet.

## Verification and scoring example

From `backend/`:

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m examples.recommendation
```

API tests migrate isolated temporary SQLite files and never use the personal database. Milestone 3 finished with 345 passing tests: all 315 previous tests and 30 new recommendation integration cases. The pure scoring module remains standard-library-only and unchanged. Its suitability gate, preference ranking, deterministic near ties, and four outcomes are documented in PROJECT.md and [report 004](reports/004_milestone_1_final_policy.md).

See [report 005](reports/005_milestone_2_database_library_api.md) for persistence decisions and [report 006](reports/006_milestone_3_recommendation_api.md) for recommendation integration and validation evidence. Historical investigations remain in numbered immutable reports; the reports index records later outcomes without rewriting earlier evidence.

## Future frontend setup

React and Vite have not been initialized. Later milestones will add `npm install`, `npm run dev`, and a development `/api` proxy. No Docker, authentication, cloud services, or deployment infrastructure are required for this local application.
