# 012 — Deployment Step 1: portable database configuration

Date: 2026-10-03 (America/Los_Angeles)

Outcome: **Deployment Step 1 complete.** Local SQLite remains the default and all regression checks pass. PostgreSQL configuration is recognized, but PostgreSQL Sidequest schema/transactions and actual deployment remain unsupported. V0.1 remains the accepted product baseline; V0.2 is unstarted.

References: [010: accepted V0.1](010_v0.1_snapshot_validation_fix.md), [011: deployment investigation](011_deployment_architecture_investigation.md). These and reports 001–009 were preserved, including the previously uncommitted report 011.

## Scope and previous behavior

Reviewed PROJECT, implementation plan, README and reports 010/011 before implementation. Previously `make_engine(path=None)` always resolved a file against `backend/`, created its parent directory, built a `sqlite+pysqlite` engine with `check_same_thread=False` and timeout 5, and installed SQLite connection and transaction listeners. The default was `backend/data/sidequest.sqlite3`; an explicit file path took precedence over `SIDEQUEST_DB_PATH`. Application import constructs the engine; lifespan validates explicit migration history, without applying migrations automatically.

Only configuration/engine initialization and a non-SQLite schema guard were implemented. No schema/model, lifecycle, scoring, frontend, dependency or hosting changes were made.

## Configuration rules

| Inputs | Behavior |
| --- | --- |
| Neither environment variable present | Existing default SQLite path |
| `SIDEQUEST_DB_PATH` only | Existing relative/absolute path resolution |
| Explicit path without `DATABASE_URL` | Existing path override, including overriding `SIDEQUEST_DB_PATH` |
| `DATABASE_URL` only | SQLAlchemy URL parsing and dialect selection |
| Both environment variables present | Clear conflict naming the variables, without URL/credentials |
| `DATABASE_URL` plus explicit path | Clear conflict; no silent precedence |
| Empty/malformed `DATABASE_URL` | Error, never silently select the local library |

Presence controls conflict detection, including an explicitly empty `SIDEQUEST_DB_PATH`. The original no-URL path resolver is unchanged, including its existing treatment of path arguments/environment values.

`DatabaseConfiguration` is a small immutable value containing the parsed SQLAlchemy URL, dialect name and optional SQLite file path. Its representation omits the URL entirely because usernames/query parameters can contain secrets too. The resolver uses `make_url` and `URL.get_backend_name`, not URL string-prefix detection. No driver or connection is needed to inspect configuration.

Supported families:

- `sqlite` and `sqlite+pysqlite`: ordinary local file URLs; relative file paths resolve against backend root and use the same SQLite initialization path.
- `postgresql`, `postgresql+psycopg`, `postgresql+psycopg2`: recognized synchronous PostgreSQL configurations, passed as parsed URLs to external engine construction.

Other dialects, the legacy `postgres` alias, unknown/async drivers, SQLite URL in-memory mode and SQLite URI mode are rejected explicitly. This does not change the legacy path-based API or claim compatibility for untested databases. No connection URL or secret is included in introduced errors/logging. Parser/engine exception chaining is suppressed so a underlying exception message containing a credential is not displayed in an ordinary traceback.

## SQLite preserved and external behavior

SQLite parent-directory creation, connection arguments, isolation setup, foreign-key PRAGMA enforcement and explicit BEGIN/BEGIN IMMEDIATE listeners remain in `_sqlite_engine`. All migrations, migration history/checksum validation and SQLite lifecycle transactions are unchanged. File URL configuration uses that same implementation.

PostgreSQL takes a separate engine-construction branch with **no filesystem writes, SQLite connect arguments, PRAGMAs, or BEGIN listeners**. It passes the parsed URL directly to SQLAlchemy. No speculative pool sizes, retry scheme, TLS defaults, Vercel options or Neon endpoints are introduced; driver/TLS/pooling choices belong to Step 2.

**No dependencies added.** PostgreSQL engine construction still requires the selected synchronous driver to be installed; a missing driver or other external initialization error becomes a sanitized RuntimeError explaining that driver and Step 2 support are required. Driver-free tests inspect dialect configuration and replace only the engine factory to verify what the production branch passes. They do not demonstrate an operational PostgreSQL database.

Both `require_current_schema` and `upgrade` now reject non-SQLite engines **before connecting**, with a clear Deployment Step 2 prerequisite. This prevents running SQLite migration SQL on PostgreSQL or treating a coincidentally named schema as deployment-ready. Application lifespan disposes the external engine on this failure. Existing SQLite validation still runs normally.

Application import continues constructing an engine. In PostgreSQL mode that construction is lazy with respect to connecting, but still loads the driver and can fail at import if it is absent. Broad startup redesign was deliberately deferred. No user-facing PostgreSQL deployment instructions are supplied.

## Files changed

