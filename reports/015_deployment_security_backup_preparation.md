# 015 — Deployment security, data migration and recovery preparation

Date: 2026-10-03 (America/Los_Angeles). Milestone: Deployment Step 4.
Status: **COMPLETE as preparation; no hosted acceptance or deployment claimed.**
Baseline: accepted V0.1, reports 010–014, frozen policy v0.1-final-004.
This new historical record supersedes no previous report. No personal database
was opened by the transfer tools, no cloud resources/secrets were created, and
no V0.2 work occurred.

## 1. Scope and result

Reviewed PROJECT.md, IMPLEMENTATION_PLAN.md, README.md and reports 010–014.
Implemented narrowly scoped request safeguards and explicit maintenance tools.
Verified fictional SQLite transfer and actual PostgreSQL custom-format backup
and restore through Sidequest. Created [DEPLOYMENT.md](../DEPLOYMENT.md) as the
operational runbook and pending live acceptance checklist. Architecture remains
one local application/one eventual protected Vercel project with PostgreSQL.

## 2. Current official protection research

Current Vercel **All Deployments** protection includes production on every plan,
including Hobby; Standard Protection is insufficient because production remains
public. This is supported by the current
[Deployment Protection documentation](https://vercel.com/docs/deployment-protection)
and the [September 9, 2026 announcement](https://vercel.com/changelog/protect-production-deployments-for-free-on-every-plan).
No account capability or actual setting was exercised in this task.

[Services documentation](https://vercel.com/docs/services) describes internal
services exposed only by top-level rewrites and one public surface with shared
Deployment Protection. Our existing route table remains intact. This supports
the intended full frontend/API/static boundary, subject to live verification
on the actual account and every resulting address. Services remains beta.

## 3. Owner-only access model

[Vercel Authentication](https://vercel.com/docs/deployment-protection/methods-to-protect-deployments/vercel-authentication)
is the authentication boundary. Audit membership, viewers, access groups and
deployment access grants: authentication for an authorized team member would
not by itself enforce single-owner access. Only the owner may be authorized.
Cookies are scoped to deployment URLs; an authenticated URL does not prove
another URL is authenticated. Anonymous traffic must receive denial or an
authentication page, never application data. No app registration, login, role
system or authentication middleware was added.

## 4. Bypass and direct-access audit

Audit stable production aliases, generated URLs, previews, any future custom
domains, actual JS/CSS assets, API reads/writes/history, unknown API routes,
error paths, docs/openapi/health-like paths and any discovered direct function
or service addresses. Internal Services should have no separately public URL;
verify the actual platform inventory instead of assuming that from config.
No health endpoint was added.

[Documented bypasses](https://vercel.com/docs/deployment-protection/methods-to-bypass-deployment-protection)
include shareable links, exceptions, trusted sources and automation bypass.
Disable them, audit grants, and do not create convenience tokens. Top-level
protection is not implemented by vercel.json itself. Configure a team default
before Git import can trigger a build/deployment, then verify inheritance.
If the real gate fails on any surface, stop before personal data or acceptance.

## 5. CSRF/cross-origin findings and implementation

Inspected actual library and session routes: mutations use POST/PATCH/DELETE;
recommendation uses POST too. Bodyless goal completion, archive restoration and
session-adjacent operations make JSON content-type/preflight an insufficient
universal defense. No broad CORS exists. A hostile HTML form can attempt a
bodyless POST; browser behavior must not depend on an undocumented cookie flag.
Current ordinary Vercel Authentication SameSite behavior was not established
from official documentation. Documented optional SameSite behavior for an
[automation bypass cookie](https://vercel.com/docs/deployment-protection/methods-to-bypass-deployment-protection/protection-bypass-automation)
does not establish ordinary owner-cookie protection.

Added an explicit `SIDEQUEST_ALLOWED_ORIGINS` production requirement and a
small middleware guard for every unsafe HTTP method. Require one exact allowed
Origin, or one allowed Referer only when Origin is absent; reject null,
malformed, duplicate, untrusted and missing evidence. Explicit cross-site
Fetch Metadata also rejects. Invalid Origin cannot fall back to a good Referer.
Host/forwarded headers do not define trust. HTTPS only except local loopback
testing. No wildcards, paths or trailing slashes. Rejection occurs before route
effects. Origin evidence is forgeable outside browsers; it does not replace
the provider authentication gate. Production fails configuration early without
the allowlist. Local app behavior remains unchanged when the setting is absent.

## 6. Header decision

Added DENY framing, nosniff and no-referrer headers at the deployment level and
to guarded API responses; API responses also get no-store. These small controls
do not restrict normal React/Vite resource loading. No CSP was introduced; no
claim about a tested CSP is made. Hosted provider auth/error responses and
Safari behavior remain live checks. No blanket copied header template or CORS.

## 7. Secrets and configuration boundary

Private runtime `DATABASE_URL` uses the future pooled PostgreSQL connection;
`SIDEQUEST_POSTGRES_POOL=null` is non-secret. Production also needs the explicit
origin allowlist, and must omit `SIDEQUEST_DB_PATH`. The owner machine uses a
separate direct `SIDEQUEST_MAINTENANCE_DATABASE_URL`; maintenance never falls
back to runtime URL. Preserve TLS connection options. Tools never accept URLs
on command-line arguments or print credentials/domain records.

Important qualification: current Vercel Services shares project variables with
builds. `DATABASE_URL` is consumed only by backend application code, but strict
per-service exclusion from trusted frontend build environments is **not** an
available guarantee demonstrated here. Never grant untrusted builds secrets,
never configure production data for arbitrary previews, and never prefix URLs
with `VITE_` or inject them through define/loadEnv. This corrects the shorthand
"backend-only" wording in mutable README without editing historical report 014.
If strict build-process isolation is required, hosting needs human review.

[Vite's default environment behavior](https://vite.dev/guide/env-and-mode)
exposes VITE-prefixed variables, not arbitrary private process values. Rebuilt
with fictional private runtime/maintenance URL sentinels and scanned generated
dist: the private sentinel was absent. This confirms current artifacts, not
future settings or all supply-chain risks. No actual secrets were used.

## 8. Transfer design and safeguards

`app.maintenance transfer --source <existing SQLite file> [--dry-run]` opens
SQLite read-only with query_only/foreign keys and a coherent read transaction.
Only SQLite source -> PostgreSQL destination is accepted. Both migration
histories/checksums must be current; the destination must contain only the four
known migrated tables and have empty domain tables. No overwrite option exists.

Source relationships and application record schemas are validated. Original
typed rows are inserted in game/goal/session order, then compared on readback.
Original snapshot JSON is never replaced with a Pydantic projection. IDs,
relationships, UTC instants, tags, states, notes and historical numeric values
are preserved. Dialect-specific migration history is not transferred. JSON
text layout and storage timestamp representation are not byte-copy contracts;
original logical snapshot evidence and values are the contract.

Target writes and ID sequence restart use one transaction and the application's
advisory lock. ALTER SEQUENCE is used because setval effects would survive a
rollback. Dry-run performs real insert/readback/sequence work then rolls back.
Failures roll back domain data and sequence changes. Unsupported next-ID ranges
are refused. Target maintenance must exclude external writers/migrators that
do not cooperate with advisory locking. Counts and logical SHA-256 are reported
without logging records. Stop/copy the source consistently before actual import;
never copy an uncheckpointed live WAL main file alone.

## 9. Real transfer evidence

Created a separate local PostgreSQL 16.3 cluster on loopback port 55439,
independent of the installed PostgreSQL service. Each integration test created
and dropped UUID-named disposable databases. SQLite fixtures were temporary;
the source-file hash was compared before/after transfer.

Fixture: three fictional games (Iron Summit, Cloud Garden, Old Harbor), four
goals including completed/archived records, two completed sessions and one
active session. UTC creation/start/finish timestamps, notes, original snapshots,
fractional time-fit `6.666666666666667`, goal completion and completed-session
recency were included. All transferred typed rows and snapshots matched exactly.

Actual canonical-app API checks compared library/goals with archived records,
history, active session and recommendation output to the SQLite source. Then
finished the recovered active session, inserted a new game and goal with
noncolliding IDs, selected an actual eligible recommendation, started/finished
a new session with a noncolliding ID and verified negative recency contribution.
No scorer changes were required. An initial verification fixture tried to start
an option outside the accepted choice band; it was corrected to select the
actual recommendation rather than change the production choice policy.

Dry-run left domain tables empty and identity sequences unchanged; the same
target then accepted the real transfer. An injected session-insert failure
rolled back all preceding inserts and sequences; retry succeeded. Wrong
dialects, nonempty target, unmigrated/incompatible history, extra target tables,
damaged source history and invalid source snapshot were refused. The real CLI
dry-run returned the expected 3/4/3 counts without data changes.

## 10. Current Neon Free recovery findings

The current [plan documentation](https://neon.com/docs/introduction/plans)
lists six-hour history capped at 1 GB-month and one manual snapshot; scheduled
snapshots are not included on Free. The recent
[October 1, 2026 Free-plan announcement](https://neon.com/blog/neon-free-plan-1-gb-per-project)
also describes the six-hour window. Some generic backup guidance describes
different broader retention ranges; use current plan-specific limits and check
the actual project. Provider history/branches/manual snapshots are convenient
within-provider recovery, not off-provider backups. Actual account limits and
recovery settings remain unverified.

## 11. Owner-controlled backup procedure

`app.maintenance backup --directory <existing private off-repo directory>` uses
actual pg_dump custom format with no-owner/no-acl. File naming is dated UTC,
exclusive reservation refuses collisions, failure removes partial output, and
success requires archive listing plus timestamp/size/SHA-256 metadata. It first
validates current app migration history. Source data is not modified; normal
writes need not stop. Archive represents pg_dump's consistent snapshot, not
later writes. No scheduler or cloud backup integration was added.

Keep encrypted/protected independent copies and several dated generations;
backup after valuable changes and before risky actions. Daily manual operation
is an initial suggested routine, not an implemented guarantee. Loss exposure is
data since the last successful backup. Full details/commands are in DEPLOYMENT.md.

Client credentials go through private libpq environment, not arguments; raw
stdout/stderr is withheld on errors. Inherited PG variables are cleared to avoid
an unintended service/target; supported URL options are translated explicitly
and unknown/repeated options refused. A privileged local process can inspect
environment values: a trusted owner device is assumed. Dumps contain personal
data and are not encrypted by pg_dump. Use clients at least as new as the server
major version. [PostgreSQL pg_dump documentation](https://www.postgresql.org/docs/16/app-pgdump.html).

## 12. Actual isolated backup and restore acceptance

Migrated a fictional PostgreSQL database, transferred fixtures, took a real
custom-format dump with PostgreSQL 16.3 tools, checked size/checksum, and restored
using actual pg_restore into a **different empty, unmigrated** PostgreSQL database.
Verified migration checksums/current history and equality of logical data hash.
Started canonical Sidequest against the restored database and repeated library,
history, snapshot, recommendation, active-session recovery, new game/goal write
and new session start/finish checks. **All passed.** This was not a mocked client
or a dump-only success claim.

Restore refuses nonempty targets, including an already migrated schema. It
uses single-transaction/exit-on-error, restores included schema/history/identity
state, and validates app records afterward. An invalid archive left an empty
target empty. Backup collision preserved previous bytes; injected backup-client
failure removed partial output; repository output directory was refused.
Only trusted archives are acceptable: restore executes SQL. No ownership/roles
or credentials are reconstructed. Post-restore validation failure can leave an
unaccepted restored database, which must remain isolated. These qualifications
are in the runbook. [PostgreSQL pg_restore documentation](https://www.postgresql.org/docs/16/app-pgrestore.html).

## 13. Disaster recovery

DEPLOYMENT.md contains explicit procedures for corruption, failed migrations,
lost/replaced databases and provider discontinuation. Stop writes, preserve
evidence, recover into an isolated new target, use a compatible Git revision,
validate data/lifecycle, then separately switch runtime configuration. Do not
rewrite migration history or destructively replace the sole surviving copy.
Within-window provider recovery is optional; independent dumps are the durable
escape path. Empty installs use migrations; full archive recovery restores its
included schema/history. Git reconstructs the app; the archive reconstructs
the database. No automatic failover or recovery-time promise.

## 14. First-deployment runbook

The 20-step sequence in DEPLOYMENT.md requires separate authorization and starts
with account/cost capability checks and protection defaults **before Git import**.
It covers empty Neon staging, runtime/direct URLs, explicit migrations,
fictional verification, protected Vercel import, private configuration and
origin allowlist, separately authorized deployment, anonymous/owner access,
routing/secrets/workflow, mobile, redeploy/cold start, independent first backup,
hosted restore evidence and final acceptance. Personal transfer is optional
and separately authorized after staging, not part of this task.

## 15. Future production acceptance checklist

DEPLOYMENT.md defines evidence fields and explicit checks for all hostname/path
surfaces; anonymous reads and writes must deny app access. It checks owner
authentication and CSRF, access grants/bypasses, assets/API/fallback/error
routing, headers and secret exposure, PostgreSQL history/persistence/recency,
session lifecycle/snapshots, actual hosted backup/restore, iPhone Safari active
recovery and measured static versus API/database cold-start latency. All remain
**pending live execution**. Local tests do not pretend to test provider UI.

## 16. Tests added

51 added cases: 30 security cases and 21 maintenance cases. Security covers
unsafe methods, hostile/bodyless requests, malformed/null/duplicate/absent
evidence, origin-vs-Referer precedence, Fetch Metadata, valid origin/Referer,
invalid configuration, headers and local default behavior. Maintenance covers
real transfer/API contracts, dry-run, rollback/sequences, dialect/schema/target
refusal, source immutability, secret-safe option handling, actual backup/restore,
invalid restore, backup failure/collision and output destination constraints.
15 maintenance cases use real PostgreSQL. Existing packaging subprocess tests
now supply a non-secret fictional allowed origin to satisfy the production guard.

## 17. Complete backend and PostgreSQL result

Command from backend with disposable local PostgreSQL test URL and isolated
import-time SQLite path: `.venv/Scripts/python.exe -m pytest -q --tb=short`.
Result: **598 passed, 2 skipped, 62.12 seconds**. All 547 prior passing cases
remain passing. The two existing intentional SQLite/dialect skips remain.
Includes all 33 prior PostgreSQL cases plus 15 new real PostgreSQL maintenance
cases: **48 real PostgreSQL cases passed**, none skipped for unavailable tools.
Packaging checks are included in the full backend result. Existing installed
PostgreSQL service and personal databases were not used for transfer/restore.

## 18. Frontend/build/packaging result

Full frontend suite: **51 passed**, two files, 12.43 seconds. Production Vite
8.3.2 build passed (26 modules; JS 252.38 kB, CSS 9.30 kB, HTML 0.47 kB).
An additional fictional-secret build passed and its generated output scan found
no private sentinel. No frontend application or build configuration changed.
Canonical production adapter and prior packaging checks passed in backend
regression; no actual Vercel runtime was exercised. `git diff --check` passed.

## 19. Frozen scorer verification

Byte-for-byte SHA-256 remains:

`b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a`

No scoring, suitability, ranking, session-choice or historical snapshot policy
was modified. No product feature was added.

## 20. Historical preservation

Compared pre-task SHA-256 values against final values for all 14 historical
reports, the SQLite initial SQL, PostgreSQL initial SQL and scorer: **17 of 17
unchanged**. Only the report index changed, plus this new numbered report.
Initial migrations remain immutable; no schema revision was needed.

## 21. Files created/changed

- Created `DEPLOYMENT.md`, this report, `backend/app/security.py`,
  `backend/app/maintenance.py`, `backend/tests/test_security.py`, and
  `backend/tests/test_maintenance.py`.
- Updated `backend/app/main.py`, `backend/index.py`, `vercel.json`,
  `backend/tests/test_production_packaging.py`, `.gitignore`, `.vercelignore`,
  `README.md`, `IMPLEMENTATION_PLAN.md`, and `reports/README.md`.
- No dependency, frontend, schema or scorer changes. Backup dump patterns are
  excluded from Git and provider upload; tools require off-repository output.
- Temporary PostgreSQL test cluster was stopped after verification; test
  databases were disposed/dropped and no temporary cluster-path file is retained
  in the workspace. Local temporary artifacts are not a personal backup strategy.

## 22. Unresolved deployment risks and human decisions

Actual Services availability, account grants/settings, automatic Git deployment,
all direct URLs, hosted TLS/runtime lifecycle, origin configuration, provider
response headers/cookies and iPhone behavior need the live checklist. No
actual cloud account state was read or changed. Free plan capabilities can
change. Shared trusted build environments do not offer demonstrated per-service
secret isolation; decide whether this is acceptable for the owner-controlled
repository. Off-provider backup retention/device encryption are owner choices.
Provider history is short, backups manual, and restoration requires compatible
code/tooling. Arbitrary external SQL is outside application locking. Actual
hosted backup/restore evidence is required before production acceptance.

## 23. Step 4 acceptance decision

**COMPLETE as repository/local preparation.** Official documentation supports
the owner gate; bypass surfaces, CSRF and secret boundaries are documented;
conservative transfer and actual dump/restore work on real isolated PostgreSQL
through Sidequest; runbooks/live checks exist; complete regressions pass;
frozen evidence remains unchanged. No cloud resources, authentication settings,
real secrets, personal imports, custom domains or automation were touched.

## 24. Exact next action requiring authorization

Authorize creation/configuration of **empty Neon/Vercel staging resources using
fictional data only**, with All Deployments owner-only defaults verified before
Git import can automatically expose a deployment. Clarify whether that resource
task includes its automatic first build/deployment; otherwise avoid import
until deployment is separately authorized. Hosted acceptance and optional
personal-data transfer remain later explicit actions. Stop here; do not begin
V0.2 or execute the runbook automatically.
