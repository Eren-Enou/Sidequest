# 005: Milestone 2 database and library API

Date: 2026-10-03 (America/Los_Angeles). Milestone: 2. Status: complete; ready for Milestone 3 review. Milestone 3 has not begun.

References: PROJECT.md, IMPLEMENTATION_PLAN.md, and [004: final scoring policy](004_milestone_1_final_policy.md). Production policy v0.1-final-004 is frozen and unchanged. Historical reports 001-004 remain unchanged.

## Scope and outcome

Implemented FastAPI, synchronous SQLAlchemy, SQLite connection configuration, request/response validation, the Game/Goal/PlaySession schema, an explicit initial migration, game/goal CRUD with soft archive, restoration, goal completion, and isolated persistence tests. No recommendation endpoint, session lifecycle endpoint, frontend, authentication, cloud service, Docker, generic repository framework, or migration autogeneration was implemented.

**All 315 tests passed, including all 239 Milestone 1 tests and 76 new database/library tests.** The library can be managed through real HTTP calls and retains data after the database and application are reopened. No scoring integration problem was found; no policy change was required.

## Architecture and files

A few modules are sufficient:

- app/database.py: file-path configuration, engine creation, per-connection foreign keys, explicit transaction control.
- app/models.py: three synchronous ORM mappings and UTC datetime conversion.
- app/schemas.py: validated create/patch/read schemas.
- app/routes.py: library routes, small record lookup/save helpers, one Session per request.
- app/main.py: application factory, startup schema verification, exception responses.
- app/migrate.py and migrations/001_initial.sql: explicit migration runner and authoritative initial DDL.
- tests/test_library_api.py: isolated API, schema, migration, persistence, and frozen-policy compatibility checks.
- requirements.txt: pinned tested runtime dependencies; requirements-dev.txt includes runtime dependencies and pytest/TestClient support.

Updated README.md with executable setup, configuration, migration, backup, endpoint, and test instructions. Updated IMPLEMENTATION_PLAN.md and the mutable reports index. PROJECT.md's product and scoring policy were not changed during this milestone.

The default file is backend/data/sidequest.sqlite3. SIDEQUEST_DB_PATH accepts an absolute path or a path relative to backend/, independent of working directory. Importing the app constructs an engine but does not connect to or initialize the personal database. Tests use explicit temporary paths. A startup connection to an unmigrated file fails with migration guidance rather than silently creating schema.

## Database schema

IDs are integer primary keys assigned by SQLite. Titles are required, trimmed by the API, and constrained to nonempty length <=200. Duplicate titles are permitted; IDs identify records. All timestamps supplied by the application are timezone-aware UTC. SQLite stores normalized UTC datetime values without offsets; ORM reads restore timezone awareness, preserving compatibility with the frozen scoring module.

### games

| Column | Type / nullability | Constraint / meaning |
| --- | --- | --- |
| id | INTEGER primary key | Stable identity |
| title | VARCHAR(200), required | Nonempty, <=200 characters |
| notes | TEXT, optional | Free text |
| current_interest | INTEGER, required, default 3 | Integer 1-5 |
| friction | INTEGER, required, default 0 | Integer 0-5 |
| energy_required | VARCHAR(6), required | low / medium / high |
| social_mode | VARCHAR(6), required | solo / social / both |
| experience_tags | JSON, required | Array of 1-4 recognized experience strings |
| archived_at | DATETIME, optional | Null means active |
| created_at | DATETIME, required | Server UTC creation time |
| updated_at | DATETIME, required | Server UTC modification time, >=created_at |

The API validates experience values, removes duplicate tags, and sorts them. SQL also validates array shape and each element's recognized string value; duplicate values can exist through direct SQL but are canonicalized at the API/domain boundary.

### goals

| Column | Type / nullability | Constraint / meaning |
| --- | --- | --- |
| id | INTEGER primary key | Stable identity |
| game_id | INTEGER, required | Foreign key games.id, deletion restricted |
| title | VARCHAR(200), required | Nonempty, <=200 characters |
| notes | TEXT, optional | Free text |
| estimated_minutes | INTEGER, required | Positive session-chunk estimate |
| priority | INTEGER, required, default 2 | Integer 1-3 |
| status | VARCHAR(9), required, default active | active / completed / archived |
| created_at | DATETIME, required | Server UTC creation time |
| updated_at | DATETIME, required | >=created_at |
| completed_at | DATETIME, optional | Required when completed; null while active; may remain when archived |

