# Sidequest

A personal gaming session recommendation web application answering: **What should I play right now, and what should I accomplish during this session?**

## Current status

**Sidequest V0.1 is complete.** All six milestones and all nine acceptance criteria are satisfied: library management, deterministic explained recommendations, session start/recovery/finish, and preserved History work through the local browser interface. Report 009's acceptance blocker was repaired with a narrowly bounded snapshot numerical-consistency check; scoring policy `v0.1-final-004` remains byte-for-byte frozen. See [report 010](reports/010_v0.1_snapshot_validation_fix.md) for final regression, browser, and acceptance evidence.

## Session outcome insights

In **Library**, select a game and choose **Show outcome insights**. The read-only
panel shows all completed-session counts, the 1–5 enjoyment distribution, counted
averages, the five most recent outcomes, and recorded experience/energy breakdowns.
Archived games retain their evidence. **Refresh outcome insights** reloads it.

`GET /api/games/{game_id}/outcomes` owns these descriptive aggregates. Active
sessions are excluded. No history yields a null average and an explicit empty
state. Insights do not affect recommendation scoring or ordering.

Finishing a session now requires an explicit enjoyment selection. Older rating-3
records remain included because deliberate selections cannot be distinguished from
the former default. No migration is needed. See [report 018](reports/018_session_outcome_insights.md).

## Stack and layout

Python 3.12, FastAPI, Pydantic, synchronous SQLAlchemy, SQLite, React/JavaScript, and Vite are implemented.

```text
backend/
  app/          # Library API, database, schemas/models, migration runner, pure scoring
  migrations/   # Explicit numbered SQL migrations
  examples/     # Fictional scoring example
  experiments/  # Frozen baseline and historical comparison policies
  tests/        # Scoring, historical policy, library/API, persistence checks
  data/         # Local SQLite database, ignored by Git
frontend/
  src/          # App shell, API access, views, forms, components, frontend tests
  scripts/      # API-only fictional library seeder for isolated smoke databases
  package.json  # React/Vite and test commands; locked dependencies
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

For a runtime-only installation use `requirements.txt`; `requirements-dev.txt` includes runtime dependencies plus pytest and the TestClient HTTP dependency. Tested direct versions are pinned. Interactive API documentation is at [localhost:8000/docs](http://127.0.0.1:8000/docs). Run the frontend in a second terminal as described below.

The default database is `backend/data/sidequest.sqlite3`, independent of the shell's working directory. Set `SIDEQUEST_DB_PATH` to use a different file. Relative configured paths are resolved against `backend/`:

```powershell
$env:SIDEQUEST_DB_PATH = 'data/my-library.sqlite3'
.venv/Scripts/python.exe -m app.migrate
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1
```

Alternatively migrate a named file using `python -m app.migrate --database PATH`; configure the API to use that same path. API startup checks the migration history and fails with setup guidance if migrations are missing or mismatched. It never auto-creates schema tables.

### Portable database configuration (Deployment Steps 1–2)

Local SQLite remains the normal/default configuration. With `DATABASE_URL` absent,
the default path, `SIDEQUEST_DB_PATH`, and explicit `--database PATH` behavior are
unchanged. PostgreSQL persistence is also supported and verified against a real
isolated PostgreSQL 16.3 cluster; no cloud deployment exists.

| Configuration | Result |
| --- | --- |
| Neither environment variable set | SQLite at `backend/data/sidequest.sqlite3` |
| Only `SIDEQUEST_DB_PATH` set | SQLite at that path; relative paths use `backend/` |
| Only `DATABASE_URL` set | Parse a SQLAlchemy URL and select its dialect |
| Both variables present, even if empty | Fail with a configuration conflict |
| `DATABASE_URL` plus an explicit SQLite path argument | Fail with a configuration conflict |

An explicitly present empty or malformed `DATABASE_URL` is an error, not fallback
to local SQLite. Configuration errors do not include the URL or its credentials.
Supported URL families are synchronous `sqlite`/`sqlite+pysqlite` file URLs and
`postgresql`/`postgresql+psycopg`/`postgresql+psycopg2`. The legacy `postgres` alias,
other dialects, async drivers, in-memory SQLite URLs and SQLite URI mode are
rejected. Relative SQLite URL file paths also resolve against `backend/`.

SQLite continues creating the parent directory, enforcing foreign keys and using
the existing explicit BEGIN/BEGIN IMMEDIATE hooks. PostgreSQL uses pinned
`psycopg[binary]==3.3.6`; a bare `postgresql://` URL selects Psycopg 3, as does
`postgresql+psycopg://`. Explicit `postgresql+psycopg2://` recognition is retained
for compatibility, but that optional driver is not installed or verified here.