| File | Purpose |
| --- | --- |
| `backend/app/database.py` | Configuration value/resolver, explicit conflict/driver validation, separate external and SQLite initialization |
| `backend/app/migrate.py` | Non-SQLite guard before migration/schema connection |
| `backend/tests/test_database_configuration.py` | 30 focused, isolated configuration/engine/startup/CLI cases |
| `README.md` | Variables, conflict/URL restrictions, driver and PostgreSQL readiness limitations |
| `IMPLEMENTATION_PLAN.md` | Separate post-V0.1 deployment-enablement status |
| `reports/012_deployment_database_configuration.md` | This immutable evidence record |
| `reports/README.md` | Report 012 index entry; existing report 011 entry retained |

Report 011 and its index entry already existed in the working tree at task start. They were not recreated or rewritten. No commits or pushes were requested/performed.

## Tests and complete regression

The **30 new tests** cover default, relative/absolute environment paths and explicit overrides; PostgreSQL URL families; captured external factory arguments and absence of any event hooks/directory writes; environment and explicit-path conflicts; malformed/unsupported URL rejection; async and unsupported SQLite URL modes; SQLite foreign keys/isolation and both BEGIN forms; persisted SQLite writes; secret-safe repr/errors/log output; non-SQLite migration/startup rejection before connection; ordinary migrated SQLite startup/reopen; and subprocess SQLite migration CLI idempotence.

All paths/databases are isolated temporary locations. External factory tests use mock engines, and migration guards assert that connection methods are never called. No cloud, internet or PostgreSQL service is needed by tests. Existing tests were not edited or weakened. The complete backend invocation selected a temporary import-time default path so importing the module-level app could not open a personal database.

| Check | Command / method | Result |
| --- | --- | --- |
| Focused configuration tests | `.venv/Scripts/python.exe -m pytest tests/test_database_configuration.py -q` from backend | **30 passed**, 2.71s |
| Complete backend | `.venv/Scripts/python.exe -m pytest -q` from backend, temporary `SIDEQUEST_DB_PATH` for import | **466 passed**, 15.56s: all 436 existing + 30 new |
| Complete frontend | `npm.cmd test` from frontend | **51 passed**, 2 files, 11.67s |
| Production frontend build | `npm.cmd run build` from frontend | **Passed**, Vite 8.3.2; 26 modules; no frontend source change |
| Diff whitespace check | `git diff --check` | **Passed**; Git's Windows LF/CRLF notices are not whitespace failures |

## Manual isolated SQLite smoke

Ran an independent Python/TestClient smoke script using a `TemporaryDirectory` and `SIDEQUEST_DB_PATH`, with `DATABASE_URL` absent. It used fictional Moonlit Orchard / Plant the greenhouse data and 30-minute, low-energy, solo progression context.

Verified:

1. Explicit migrations apply and a repeated run is idempotent.
2. Ordinary configured application lifespan starts successfully.
3. Game and goal creation return 201.
4. Recommendation returns 200 with a clear recommendation.
5. Session start returns 201.
6. A fresh application instance recovers the persisted active session.
7. Finish returns 200 with duration 20, enjoyment 5, progress and notes.
8. Another reopen returns exactly the completed history row and no active session; library and recommendation snapshot remain intact.

**Passed the full loop.** No browser was needed; no personal Sidequest database was used.

## Frozen evidence verification

Before changing files, recorded SHA-256 hashes for reports 001–011, existing migration SQL and scorer. Compared those same files after implementation: **all match**.

`backend/app/scoring.py` SHA-256:

```text
b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a
```

The required hash matches exactly. Policy `v0.1-final-004`, reports 001–011, SQLite migration SQL and V0.1 domain/frontend behavior are preserved. No resources/accounts, secrets, cloud connections, deployment workflows, schema changes or data import were introduced. No cloud resources were touched.

## Deferred work and exact next deployment step

PostgreSQL is deliberately **not working Sidequest persistence yet**: no driver added, PostgreSQL DDL/migration stream, UTC/dialect integration, session serialization or PostgreSQL persistence tests. External engine construction alone does not remove those blockers. SQLite remains the normal local development/runtime configuration. Unknown dialects do not inherit SQLite assumptions.

Recommended next task, subject to review:

> Deployment Step 2 only: introduce a synchronous PostgreSQL driver, explicit PostgreSQL migrations separate from unchanged applied SQLite migrations, dialect-correct UTC/JSON/constraint behavior and transaction serialization preserving the existing start/finish/library contracts. Verify against an isolated PostgreSQL test database plus the complete SQLite regression, preserving frozen scoring and historical snapshots. Agree on a local test-database setup without assuming Docker or creating cloud resources. Do not deploy, connect to Neon, import personal data, build authentication, or begin V0.2.

Stop after Step 1. Step 2 remains unstarted.