Foreign key ensures every goal has a game. A unique (id, game_id) parent key supports the session composite foreign key. game_id is immutable through PATCH, preventing library edits from moving historical goal relationships. Completed_at cannot precede created_at. Index: goals.game_id.

### play_sessions (schema foundation only)

| Column | Type / nullability | Constraint / meaning |
| --- | --- | --- |
| id | INTEGER primary key | Stable identity |
| game_id | INTEGER, required | Foreign key games.id, deletion restricted |
| goal_id | INTEGER, required | Composite foreign key (goal_id, game_id) -> goals(id, game_id) |
| game_title_snapshot | VARCHAR(200), required | Nonempty title at session creation |
| goal_title_snapshot | VARCHAR(200), required | Nonempty title at session creation |
| started_at | DATETIME, required | UTC start |
| finished_at | DATETIME, optional | Null while active; cannot precede start |
| actual_duration_minutes | INTEGER, optional while active | Positive integer when finished |
| enjoyment_rating | INTEGER, optional while active | Integer 1-5 when finished |
| progress | TEXT, optional while active | Nonempty when finished |
| notes | TEXT, optional | Free text |
| situation_snapshot | JSON, required | JSON object for future validated context snapshot |
| recommendation_snapshot | JSON, required | JSON object for future validated frozen-policy explanation |

The composite foreign key rejects a session linking a goal to the wrong game. Direct deletion of referenced games/goals is restricted. Active rows require null completion fields; finished rows require duration, rating, and nonempty progress. A partial unique index on constant 1 WHERE finished_at IS NULL ensures at most one active row. Indexes cover game/finished time and goal ID. These are schema protections for planned behavior, not implemented session lifecycle operations.

Snapshot payload contents are not yet application-validated beyond JSON-object shape. Milestone 4 will validate those contents and expose start/finish/history operations. Milestone 2 inserts sessions only in tests to verify schema/history relationships and persistence.

### schema_migrations

version INTEGER primary key, name TEXT unique/required, checksum TEXT required, applied_at TEXT required in UTC. This ledger is maintained by the explicit migration runner, not mapped as a user domain object.

## Relationships and foreign-key enforcement

Game -> many Goals -> many PlaySessions. A session also records its Game through a direct restricted foreign key; the composite goal/game key ensures both references agree. ORM relationships expose Game.goals, Goal.game, Goal.play_sessions, and PlaySession.goal.

Each new SQLite connection enables PRAGMA foreign_keys=ON and verifies it is active. Tests dispose/recreate connections and verify enforcement, missing-parent rejection, mismatched goal/game rejection, and restricted deletes. Foreign keys are a connection-level setting: external SQLite tools must enable them independently.

SQLite's driver legacy transaction behavior is disabled. SQLAlchemy emits explicit BEGIN for ordinary transactions and BEGIN IMMEDIATE for migration upgrades. DDL and the migration ledger therefore roll back together, including when an upgrade fails midway. Reads and writes use synchronous Sessions; no background jobs or async database layer exists.

## API routes

| Method | Path | Result |
| --- | --- | --- |
| POST | /api/games | Create; 201 with GameRead |
| GET | /api/games | List by ascending ID; include_archived option |
| GET | /api/games/{game_id} | Retrieve, including archived |
| PATCH | /api/games/{game_id} | Edit library metadata; GameRead |
| DELETE | /api/games/{game_id} | Idempotent archive; 204 |
| POST | /api/games/{game_id}/restore | Restore; GameRead |
| POST | /api/goals | Create for an existing active game; 201 with GoalRead |
| GET | /api/goals | List by ascending ID; game_id/status/include_archived filters |
| GET | /api/goals/{goal_id} | Retrieve, including archived/completed |
| PATCH | /api/goals/{goal_id} | Edit title/notes/estimate/priority; GoalRead |
| DELETE | /api/goals/{goal_id} | Idempotent archive; 204 |
| POST | /api/goals/{goal_id}/complete | Explicit, idempotent completion; GoalRead |
| POST | /api/goals/{goal_id}/restore | Restore/reopen as active and clear completed_at; GoalRead |