Configure `DATABASE_URL` privately in your shell/environment, with
`SIDEQUEST_DB_PATH` unset. From `backend/`, run `python -m app.migrate` explicitly
before starting the API. The command selects `migrations/postgresql/` for
PostgreSQL and the original `migrations/` for SQLite. Startup validates current
checksummed history; it never upgrades schema. PostgreSQL writes serialize with
a transaction-scoped application advisory lock and a database uniqueness
constraint protects the single active session. UTC timestamps and original JSON
snapshot numbers are preserved.

Keep connection credentials out of source control, logs, frontend variables and
shared shell transcripts. Connection/migration error messages omit connection
URLs. Configure appropriate TLS/query options privately for any future host;
host-specific pooling, packaging, authentication and deployment remain deferred.
See [report 013](reports/013_deployment_postgresql_compatibility.md) for evidence.

To run additional real PostgreSQL contracts, provide
`SIDEQUEST_TEST_POSTGRES_URL` privately, pointing only to an isolated loopback
PostgreSQL cluster with permission to create/drop disposable databases, then run
`python -m pytest -q` from `backend/`. Each PostgreSQL case creates a uniquely
named database and drops it afterward. Never point this setting at a personal or
shared server. With this variable absent, PostgreSQL cases skip explicitly;
ordinary SQLite checks still run. The test-only setting does not configure the
application database. No Docker, cloud resources, or personal data are required.

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

## Session lifecycle and history API

| Method | Route | Behavior |
| --- | --- | --- |
| POST | /api/sessions/start | Re-evaluate and start an accepted choice; 201 |
| GET | /api/sessions/active | Recover active session; 200 with JSON null if none |
| POST | /api/sessions/{id}/finish | Record completion and optionally complete the goal |
| GET | /api/sessions | Completed history, finish time descending then ID descending |
| GET | /api/sessions/{id} | Retrieve an active or completed session; 404 if missing |

Start body (use a game/goal pair in the current recommendation choices):

```json
{
  "game_id": 1,
  "goal_id": 1,
  "situation": {
    "available_minutes": 45,
    "energy": "low",
    "social_preference": "solo",
    "desired_experience": "progression"
  }
}
```

Start recalculates using current persisted data and one backend timestamp. Any choice in `recommendations` is accepted, including a near-equivalent non-winner. Missing records return 404; mismatched pairs, active-session conflicts, and stale/unrecommendable choices return 409. A stale-choice response includes the refreshed recommendation and guidance to request a new one. Client scores, snapshots, and timestamps are rejected.

Finish body:

```json
{
  "actual_duration_minutes": 30,
  "enjoyment_rating": 4,
  "progress": "Harvested crops and built the shed",
  "notes": "Save seeds for next time",
  "mark_goal_completed": false
}
```

Duration is a strict positive integer; enjoyment is 1-5; progress is required and trimmed to nonblank text. Notes are optional (omitted/null becomes null; an empty string is preserved). Goal completion defaults to false and is atomic with finish when requested. Already-finished sessions return 409, preserving the first result. Finish can record play after library archival; optional goal completion requires restoring archived game/goal records first. Impossible timestamp ordering returns 409; duration is user-confirmed and need not equal elapsed wall-clock minutes.

