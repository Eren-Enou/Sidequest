# Deployment Step 2: PostgreSQL persistence compatibility

Date: 2026-10-03 (America/Los_Angeles). Status: **COMPLETE**.

## Scope and baseline

This adds persistence compatibility to accepted Sidequest V0.1, with SQLite still
the local default. Product behavior, routes, frontend, snapshot version, numerical
validation and scoring policy v0.1-final-004 remain unchanged. Reports 010–012
supply the accepted snapshot contract and preceding deployment decisions. This is
not V0.2, production packaging, authentication or deployment.

The starting suite contained 466 backend tests and 51 frontend tests. The previous
Step 1 working changes and uncommitted reports 011/012 were retained.

## Environment discovery and real evidence

Windows already had PostgreSQL 16.3 binaries and an existing running PostgreSQL
service. Rather than connect to that service or its databases, this task used
installed initdb/pg_ctl to create a separate temporary cluster. It listened only
on loopback on a separate port, with a dedicated temporary test role and no
personal data. Local trust authentication was limited to this disposable cluster;
it is not a proposed production authentication setting. No Docker installation
was needed. No Neon, Vercel or other cloud resources were contacted or created.

Every PostgreSQL integration case created a distinct UUID-named database, migrated
it explicitly, and dropped it with FORCE during cleanup. PostgreSQL's configured
server timezone was America/Los_Angeles; a focused connection also used
Pacific/Auckland. These are real database/driver operations, not PostgreSQL mocks
or SQLite substitutes. The temporary cluster was stopped after verification.

## Driver and connection configuration