There are 13 method/route operations over seven distinct OpenAPI paths. /docs and /openapi.json are FastAPI's interactive documentation, not product frontend screens.

Request/response behavior:

- Unknown fields rejected. Titles trimmed. Strict integer ratings/ranges and enums enforced. Positive stored IDs/estimates are capped at SQLite's signed 64-bit maximum to reject unsupported integers with 422 instead of overflow errors; scoring policy remains unchanged.
- PATCH changes only supplied fields. notes:null clears notes; other writable fields reject explicit null. Empty PATCH is a no-op. Status, timestamps, IDs, and game_id reassignment are not generic edits.
- Default lists hide archived games/goals and goals under archived games. Completed goals remain visible unless status-filtered. include_archived=true includes archived records; status=archived also requires that flag. Direct GET remains available for history references.
- Archiving a game does not rewrite child goal statuses. Goal archival retains its existing completed_at. Restoring/reopening a goal intentionally clears completion and requires an active parent. Metadata edits remain available for archived records.
- Creation/completion/restoration under an archived parent is rejected with 409 and restoration guidance. No hard-delete endpoint exists.
- 422 validation, 404 missing records, 409 state/constraint conflicts, 503 busy SQLite writer. Requests use one transaction/session and close/roll back on failure. The API does not expose raw database error details.

## Migration approach

Run from backend/: `python -m app.migrate` (or --database PATH). Default migration file: migrations/001_initial.sql. No metadata.create_all or automatic startup migration is used.

The runner checks contiguous numbered SQL files, locks the writer with BEGIN IMMEDIATE, validates applied version/name/content history, applies pending statements, and records each revision in the same transaction. SHA-256 hashes use UTF-8 text with newline normalization so CRLF versus LF does not cause spurious drift. Reapplying current migrations is a no-op. Unknown future versions, changed historical migration contents, gaps, and unversioned nonempty databases are rejected.

Failed upgrades roll back both DDL and ledger entries. Tests cover failure on an initially empty database and failure after revision 001. API startup requires all known migrations and expected tables. This is intentionally a small forward-only SQL runner: no Alembic, downgrade framework, autogeneration, or separate schema-management infrastructure. New schema changes must add a new migration file.

Applied migrations are immutable like reports. Stop the API and copy the local SQLite file before changing schema; restoring a backup must use compatible migration history. Startup history checks do not detect every possible out-of-band manual schema edit.

## Compatibility with the frozen scoring engine

All candidate inputs have persisted sources: Game IDs/titles/current_interest/friction/energy/social/tags/archive time; Goal IDs/titles/estimated_minutes/priority/status; latest completed PlaySession.finished_at per game for recency. API-managed fields are independent of the scorer's domain types. No recommendation route, scorer adapter service, or recommendation database table was added.

A test creates records, stores a completed session, reopens the SQLite engine, builds a plain Candidate using every relevant field, and calls the unchanged pure scorer. Its policy remains v0.1-final-004. This establishes type/UTC compatibility without implementing Milestone 3.

## Test suite and smoke verification

Command: `.venv/Scripts/python.exe -m pytest -q` from backend/.

```text
315 passed in 8.85s
```

Exit code 0, no warnings in the final run. All 239 existing Milestone 1 tests passed without modifying their files; 76 new tests passed. `python -m pip check` reported no broken requirements.

New tests cover creation/defaults, retrieval/list ordering/filtering, all writable fields and partial edits, null handling, enum/title/range/SQLite-integer validation, missing records, relationship immutability, archive/restore/completion idempotency, parent archive semantics, database-level checks, connection-level foreign keys, same-game session constraints, snapshot preservation after edits/archives, UTC offset normalization and naive-time rejection, reopen persistence, one-active-session schema protection, initial/idempotent migration, CRLF portability, unknown/future history refusal, and transactional DDL rollback.

Every API/persistence test creates a unique file under pytest's temporary directory and runs the same explicit migration path. No test creates or modifies backend/data/sidequest.sqlite3; backend/data/ still contains only .gitkeep after verification.