Responses preserve snapshot titles, timestamps, finish fields, `situation_snapshot`, and a versioned `recommendation_snapshot`: `{snapshot_version: 1, selected: <scored choice>, evaluation: <full recommendation response>}`. Full factor inputs, explanations, policy version, and alternatives are saved at start. History reads saved evidence without recomputing scores or consulting current titles. Snapshots have no edit endpoint.

SQLite `BEGIN IMMEDIATE` serializes lifecycle writers before validation; the existing partial unique index also enforces one active session. Active sessions and completed history survive restart. Finishing naturally updates later recommendation recency through the existing completed-session query. No new migration is needed.

## Migrations and local data

`python -m app.migrate` applies pending numbered SQL files in one explicit transaction under a dialect-specific writer lock. `schema_migrations` records version, filename, normalized-content SHA-256, and applied UTC time. Running again is a no-op. Applied migrations are immutable: add the next numbered SQL file rather than editing the initial migration. SQLite foreign keys are enabled on every application/migration connection; PostgreSQL enforces native foreign keys. The runner refuses unknown future history and unversioned nonempty databases.

This is a small forward-only runner, without autogeneration or downgrade commands. Stop the API and copy the SQLite file to back it up; restore a saved file only with compatible migration history. Personal databases are excluded from Git. Session operations use the existing PlaySession table and constraints.

## Verification and scoring example