Added one direct dependency: **psycopg[binary]==3.3.6**, pinned alongside existing
requirements. Psycopg 3 supports synchronous SQLAlchemy use; its binary package
avoids requiring a local compiler/libpq installation. This follows the
[official Psycopg installation guidance](https://www.psycopg.org/psycopg3/docs/basic/install.html).
The existing application remains synchronous. No async driver or separate pooling
library was added. The installed Windows wheel passed the real integration run;
Linux/serverless wheel and runtime packaging are still Step 3 responsibilities.

Bare postgresql URLs now select postgresql+psycopg. Explicit psycopg URLs also
work. Previously recognized explicit psycopg2 URLs remain recognized, but no
psycopg2 dependency or compatibility verification is claimed. READ COMMITTED is
explicit for PostgreSQL so reads after waiting for the write lock see committed
changes. SQLite configuration, path resolution, conflicts, foreign-key hooks and
BEGIN/BEGIN IMMEDIATE hooks remain intact.

URLs remain backend-only private environment values. Configuration/factory and
startup/CLI connection failures use generic messages without echoing connection
URLs; PostgreSQL SQLAlchemy parameter output is hidden. HTTP operational failures
return a generic 503 and integrity conflicts retain the existing 409. Test setup
failures omit connection details. No credentials or environment files were added
to source control. Appropriate hosted TLS/pooling settings are deferred.

## Explicit migration architecture

SQLite continues using backend/migrations/001_initial.sql without any byte change.
PostgreSQL has its own backend/migrations/postgresql/001_initial.sql. Both streams
start at 001, are forward-only, require contiguous numbering, and validate
filename/version/normalized-content SHA-256 against applied history. A PostgreSQL
script marker rejects cross-dialect stream selection before SQL is executed.

PostgreSQL schema_migrations records version, unique name, checksum, applied_at
TIMESTAMPTZ, and an explicitly constrained postgresql dialect. Its checksums are
separate from SQLite. Existing SQLite metadata format remains unchanged.

python -m app.migrate selects the configured dialect, obtains the appropriate
writer lock, applies trusted pending scripts and metadata in one transaction,
and reports the current migration number without connection details. PostgreSQL
scripts use Psycopg's complete-script execution, not SQLite's statement splitter.
Repeat application is a no-op. Unversioned nonempty databases, wrong streams,
future history and edited applied scripts are refused. A failed pending migration
rolls back DDL and metadata. No downgrade/autogeneration/create_all is introduced.

Startup only validates history and required tables. Fresh unmigrated databases
are rejected, and an actual TestClient startup after deleting history was rejected
without silently repopulating it. The CLI was exercised on each dialect and
returned Database at migration 001.

## Schema mapping and constraints

| Contract | PostgreSQL implementation |
| --- | --- |
| Game/Goal/PlaySession IDs and integer duration range | BIGINT identity keys and BIGINT FK/minute columns; ORM keeps SQLite Integer variants |
| Parent relationships | Native RESTRICT foreign keys; Goal UNIQUE(id, game_id); composite session FK prevents using another game's goal |
| Titles/values | Bounded VARCHAR, nonempty trimmed titles, interest/friction/priority/rating ranges, explicit energy/social/status checks |
| Time/state | TIMESTAMPTZ; update/completion/finish ordering; active vs finished required/null field checks |
| Experience tags | JSON array, 1–4 entries, each a recognized string experience |
| Snapshot payloads | Native JSON, NOT NULL and object-type checks |
| One active session | Unique constant-expression partial index WHERE finished_at IS NULL |
| Query indexes | Goal game ID, session game/finish time, session goal ID |

Native PostgreSQL types/check syntax differ from SQLite JSON1 and text timestamps,
while API validation and domain invariants remain equivalent. BIGINT prevents an
accidental reduction of SQLite's existing integer range; a 2**40 minute estimate
round-tripped through both APIs. Database snapshot checks enforce object shape;
the existing application snapshot validator remains responsible for full content.
No new schema columns or API fields were needed.

## Snapshot and UTC preservation

Native JSON (not JSONB) and existing SQLAlchemy/Python serialization preserve the
original evidence. The Report 009/010 fictional Iron Summit/Cloud Garden case
retained Cloud Garden score **70.41666666666666** and time_fit
**6.666666666666667**, including exact snapshot dictionary equality after raw ORM
readback, application reopen, finish and history. No rounding, recomputation,
version bump, audit-entry removal or normalization was introduced.

UTCDateTime now selects timezone-aware DateTime for PostgreSQL. It binds aware
UTC and converts returned offsets to UTC; it never strips the offset before
PostgreSQL binding. SQLite keeps its existing naive-UTC storage and aware-UTC
readback. Tests cover non-UTC server/connection timezone and an input with a
+09:30 offset, offset session clocks, history ordering, and completed-session
recency. The full loop verified the existing recent_play change from 0 to -3.

## Transaction/concurrency decision

For this single-owner application, one database-local, transaction-scoped advisory
lock is simpler than coordinating multiple rows, including the absent active
session row. Row locks alone would not protect the initial empty-active check.
Serializable isolation would require new retry behavior. The chosen stable
identity is the two-integer pair **(0x53494445, 1)**, obtained through
pg_advisory_xact_lock before any library mutation or lifecycle lookup/revalidation.
Migrations use the same identity. Reads and recommendation requests remain unlocked.

READ COMMITTED plus this lock ensures a waiting writer reads the latest committed
library state. All participating application writers acquire the lock first, and
commit/rollback releases it naturally, consistent with
[PostgreSQL transaction advisory lock semantics](https://www.postgresql.org/docs/16/explicit-locking.html#ADVISORY-LOCKS).
The unique active-session index independently protects inserts. This is limited
to a Sidequest database, not an external coordination system.

Real simultaneous starts produced one successful start and one conflict. Concurrent
finishes preserved the first saved result; repeated finish retained existing
conflict behavior. An injected UPDATE failure returned 409 and rolled back both
session finish and optional goal completion. A controlled library writer held the
lock while archiving a game: session start demonstrably waited, then read the
committed archive and returned 409 without inserting an active session. Stale
recommendation and near-equivalent selected-choice behavior also passed.

Arbitrary direct SQL writers that omit this advisory lock do not participate in
application serialization, although native constraints still enforce their own
invariants. This is an intentional small-application boundary.

## Tests and complete results

Added test_persistence_contract.py: **64 collected cases**, comprising 32 real
PostgreSQL cases and 32 SQLite counterparts; 63 passed and one SQLite case skipped
because it specifically observes PostgreSQL advisory locking. Selected established
library/session assertions are reused without rewriting the whole test suite.

Coverage includes fresh/repeated migration; missing/current schema validation;
actual explicit CLI; create/read/edit/archive/restore/complete library operations;
recommendations and completed-session recency; start/revalidate/near-equivalent
choice; recovery/reopen/finish/history; optional completion; injected rollback;
concurrent starts/finishes; library/lifecycle ordering; foreign/composite keys;
active uniqueness; title/tags/range/status/active-field/JSON constraints; UTC;
fractional evidence; large integer range; wrong migration streams, changed
checksums, corrupt history and failed-migration transactional rollback.

The 30 Step 1 configuration tests were updated where their intentional
PostgreSQL-unsupported assumptions no longer apply; their SQLite/configuration
coverage remains. The other 436 accepted V0.1 backend tests were unchanged.

| Verification | Actual final result |
| --- | --- |
| Complete backend with real PostgreSQL enabled | **529 passed, 1 skipped, 37.19s** (530 collected) |
| Real PostgreSQL subset within that run | **32 passed**, zero PostgreSQL skips/failures |
| Previous backend baseline | All **466** cases passed, including updated Step 1 expectations |
| Added SQLite contract cases | **31 passed**, one dialect-specific skip |
| Complete frontend suite | **51 passed**, two test files |
| Production frontend build | Passed; 26 modules transformed |
| Independent temporary SQLite smoke | Create → recommend → start → reopen/recover → finish with goal completion → history passed; snapshot retained |
| git diff --check | Passed |

An early integration attempt found a test-fixture engine mismatch: failure
injection observed the migration engine rather than the API engine. The fixture
was corrected to yield the API engine and waiting-test cleanup releases its lock
even if an assertion fails. No production behavior was weakened to fix tests.

## Preservation and changed files

SHA-256 comparison against the pre-task filesystem baseline confirms reports
001–012 and the original SQLite migration are byte-for-byte unchanged, including
previously uncommitted reports 011/012. The frozen scorer hash is exactly:

b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a

Step 2 changed backend/app/database.py, migrate.py, models.py, routes.py,
session_routes.py and main.py; backend/requirements.txt; the existing Step 1
configuration test file; README.md; IMPLEMENTATION_PLAN.md; reports/README.md.
It added the PostgreSQL migration, cross-dialect test file, and this report.
Frontend, scoring, original migrations and historical reports were untouched.
Existing Step 1 edits remain in the working tree. No commit, push or tag was made.

## Limitations and completion decision

PostgreSQL 16.3 on Windows with Psycopg 3.3.6 is verified. Hosted Neon, TLS/proxy
behavior, serverless concurrency/connection budgets, Linux binary wheel packaging,
Vercel runtime/static routing, access protection and backup/restore procedures are
not verified. There is no deployed instance or new cloud resource. PostgreSQL
tests require the explicit isolated local test setting; absence results in honest
skips. The application lock deliberately serializes all writes for a small personal
library; no throughput optimization or multi-user design is implied. Migrations
remain maintenance operations, not a live zero-downtime deployment promise.

**Deployment Step 2 is genuinely COMPLETE:** real PostgreSQL persistence,
constraints, migrations, UTC, concurrency, atomicity, snapshot evidence and domain
contracts pass alongside SQLite and frontend regressions.

**Exact next recommended action:** separately authorize Deployment Step 3 only:
production packaging/runtime compatibility for the proposed single-project host,
including Python entrypoint, static frontend/API routing and build/runtime checks,
while preserving V0.1. Do not deploy, create Vercel/Neon resources, load personal
data, add product features or begin V0.2 during that step. Nothing from Step 3 was
started here.
