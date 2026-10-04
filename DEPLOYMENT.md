# Protected deployment and recovery runbook

Prepared 2026-10-03, Deployment Step 4. No cloud resources or deployment exist.
This is an execution checklist for a later, separately authorized task, not
permission to run it. V0.1 and its scorer remain frozen.

## Access boundary

Use Vercel Authentication with **All Deployments**, not Standard Protection.
Current documentation supports production protection on every plan, including
Hobby. Top-level protection applies across Services; services are internal
unless exposed by the project's route table. Protect the frontend, static
assets, API, generated deployment URLs, previews and any eventual custom domain.
See [Deployment Protection](https://vercel.com/docs/deployment-protection),
[Vercel Authentication](https://vercel.com/docs/deployment-protection/methods-to-protect-deployments/vercel-authentication)
and [Services routing](https://vercel.com/docs/services/routing).

Authentication alone does not mean owner-only: audit team/project membership,
viewers, access groups and deployment access grants. Only the owner may have
access. Disable shareable links, protection exceptions, trusted-source bypasses
and automation bypasses. Never create a bypass token to make smoke tests easier.
Authentication cookies are scoped to a deployment URL; test authentication on
each hostname rather than assuming a cookie transfers between deployment URLs.
Current ordinary authentication-cookie SameSite behavior is not documented well
enough to use it as the CSRF guarantee. Bypass-cookie documentation is not evidence
about the ordinary authentication cookie.

Before importing a Git repository (which may trigger deployment), configure the
team default to All Deployments protection and verify project inheritance. If
the actual account cannot protect all surfaces before exposure, stop. Do not
substitute application accounts or a public deployment. Settings, direct URLs
and provider responses must be verified live; repository configuration cannot
prove a hosted boundary.

## Application request safeguards

Production `index:app` requires `SIDEQUEST_ALLOWED_ORIGINS`: a comma-separated
list of exact HTTPS origins, with no trailing slash, paths or wildcards. Example
non-secret syntax: `https://sidequest.example`. Use the eventual stable protected
application origin. Explicitly add a generated origin only if the owner must
write through it. Previews must use isolated fictional databases and their own
allowlist, never the personal production database.

POST, PUT, PATCH, DELETE and any other unsafe method require one allowed Origin;
if Origin is absent, one allowed Referer is accepted. Missing, malformed,
duplicated or untrusted evidence is rejected with 403 before a route mutates
data. Explicit cross-site Fetch Metadata is rejected too. Invalid Origin cannot
be rescued by a good Referer. The allowlist is configuration, independent of
Host and forwarded headers. HTTP loopback is permitted for local testing only.
No CORS is enabled. Tools calling mutations need an allowed Origin as well as
the real provider authentication. Origin can be forged by a non-browser client;
this is CSRF protection, not authentication. GET/HEAD/OPTIONS remain read-only.
Local `app.main:app` remains unchanged when the variable is absent.

The entire deployment requests `X-Frame-Options: DENY`,
`X-Content-Type-Options: nosniff`, and `Referrer-Policy: no-referrer`.
The configured API guard also sends `Cache-Control: no-store`. No CSP was
introduced: a strict policy and provider authentication/toolbar interaction
need their own actual-browser verification. Verify headers on live assets,
API errors and successful API responses; provider-generated responses may
have different headers. The guard rejects unsafe requests without either
Origin or Referer, so confirm iPhone Safari's normal same-origin fetch behavior.

## Private configuration

| Setting | Intended use |
| --- | --- |
| `DATABASE_URL` | Private PostgreSQL application connection, eventually Neon pooled URL with required TLS options. |
| `SIDEQUEST_POSTGRES_POOL=null` | Runtime NullPool; no retained local connection pool. |
| `SIDEQUEST_ALLOWED_ORIGINS` | Explicit protected browser origins; non-secret. |
| `SIDEQUEST_MAINTENANCE_DATABASE_URL` | Owner-machine direct PostgreSQL URL for explicit maintenance; not deployed. |
| `SIDEQUEST_DB_PATH` | Local SQLite only; absent in production. |

Only the backend consumes the database URL. Never use `VITE_DATABASE_URL`,
`VITE_*` credentials, a Vite `define` replacement, committed `.env` files or
client-side connection code. Never echo URLs or pass them on a command line.
Keep runtime pooled and maintenance/direct URLs separate and retain TLS query
options; the maintenance tool rejects unsupported options rather than silently
dropping them. Set values privately through provider settings or an owner-only
local environment. Use a trusted device, avoid shell transcripts and clear
maintenance values after use. A logical dump contains personal data and notes;
protect it like the database.

**Hosting boundary limitation:** current Services uses shared project environment
variables, including builds. Private `DATABASE_URL` is application/backend-only,
but cannot be claimed to be isolated from trusted frontend build processes by
this configuration. Do not grant untrusted builds project secrets. Never
configure production secrets for arbitrary preview branches. Vite exposes
`VITE_*` by default; the current config does not load all environment values
into client code. A build with fictional private database sentinels was scanned
and contained neither secret. Inspect actual deployed artifacts and network
responses too. If strict per-service build isolation becomes a requirement,
stop and review hosting rather than claiming it already exists. Sources:
[Services](https://vercel.com/docs/services),
[Vite environment variables](https://vite.dev/guide/env-and-mode).

## Explicit SQLite transfer

Use compatible Python dependencies from `backend/`. The owner privately sets
`SIDEQUEST_MAINTENANCE_DATABASE_URL` to the direct **destination** URL. Before
transfer, set `DATABASE_URL` privately to that same direct URL for the explicit
existing migration command, with `SIDEQUEST_DB_PATH` absent:

```powershell
python -m app.migrate
python -m app.maintenance transfer --source C:\OwnerData\sidequest-copy.sqlite3 --dry-run
python -m app.maintenance transfer --source C:\OwnerData\sidequest-copy.sqlite3
```

The example paths are placeholders. Stop the source app, finish an active
session if practical, and make a consistent SQLite copy outside the repository
(use SQLite backup or checkpoint/close before copying; do not copy only the main
file of a live WAL database). Preserve the original and copy. Inspect them
privately. This task used fictional fixtures only; personal transfer requires
separate authorization.

The destination must already have its own current PostgreSQL migration history
and empty domain tables. Transfer accepts only SQLite -> PostgreSQL, validates
both histories/checksums and source foreign keys, and copies the three known
domain tables in relationship order. It preserves IDs, UTC timestamps,
statuses, tags, notes, original snapshot JSON and fractional values; it does
not project snapshots through response serialization or copy SQLite migration
rows. It reads the source read-only and compares typed destination rows to
source rows before commit. Sequence restart uses transactional ALTER SEQUENCE.
Dry-run executes the same validations/inserts/sequence work, then rolls back.
Wrong dialects, extra destination tables, nonempty targets, invalid histories
or invalid snapshots fail closed. There is no destructive overwrite option.

Writes are serialized with the application's advisory lock; keep the target
off-line to other tools and migration operators throughout maintenance. These
locks cannot control arbitrary external SQL. Results contain counts and a
logical SHA-256, not personal records or credentials. JSON object formatting
and SQLite timestamp byte encodings can change across dialects; application
values and historical numeric evidence must match exactly. Verify the API
library, goals, history, active state, snapshots and recommendations before
switching runtime configuration. A transferred active session can resume;
elapsed time still derives from its original start timestamp.

## Owner-controlled backup

Neon Free currently offers a **six-hour** restore window, capped at
1 GB-month history, and one manual snapshot; scheduled snapshots are not Free.
Provider recovery and branches remain in Neon and are not independent backups.
Plan limits can change: confirm the actual project settings at deployment.
[Current plan documentation](https://neon.com/docs/introduction/plans),
[backup guidance](https://neon.com/docs/manage/backups).

Privately set the maintenance direct URL, choose an existing private directory
outside both this repository and Neon, and run:

```powershell
python -m app.maintenance backup --directory C:\OwnerBackups\Sidequest --pg-bin "C:\Program Files\PostgreSQL\16\bin"
```

The client directory is an example, not a production version promise. Install
trusted pg_dump/pg_restore compatible with the actual server; pg_dump must not
be older than the server major version. The tested local pair was PostgreSQL
16.3. The command uses custom format, records UTC time, size and SHA-256, checks
pg_dump success and archive readability, and refuses filename collisions.
The name is `sidequest-YYYY-MM-DDTHHMMSSZ.dump`. Failed output is removed.
No database writes or routine application downtime are required. pg_dump takes
a consistent snapshot; writes after that snapshot are outside the backup.
See [pg_dump](https://www.postgresql.org/docs/16/app-pgdump.html).

Credentials go to the child client through libpq environment variables, not
arguments; command output is captured and failures are sanitized. Environment
values can be visible to sufficiently privileged local processes, so use only
the trusted owner machine. No protection against a compromised owner device is
claimed. Never paste diagnostic output containing credentials or domain data.

Take a backup after valuable play/history changes and before every import,
migration or risky maintenance action. A daily owner-initiated backup is a
reasonable initial routine; the recoverable loss is everything since the last
successful dump. Keep several dated generations, verify hashes after copies,
and keep another protected copy on a separate device/location. Use device or
file encryption; archives are not encrypted by pg_dump. Do not automatically
delete the last known tested backup. No scheduling is configured.

## Tested restore and disaster recovery

Restore only a trusted owner-created archive into a separate, completely empty
PostgreSQL database with no app traffic. **Do not migrate it first:** the full
dump restores its schema, PostgreSQL migration history, domain rows and identity
sequences. Point the private maintenance URL at this new target:

```powershell
python -m app.maintenance restore --archive C:\OwnerBackups\Sidequest\sidequest-YYYY-MM-DDTHHMMSSZ.dump --pg-bin "C:\Program Files\PostgreSQL\16\bin"
```

The tool refuses a nonempty target and uses pg_restore's single transaction and
exit-on-error behavior. It subsequently validates current schema/checksums,
domain records and a logical hash. SQL restore failure rolls back the restore;
post-restore application validation failure may leave restored data, so keep
that target quarantined and investigate. Never reuse it by overwriting.
Trusted dump SQL can execute database commands. Roles/ownership/grants are not
transported; target access/credentials remain an explicit owner setup action.
See [pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html).

Use the Git revision compatible with the backup's schema. Verify history,
relationships, snapshots, recency and active state through Sidequest, then
perform a new game/goal write and session start/finish to check sequences and
constraints. Compare the restore logical hash to an original known snapshot
when available; a running database may have advanced since its backup. Later
schema upgrades need explicit migration after recovery verification and a
fresh backup. Switch the application URL only after acceptance. Preserve the
old database and files until recovery is accepted.

- **Accidental corruption:** stop application writes, preserve evidence and a
  dump of the damaged state if readable. For a recent event, consider Neon
  history recovery into an isolated branch within the actual retention window;
  otherwise restore a known good logical backup into a new database. Compare
  expected losses before switching. Do not destructively restore over the only
  copy.
- **Failed migration:** keep traffic stopped; inspect history and failure
  privately. Do not edit old SQL/checksums or mark an unapplied migration as
  applied. Use compatible code with an intact schema, or recover into a fresh
  database from the pre-migration backup; verify before explicitly retrying a
  corrected new migration.
- **Lost/replaced Neon database:** restore the off-provider archive into an
  authorized empty PostgreSQL database, verify with matching Git code, configure
  private runtime/direct URLs and explicitly validate the new protected host.
- **Provider discontinuation:** reconstruct the app from Git and data from the
  independent dump on compatible PostgreSQL. For an empty new installation use
  the migration stream; for full dump recovery use its included schema/history.
  Authentication/protection, credentials and hosting configuration need fresh
  verification. Source and SQL streams are portable; a Vercel deployment is
  replaceable. There is no automatic failover or recovery-time guarantee.

## First deployment sequence — do not execute yet

1. Obtain authorization to create empty Neon/Vercel staging resources, use only
   fictional data, and agree any cost boundary. Recheck plan limits and Services
   beta availability on the account. This is resource preparation, not permission
   for personal transfer or product acceptance.
2. Establish owner-only All Deployments team defaults before any Vercel Git import
   or first build. Audit all access grants and bypass settings. Stop if unavailable.
3. Create the authorized Neon Free project/database for staging. Identify pooled
   runtime and direct maintenance URLs, TLS options and server major version.
4. Configure direct maintenance values privately on the owner machine. Run the
   existing PostgreSQL migration stream explicitly; validate current history.
5. Seed fictional data and verify through the local canonical app. Personal
   SQLite transfer is optional **later**, after separate authorization and a
   tested source copy/empty production target; run dry-run before committing.
6. Confirm database constraints/history and keep staging credentials distinct
   from any later personal database.
7. Create/import the authorized Vercel project at repository root; inspect inherited
   All Deployments protection before proceeding. Do not expose an unprotected
   first deployment. Verify current Services configuration support.
8. Set private runtime configuration for only the authorized environment; never
   connect arbitrary previews to production. Keep the direct maintenance URL
   off Vercel. Set the stable protected origin allowlist and NullPool profile.
9. Obtain separate deployment authorization if it was not included in the task.
   Deploy the unchanged prepared application. Import may automatically deploy;
   the authorized scope and inherited gate must account for that before import.
10. Inventory all resulting domains, aliases, preview/generated URLs, service or
    function addresses and bypass settings. Test anonymous denial first.
11. Authenticate only as the owner; test the stable URL and any other required
    protected hostname independently.
12. Verify React, assets, API routing, unknown API JSON 404 and security headers.
13. Inspect served bundles, errors, logs and network payloads for secret exposure.
    Test cross-origin mutations while authenticated using fictional records.
14. Exercise fictional create/edit/archive/complete, recommendation explanations,
    start, reload/recover, finish and history. Check recency and fractional snapshots.
15. Redeploy/restart and repeat reads to prove PostgreSQL persistence and lifecycle.
16. Test iPhone Safari authentication and the primary workflow, including active
    session recovery after reload/backgrounding.
17. Measure static and API/database wake latency after inactivity separately;
    record observations rather than claim a provider SLA or fixed latency.
18. Produce the first hosted-data backup on the owner machine, outside Neon, and
    copy/check it in the independent protected backup location.
19. Restore that backup into a separate authorized empty recovery database and
    verify the application/lifecycle. Local evidence alone does not certify a
    hosted production dump. Document recovery losses, timing and errors.
20. Declare the deployment accepted only after every relevant check below passes.
    Personal data import and any environment switch require explicit subsequent
    authorization; this runbook does not authorize them.

## Live acceptance record

For each check record date, environment, hostname/path, authenticated/anonymous
state, expected versus observed behavior and redacted evidence. No secrets or
personal contents in public reports. These checks remain pending until deployment.

| Area | Required checks |
| --- | --- |
| Anonymous boundary | `/`, actual JS/CSS assets, `/api/games`, goals, history, active-session reads, recommendations and mutations deny application access. An auth page/redirect is acceptable; application JSON/HTML/data are not. Check unknown API paths and error paths as well. |
| Alternate surfaces | Repeat on stable production domain, generated deployment URLs, all preview aliases, any custom domain and every discovered direct function/service address. Internal-only services should have no independent public URL; verify actual inventory. Check docs/openapi and any health-like paths; there is no added public health endpoint. |
| Access/bypasses | Only owner has membership/viewer/access grants. No shareable links, domain exceptions, trusted-source or automation bypasses. Anonymous API requests with supplied Origin still denied by Vercel. Protection covers production, not just previews. |
| Owner/CSRF | Owner login works, same-origin reads/writes work. Evil/missing/null Origin and hostile forms/fetch cannot mutate fictional records; invalid Origin plus good Referer still denied. Confirm frontend fetch supplies accepted evidence, including Safari. |
| Headers/secrets | Verify DENY/nosniff/no-referrer on app/assets/API, no-store on API. No URLs/passwords in client build, source maps, browser payloads, errors or logs. No `VITE_*` secrets or production credentials in untrusted builds. |
| Routing | `/` serves React, actual assets load, `/api/games` serves FastAPI JSON, unknown `/api/*` returns JSON 404, frontend fallback never captures API. Missing assets do not return React HTML. |
| Database | PostgreSQL migrations/checksums current; create/read/edit/archive/complete work; relationships and constraints hold; recommendations and recency work; session lifecycle and history/snapshots survive redeploy/cold start. |
| Backup/recovery | Dated backup succeeds, metadata/hash recorded, independent copy exists outside provider, actual hosted-data restore into a separate empty database works through app and new lifecycle. |
| Mobile | iPhone Safari login, library, Tonight, scoring explanation, start, reload active recovery, finish and History are usable. |
| Cold start | Record first static request and first API request after inactivity, subsequent warm requests and failures. Separate Vercel wake from Neon connection/query wake where observable. |

Any failed access boundary is a blocker. Stop, preserve evidence, and correct or
review the deployment without importing personal data. This preparation is not
evidence that actual Vercel routing, cookies, Safari behavior or hosted recovery
has already passed.