A separate real HTTP smoke check used a temporary database and a hidden local Uvicorn process. It ran the migration command twice, validated startup/OpenAPI, created a game and goal, edited priority, completed the goal, archived the game, and retrieved archived data. All HTTP assertions passed. The smoke process was terminated. Initial temporary-file cleanup hit a Windows file-sharing error; a later cleanup command was rejected by automatic approval with 'blocked by policy'. Temporary smoke files remain outside the repository at C:/Users/Aaron/AppData/Local/Temp/sidequest_m2_smoke_7yja08sz. This cleanup limitation does not affect application behavior or passing tests.

The first targeted API test run showed an upstream Starlette warning about its legacy httpx test backend. The development dependency was changed to the installed Starlette-supported httpx2 package; the final suite is warning-free. Runtime dependencies are pinned to tested versions; httpx2 is test-only, not application infrastructure.

## Decisions, deviations, and known limitations

- Chose a versioned SQL runner rather than Alembic; the plan required an explicit migration mechanism but left its choice open. This is within scope and sufficient for the small local schema.
- Added restore/reopen operations so archives are reversible. DELETE means archive, consistent with preserving history.
- Kept game_id immutable on goal edits to preserve historical references. Moving a goal to another game is not implemented.
- Added same-game and single-active-session schema constraints now, since the PlaySession table is part of this milestone; actual lifecycle routes remain deferred.
- JSON snapshot shape is checked, but full nested context/explanation validation belongs to future session writes. No session request/response schemas or API were prematurely added.
- No pagination, full-text search, unique-title policy, concurrent-user support, CORS policy, or deployment setup. Lists suit a personal library. SQLite writer conflicts return retry guidance; there is no retry queue.
- UTCDateTime is a small SQLite-specific value adapter, not a new data-access abstraction. Migration SQL is authoritative; ORM metadata.create_all must not be used as schema management.
- Schema/API validation cannot infer whether estimates or subjective interest/friction accurately reflect the user. Scoring weights and heuristics remain frozen.

## Readiness for Milestone 3

Milestone 2 acceptance criteria are satisfied: the library is manageable through API calls, all fields needed for scoring persist, constraints and relationships are enforced, and data survives reopening. Milestone 3 can load games/goals and completed-session recency and invoke the frozen engine using an explicit evaluation timestamp. Its result must preserve the four statuses, suitability-only acceptance, factor explanations, and near-equivalent choices already specified in PROJECT.md.

No Milestone 3 endpoint or work was started. No scoring integration problem required policy modification. The user can review the documented library API before authorizing the next milestone.

## Provenance, versions, and preservation

| Package | Tested version |
| --- | --- |
| fastapi | 0.142.2 |
| pydantic | 2.13.5 |
| SQLAlchemy | 2.0.54 |
| uvicorn | 0.54.0 |
| starlette | 1.7.0 |
| pytest | 8.4.2 |
| httpx2 | 2.13.1 |

Python: 3.12.6. SQLite: 3.45.3.

Frozen scoring.py SHA-256 (unchanged): `b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a`.
Initial migration normalized-content SHA-256: `85be3aa48097821482a7358a93b5e3a576770feed6eadad05060bf0bc1c1ffc8`.

Historical report hashes, unchanged:

- `001_milestone_1_engine_evaluation.md`: `321498eabc0741db9eac22988981bbc3e7ec948035369c732f0c1777b7b299bb`.
- `002_scoring_policy_experiment.md`: `100799e3a6df1d49614a3321d84a5add048fcab5b6f327135ab3543d2596f7aa`.
- `003_duration_and_threshold_experiment.md`: `e6f32387a0c3e2fc412d808b237d9f22f02fab4cba10d2a50660de37c08ef390`.
- `004_milestone_1_final_policy.md`: `714ae26c0da3adef95bb24c4676ac95c2a3a013921042a3da70e5f3170f0ae4a`.

Report 005 is a new immutable historical record. Future repeats or corrections must use 006 or the next available number, reference this report, and update the mutable reports index.

## Documentation references

The connection-level foreign-key and explicit transaction configuration follows the [SQLAlchemy SQLite documentation](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html). SQLite explains the per-connection requirement in its [foreign-key documentation](https://www.sqlite.org/foreignkeys.html). Request validation uses the [Pydantic validator API](https://pydantic.dev/docs/validation/latest/concepts/validators/). Product behavior and test results above are observations of this implementation, not claims borrowed from those references.
