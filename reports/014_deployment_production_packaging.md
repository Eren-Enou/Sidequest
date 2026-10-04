# Deployment Step 3: production packaging and Vercel runtime compatibility

Date/research date: 2026-10-03 (America/Los_Angeles).
Status: **COMPLETE for repository packaging and production-like local verification**.
No actual Vercel build or runtime was executed; no deployment exists.

## Scope and architectural confirmation

Reviewed PROJECT.md, IMPLEMENTATION_PLAN.md, README.md and reports 010–013.
Accepted V0.1, frozen scoring, snapshots, APIs and local SQLite remain the baseline.
This task adds production packaging, not authentication, cloud resources or V0.2.
Existing staged Step 1/2 work was retained without unstaging or committing it.

Current official documentation confirms the one-project, same-origin React/Python
shape. It now recommends Services for Python alongside another frontend framework,
rather than introducing new file-based /api functions. Services is beta and account
availability must be verified before deployment. This does not invalidate Report
011's architectural purpose; it refines its previously tentative packaging choice.
No provider change was found that requires abandoning the selected architecture.

## Current official findings and sources

Sources were retrieved on the research date; stale search snippets were not treated
as definitive when newer fetched documentation/changelog differed.

| Official source | Finding relevant to this package |
| --- | --- |
| [Python runtime](https://vercel.com/docs/functions/runtimes/python) | ASGI/WSGI framework support; requirements.txt discovery; supported entrypoint/app names; Python files are not automatically tree-shaken; combine frameworks with Services |
| [Python versions](https://vercel.com/docs/functions/runtimes/python/python-version) | Python 3.12 default, 3.13/3.14 supported; .python-version is accepted |
| [FastAPI guide](https://vercel.com/docs/frameworks/backend/fastapi) | Canonical app export; Fluid compute; lifespan startup supported; shutdown cleanup window is limited; function configuration keyed by entrypoint |
| [Services](https://vercel.com/docs/services) | Multiple framework roots in one project/domain; top-level protection applies across their public surface |
| [Service configuration](https://vercel.com/docs/services/config-reference) | root, framework, entrypoint, install/build commands, outputDirectory and function settings are supported |
| [Service routing](https://vercel.com/docs/services/routing) | First matching service rewrite wins; original path reaches service; its 404 never falls through to another service |
| [Service pricing/limits](https://vercel.com/docs/services/pricing) | Standard function compute limits apply; Hobby allowances are documented; no internal bindings are required here |
| [Rewrites](https://vercel.com/docs/routing/rewrites) and [static configuration](https://vercel.com/docs/project-configuration/vercel-json) | Native rewrites, regex sources, filesystem precedence, include/exclude globs; legacy builds and filesystem handles are unnecessary |
| [Function limits](https://vercel.com/docs/functions/limitations) | Fluid Hobby: 300-second duration, 2 GB memory; standard Python bundle 500 MB uncompressed; 4.5 MB request/response payload limit |
| [Build configuration](https://vercel.com/docs/builds/configure-a-build) | Root directory and framework build/output settings govern packaging |
| [Environment variables](https://vercel.com/docs/environment-variables) | Private environment settings scope build/runtime and deployment environments |
| [September 9 protection changelog](https://vercel.com/changelog/protect-production-deployments-for-free-on-every-plan) | All Deployments Vercel Authentication, including production, is now free on every plan |

Older January protection documentation/search results still described paid
production protection. The newer official September announcement supports Report
011's owner-only Hobby gate; actual account settings and anonymous-route behavior
remain later acceptance checks. No protection was enabled or bypass configured.

## Repository and build structure

Root vercel.json declares backend and frontend Services using their existing roots.
This is platform build/routing configuration, not new business-service abstractions.
It requires the eventual Vercel project root to be the repository root.

Backend has framework fastapi and entrypoint index:app. backend/index.py checks
PostgreSQL configuration before importing app.main.app and exports that exact
canonical object. There is no second FastAPI app, wrapper API, CORS change or route
rename. The normal local Uvicorn entrypoint remains app.main:app.

backend/.python-version selects 3.12. Dependency discovery uses existing
backend/requirements.txt; no duplicate root Python manifest, root package.json,
Dockerfile, custom system package install or deprecated builds configuration was
needed. Runtime requirements and their pins were unchanged.

Frontend has framework vite, installCommand npm ci, buildCommand npm run build,
and outputDirectory dist relative to frontend/. This runs the existing Vite build,
not the development server, with native static delivery. No FastAPI static mount
or duplicated build script was introduced. Local Vite proxy configuration and
frontend source remained unchanged.

## Public routing and SPA fallback

Top-level ^/api(?:/.*)?$ selects backend, including bare /api and unknown API paths.
All remaining paths select frontend. Services preserve the original /api prefix
and routing into the backend is final, so a missing endpoint returns the API's
404 rather than React HTML. There is no external origin or service-to-service binding.

Frontend-only fallback targets /index.html after filesystem lookup and excludes
api and assets prefixes explicitly. Actual built assets resolve normally, and
missing /assets files cannot be rewritten to HTML. React currently keeps Tonight,
Library, Active session and History in component state and does not change the
browser path; / is its actual route. Structural tests additionally probe /library,
/history/42 and /apiculture as possible direct frontend paths. These paths open
the app; they do not introduce new deep-link navigation behavior.

Regex selection tests are local structural checks, not Vercel routing emulation.
Actual platform routing remains a protected-staging check.

## Linux dependency and bundle evidence

All six direct runtime requirements and their resolved dependencies downloaded as
binary-only wheels targeting CPython 3.12, cp312 ABI, manylinux2014 x86_64.
The concrete driver wheel was:

psycopg_binary-3.3.6-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl

SQLAlchemy, greenlet and pydantic-core also resolved compatible Linux wheels;
other requirements were portable wheels. No compiler or PostgreSQL system package
is part of the design. Resolved wheel contents total **47,349,933 bytes uncompressed**,
comfortably below the standard Python limit before application/runtime overhead.
This is a dependency size estimate, not an actual Vercel function bundle measurement.
Transitive dependencies follow the existing resolver strategy; no new lock strategy
or version changes were introduced.

No usable Vercel CLI, Docker or Linux WSL installation was available. None was
installed/authenticated to simulate a deployment. Linux wheels were resolved and
inspected, not imported on Windows or executed under Vercel Linux.

## Database configuration and connection review

DATABASE_URL remains environment-driven and private; SIDEQUEST_DB_PATH must be
absent in production. The production adapter rejects missing or SQLite configuration
before app construction, preventing accidental durable-local-storage fallback.
Import creates only the canonical lazy engine and makes no connection. Framework
build introspection may import the adapter; private configuration must therefore
be available if it does, without putting credentials in frontend build variables.
No database URL is committed or hardcoded; no cloud connection was attempted.

Added opt-in SIDEQUEST_POSTGRES_POOL=null, selecting SQLAlchemy NullPool. Absent it,
local PostgreSQL retains its existing QueuePool; SQLite ignores this PostgreSQL-only
setting. Invalid profiles fail through a credential-safe error. Existing isolation,
transaction advisory locks, uniqueness constraints and lifecycle logic are unchanged.

A reused/frozen serverless process can retain stale idle QueuePool connections,
while per-process pools multiply idle connections across scaled instances. For this
small personal application, opening/closing connections with NullPool is a simple
opt-in correctness tradeoff. It avoids persistent idle sockets and the need for
pre-ping on retained connections; it does not impose a global active connection
budget. QueuePool with pre-ping and small limits is a possible later measured
alternative. Pre-ping cannot rescue a failed in-flight transaction, and no automatic
write retry or new sizing guesses were added. See [SQLAlchemy pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html).

Neon's [pooling guidance](https://neon.com/docs/connect/connection-pooling) (also
retrieved as its official Markdown resource) recommends pooled URLs for serverless
requests and direct URLs for migrations/maintenance. Its transaction pooling
limits session state and session-level locks. Sidequest uses transaction-scoped
locks and no request-level SET/session state, so the current design is compatible
in principle. Hosted PgBouncer/TLS/prepared-statement behavior is not locally proven.
Use provider-supplied TLS options privately; no TLS disabling was added.

## Filesystem and migration audit

The only application persistence-directory creation is inside _sqlite_engine.
Production mode uses PostgreSQL before reaching that branch. Games, goals, sessions
and snapshots write through SQLAlchemy to the database; no user files or generated
runtime artifacts are needed. Source SQL is read only, with backend paths derived
from __file__, not cwd. Python bytecode caches are optional interpreter artifacts,
not required durable application state. No temporary runtime storage was introduced.

Function includeFiles explicitly includes app/** and migrations/** under backend.
Function excludes remove development/tests/examples/experiments/local-data caches.
Root .vercelignore additionally excludes local environments, node_modules, Python
caches, environment files, databases, reports and Git metadata from source upload.
The migration streams themselves were not changed.

Migrations remain an explicit owner-controlled release step: from backend/, privately
configure a maintenance/direct URL and run python -m app.migrate before traffic.
Startup only validates schema; build commands, requests and cold starts do not upgrade
it. Vercel lacks the ordinary persistent release SSH shell, so owner-machine execution
is the initial proposed workflow. Do not attach production data to arbitrary previews.

## Production-like verification and tests

Added 17 packaging tests and two dialect-parameterized production-entrypoint
integration cases. One of the latter intentionally skips for SQLite.

The packaging fixture copies app, migration SQL and entrypoint into a temporary
service-root layout, runs a fresh Python process with -I from an unrelated directory,
removes inherited PYTHONPATH and disables optional bytecode writes. Imports of
FastAPI, SQLAlchemy, Pydantic, Psycopg and all backend modules succeed. The exported
object is identical to app.main.app. SQL files are found at absolute paths. A mkdir
failure guard confirms PostgreSQL construction does not require filesystem writes;
no SQLite files/data directory appear. Missing/SQLite production configurations
are rejected. Pool choices, secret-safe errors, routing separation, SPA boundaries,
manifest/build configuration and secret-free configuration are tested.

A real PostgreSQL packaging case uses an isolated migrated test database, seeds a
fictional game, imports the copied adapter using NullPool, executes lifespan/schema
validation and retrieves the record; /api/missing returns JSON 404. Existing real
PostgreSQL contracts were rerun without weakening their checks.

The actual Vite build's index.html references two existing emitted JS/CSS files.
Build output/configuration checks found no DATABASE_URL or PostgreSQL connection
string. An independent live local smoke started Uvicorn on isolated SQLite and
Vite with its existing proxy: / returned HTML, /api/games returned [] and an unknown
API path returned JSON. Both helper processes were stopped.

Current official JSON schema was retrieved. It contains an unrelated queue-trigger
metaschema defect (numeric exclusiveMinimum under its older schema declaration),
so generic metaschema prevalidation failed. Direct Draft7 instance validation of
our configuration against its applicable constraints passed without editing the
provider schema. A one-off validator was installed only into a temporary directory;
no project dependency was added. This does not claim Vercel build execution.

## Complete results and preservation

| Check | Actual result |
| --- | --- |
| Complete backend including real PostgreSQL | **547 passed, 2 skipped, 48.89s** (549 collected) |
| Prior baseline | All 529 passing cases remain passing; previous intentional skip retained |
| Added Step 3 cases | 18 passed, one SQLite production-only skip |
| Real PostgreSQL regression | **33 passed**, zero PostgreSQL skips; 32 preserved plus packaged-entrypoint case |
| Frontend | **51 passed**, two files |
| Production Vite build | Passed, 26 modules, expected dist/index.html and assets |
| Linux dependency resolution | All runtime dependencies resolved as compatible binary wheels |
| Packaging/configuration checks | Canonical import, cwd-independent SQL, no SQLite writes, separation and schema instance validation passed |
| Local SQLite/Vite proxy smoke | Passed |
| git diff --check | Passed |

All PostgreSQL databases were unique disposable test databases on a separate
loopback PostgreSQL 16.3 cluster; the existing server/personal database was untouched.
The temporary cluster was stopped after verification. No Vercel CLI or actual
Vercel Linux build/runtime was used. Early negative subprocess cases had malformed
newline escaping; the harness was corrected and all final checks pass.

Pre-task SHA-256 comparison preserves reports 001–013, both initial dialect migrations
and frozen scoring byte-for-byte. The scorer remains:

b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a

## Changed files and remaining boundaries

Created vercel.json, .vercelignore, backend/index.py, backend/.python-version,
backend/tests/test_production_packaging.py and this report. Changed .gitignore,
backend/app/database.py, backend/tests/test_persistence_contract.py, README.md,
IMPLEMENTATION_PLAN.md and reports/README.md. No runtime dependencies, frontend
source, scoring, domain schemas, migrations or historical reports changed.
No commit, push, resources, accounts, secrets, authentication or deployment was made.

Remaining deployment checks: Services beta availability on the actual Hobby account;
actual Linux function bundle/build/lifespan and route resolution; private environment
scoping and TLS/pooler operation; real cold-start latency and active connection budget;
owner-only gate on every URL/frontend/API/static surface; anonymous denial including
errors/unknown routes; preview data isolation; backup/restore and release migration
procedures. Function payload limits may constrain a much larger history library;
no pagination/product expansion was introduced.

**Step 3 is COMPLETE at the explicitly requested repository/local packaging level.**
Its acceptance does not assert a live working Vercel deployment. The researched
architecture is supported; no discrepancy required abandoning Report 011.

**Exact next recommended action:** authorize Deployment Step 4 only: prepare security
and backup acceptance procedures, locally test any required configuration/CSRF
safeguards and sample-data dump/restore, and define a fail-closed owner-only protection
checklist. Preserve V0.1 and historical evidence. Do not deploy, create Vercel/Neon
resources, load personal data, implement login without separate authorization, or
begin V0.2. Stop after Step 3 here.