From `backend/`:

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m examples.recommendation
```

API tests migrate isolated temporary SQLite files and never use the personal database. Milestone 4 finished with 410 passing tests: all 345 previous tests and 65 new session integration cases. The pure scoring module remains standard-library-only and unchanged. Its suitability gate, preference ranking, deterministic near ties, and four outcomes are documented in PROJECT.md and [report 004](reports/004_milestone_1_final_policy.md).

See [report 005](reports/005_milestone_2_database_library_api.md) for persistence decisions, [report 006](reports/006_milestone_3_recommendation_api.md) for recommendation integration, and [report 007](reports/007_milestone_4_session_lifecycle.md) for lifecycle contracts and validation evidence. Historical investigations remain in numbered immutable reports; the reports index records later outcomes without rewriting earlier evidence.

## Local frontend setup

Use a supported Node.js branch (20.19+, 22.13+, or 24+); tested with Node 24.13.0 and npm 11.6.2. From the repository root in a second PowerShell terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open [Sidequest at localhost:5173](http://127.0.0.1:5173). Vite binds to loopback and proxies `/api` to the backend at port 8000. The browser uses relative URLs. For a backend on another local port, set `$env:SIDEQUEST_API_TARGET = 'http://127.0.0.1:8015'` before running Vite. The development server uses a strict port to avoid silently moving to another URL.

**Library:** add a game with interest, getting-started effort, energy, play style, experiences, and notes; select it to add goals. “How hard is it to get started?” measures resistance to starting, not game difficulty, and preserves the API's six values 0–5. “Useful session length” is a rough worthwhile chunk of play on a goal, not total goal-completion time. Games can be edited, archived, or restored. Goals can be edited, completed/reopened, archived, or restored. Archived games can be shown using the shelf checkbox. Restore an archived parent before adding/reopening/completing its goals.

**Tonight:** describe time, energy, social preference, and desired experience. Results show the game/goal, score, suitability, and expandable factor calculations. Equivalent choices are presented together with a radio selection. Empty/poor-fit outcomes explain what to adjust. Starting sends the selected pair and evaluated situation to the backend for fresh validation. Conflicts offer a recommendation refresh. An active-session banner survives page reload and blocks duplicate starts.

**Active session:** starting opens the saved game/goal, start time, local elapsed timer, original situation, score, suitability, and expandable explanation. Reload recovers the backend record; select Active session to continue. Timer ticks never write to the database.

**Finish Sidequest:** confirm or edit suggested elapsed minutes, rate enjoyment 1–5, describe progress, and optionally add notes or mark the goal complete. The existing API handles atomic goal completion. Successful finish clears the active session and opens its History detail. A duplicate finish or lost write response triggers a read of the saved result; an unresolved conflict keeps the draft while the backend record remains active. Unsaved form drafts and selected screens do not survive reload.

**History:** browse date, snapshot titles, actual minutes, enjoyment, and progress; inspect notes, timestamps, original context, and saved score factors. Library edits/archives do not replace historical evidence. The next recommendation gets recency from completed backend sessions. There is no frontend scoring or recency calculation. Other-tab changes may require reload.

Snapshot validation accepts insignificant floating-point representation differences using relative and absolute tolerances of `1e-12`, while checking every ranked candidate and retaining all exact stored values. Material score/breakdown discrepancies and nonfinite totals are rejected. This integration repair changes neither scoring nor historical evidence; report 009 preserves the original failed investigation.

Frontend verification from `frontend/`:

```powershell
npm test
npm run build
npm run preview
```

Milestone 6 verification: **51 frontend tests passed** (26 preserved + 25 added), all **410 backend tests passed**, and the production build passed. An actual browser completed creation → recommendation → start → reload/recovery → finish → history → recency feedback, then confirmed snapshot preservation after renaming/archiving. A 13-game / 37-goal library exposed the session-start blocker. See [report 009](reports/009_milestone_6_v0.1_completion.md); historical Milestone 5 evidence remains in [report 008](reports/008_milestone_5_react_library_recommendation.md).

Final acceptance repair: **436 backend tests passed** (410 existing + 26 new), **51 frontend tests passed**, and the production build passed. The previously failing two-candidate browser scenario now starts, survives reload, finishes, and appears in History with unmodified scores. Additional start/finish flows passed with the Milestone 6 fictional dataset (14 games / 38 goals including the two reproduction pairs). All nine PROJECT acceptance criteria are satisfied; reports 001–009 remain unchanged. See [report 010](reports/010_v0.1_snapshot_validation_fix.md).

To repeat the larger-library observation, explicitly migrate a new temporary database, run the API against that file and a distinct loopback port, and point Vite's proxy at that port. Then, from the repository root:

```powershell
backend/.venv/Scripts/python.exe frontend/scripts/seed_smoke_library.py http://127.0.0.1:8016
```

This adds 12 fictional games and 36 goals through the library API, including archived/completed records. Each run adds new records. Use an isolated database, never the personal library. The report records the two situation inputs and the additional game/goal created in the browser.

`npm run preview` is a local build check, not deployment infrastructure; it inherits the same local API proxy. Production hosting is deferred; any eventual host must serve `/api` on the same origin. No Docker, authentication, cloud services, or deployment configuration is required for this local application.

## Production packaging (Deployment Step 3)

No deployment exists. The repository-root `vercel.json` describes one Vercel
project using current Services configuration: `backend/` is a FastAPI service
and `frontend/` is a Vite/static service. These are hosting build boundaries,
not new application microservices. The project root must remain the repository
root. `/api` and `/api/*` route exclusively to the backend with their original
paths; other requests reach frontend static delivery. Existing assets take
precedence over the frontend SPA fallback. Missing assets return 404 rather
than HTML. React currently switches screens without changing the browser path;
`/` is its actual navigation URL. The fallback supports future direct frontend
paths and explicitly excludes API and asset prefixes.

The production ASGI entrypoint is `backend/index.py` (`index:app` relative to
that service root). It imports the canonical `app.main.app`, creates no second
application, and requires PostgreSQL before importing the application so missing
configuration cannot create a local SQLite directory. `backend/.python-version`
selects Python 3.12. Existing `backend/requirements.txt` remains the production
manifest; there is no root copy. SQL resources are included explicitly and
remain resolved from source paths, independent of working directory. Development
files, local databases and environment files are excluded from upload/bundling.

Frontend installation/build remain `npm ci` and `npm run build`, with `dist`
relative to `frontend/` as the static output. FastAPI does not serve React files.
The browser continues using relative `/api` calls; no CORS was added. Ordinary
local Uvicorn and Vite proxy commands above are unchanged and require no Vercel
CLI. `app.main:app` continues to support local SQLite; `index:app` is specifically
the production PostgreSQL entrypoint.

Eventually configure application/backend-consumed `DATABASE_URL` privately, with
`SIDEQUEST_DB_PATH` absent. Set `SIDEQUEST_POSTGRES_POOL=null` for the production
runtime to avoid retaining idle connections across process freezes/reuse.
Absent this setting, local PostgreSQL keeps its original QueuePool; SQLite is
unaffected. No pool size or connection budget is claimed to fit all deployments.
For eventual Neon, use its pooled application URL with appropriate TLS options;
use a separate direct URL privately for controlled migration/maintenance actions.
Do not put either URL in Vite-prefixed variables or committed configuration.
Vercel environment settings can apply to builds as well as runtime; the adapter
may be inspected during framework builds and must have valid private configuration,
but importing it opens no database connection.

Before application traffic, from `backend/` with the maintenance database URL
set privately, run `python -m app.migrate` explicitly. Startup validates schema
only. Builds, requests and cold starts never apply migrations. Vercel does not
provide the ordinary persistent SSH release shell; use an explicitly controlled
owner-machine release action initially. Do not migrate from arbitrary preview
builds or connect previews to personal/production data.

Before any future deployment, separately verify Vercel owner-only All Deployments
protection for frontend, API, static access, production domains and generated URLs,
with no public exceptions or bypass links. Packaging does not configure this gate
or add application authentication. Services is currently beta; plan/account support,
actual Vercel routing/lifespan/bundles, hosted TLS and cold-start behavior must still
be verified during authorized staging. Local structural tests and Linux wheel
resolution are not an actual Vercel runtime test. See [report 014](reports/014_deployment_production_packaging.md).

## Security, transfer and recovery preparation (Deployment Step 4)

Read [DEPLOYMENT.md](DEPLOYMENT.md) before any hosted work. It defines owner-only
All Deployments protection, the bypass audit, private configuration, SQLite
transfer, dated logical backups, tested restore, disaster recovery and future
live acceptance checks. Current Vercel Services shares project environment
variables with builds: the database URL is consumed only by the backend and is
never a Vite/client variable, but service-level build isolation is not claimed.

Production `index:app` now also requires `SIDEQUEST_ALLOWED_ORIGINS`, an exact
comma-separated HTTPS origin allowlist. Unsafe requests require an allowed
Origin or, when absent, an allowed Referer. This is a narrow CSRF safeguard;
Vercel Authentication remains the access boundary. Local commands need no new
configuration when this variable is absent. Minimal response headers prevent
framing/MIME sniffing and referrer leakage; no CSP or CORS was introduced.

From `backend/`, the explicit maintenance entrypoint is
`python -m app.maintenance {transfer,backup,restore} --help` (select one command).
It requires a privately configured `SIDEQUEST_MAINTENANCE_DATABASE_URL` and never
falls back to the runtime URL. Transfer needs a read-only SQLite source and an
already-migrated empty PostgreSQL destination; use `--dry-run` first. A full dump
restore instead needs a completely empty, **unmigrated** PostgreSQL destination.
Backups require pg_dump/pg_restore and an existing directory outside this repo.
See the runbook for exact commands and precautions; do not use personal data
without separate authorization.

Step 4 verification: **598 backend passed, two intentional skips**, including
the existing 33 PostgreSQL cases and 15 new real PostgreSQL maintenance cases;
**51 frontend passed**, production build and private-sentinel artifact scan
passed. The real PostgreSQL 16.3 dump/restore round trip recovered the fictional
library, history, snapshots and active session, then supported new writes and
session completion. See [report 015](reports/015_deployment_security_backup_preparation.md).
No cloud resources, deployment or personal-data transfer occurred.
