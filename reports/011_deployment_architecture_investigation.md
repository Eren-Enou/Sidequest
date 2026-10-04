# 011 — Deployment architecture investigation

Research date: **2026-10-03, America/Los_Angeles**. Baseline: **v0.1.0**, initially clean working tree. Status: investigation complete; implementation and deployment unstarted. This is an immutable historical report; later verification or changed pricing belongs in report 012 or later.

## 1. Decision

Recommend **one Vercel Hobby project**, exposing the React build at `/` and the existing Python FastAPI application at `/api/*`, with **Neon Free PostgreSQL** for persistent data. Keep relative browser requests and one HTTPS origin. Enable **Vercel Authentication → All Deployments**, allowing only the owner's Vercel account. This is a single deployment with CDN assets and a Python function, rather than a continuously running Uvicorn process.

The decisive current information is Vercel's **September 9, 2026** change: production protection is now free on every plan. For this one-user application, provider login can replace building a Sidequest account system. Earlier advice that free protection excludes production is obsolete. [Vercel announcement](https://vercel.com/changelog/protect-production-deployments-for-free-on-every-plan), [protection pricing](https://vercel.com/docs/deployment-protection/usage-and-pricing).

Fallback: **one Render Free Python web service** serving React and FastAPI, using the same Neon database, with a small single-owner password/session login implemented before exposure. Both choices require a deliberate PostgreSQL port; neither can safely retain a writable local SQLite production database.

Expected recurring provider bill: **$0 + $0 = $0/month**, within the published allowances. Use a provider subdomain, not a purchased domain, and no paid add-ons, trial upgrades, marketplace billing, or keep-alive service. “Ongoing free” below means a recurring free plan without fixed trial expiry; it does not guarantee a provider will retain that plan forever.

## 2. Actual repository requirements

Inspection covered `PROJECT.md`, `IMPLEMENTATION_PLAN.md`, report 010, README, dependency files, and the relevant source/migration files. V0.1 acceptance remains complete; deployment is separate work.

| Concern | Current repository behavior | Deployment consequence |
| --- | --- | --- |
| Startup | `backend/app/main.py` exports `app = create_app()`. Engine creation occurs at import. Lifespan checks current migration history and disposes the engine. Local command is `python -m uvicorn app.main:app` from `backend/`, bound to loopback. | Preserve startup validation. Render needs `--host 0.0.0.0 --port $PORT`, without reload. Vercel loads an ASGI entrypoint instead of starting Uvicorn. |
| Dependencies | Synchronous SQLAlchemy; pinned FastAPI, Pydantic, SQLAlchemy, Uvicorn, Starlette in `backend/requirements.txt`. No PostgreSQL driver. | Add a synchronous PostgreSQL driver later; retain Python scorer and API/domain contracts. |
| Database config | Only `SIDEQUEST_DB_PATH`; default `backend/data/sidequest.sqlite3`, relative paths resolved against backend root. `make_engine` creates directories and hardcodes `sqlite+pysqlite`. | A database URL is not supported today. Import-time filesystem writes must disappear when an external DB is selected. |
| SQLite connections | Every connection enables/validates foreign keys; explicit transaction begin hooks; session writes request `BEGIN IMMEDIATE`. | These hooks cannot run against PostgreSQL. |
| Migrations | Explicit `python -m app.migrate [--database PATH]`; numbered SQL, normalized SHA-256 history, forward-only. Startup checks, rather than applying migrations. | Keep explicit versioned migrations; do not substitute `create_all` or automatic request-time migrations. |
| Frontend | `npm ci`, `npm run build` in `frontend/` produce `dist/`; React/JavaScript. Node engine requires supported modern versions; pin the tested runtime rather than accepting host defaults. | Deploy built assets, never the Vite development server. Exclude node_modules and personal data from Python packaging. |
| Browser API | `frontend/src/api.js` uses `fetch('/api' + path)` with JSON requests; no auth token or production API-base variable. | Same-origin hosting preserves this behavior. Browser-visible environment variables must never contain DB/login secrets. |
| Vite | Port 5173, loopback binding, development `/api` proxy; `SIDEQUEST_API_TARGET` overrides its local upstream. | This proxy is not included in `dist/`. It provides no production routing. |
| CORS/static files | FastAPI currently has neither CORS middleware nor frontend static mounting. | Add production static/routing integration. Split origins additionally require explicit CORS or an HTTPS proxy. |
| Security | No authentication dependency or middleware on library, recommendations, sessions, or history. | Every public deployment must have an access gate covering the API, not merely a hidden frontend URL. |
| Backup | README says stop API and copy SQLite file; personal DB files ignored by Git. | Git pushes/tagging preserve code, not user data. Hosted PostgreSQL needs a separate backup/restore procedure. |

The existing recorded baseline is **436 backend tests, 51 frontend tests, and a passing build**, from report 010. Those checks were **not rerun** for this documentation-only investigation; no new runtime verification is claimed.

## 3. Current hosting evidence

Official current pages were opened; Neon pages that the web reader could not parse were read using public HTTPS requests and HTML text extraction. Cached search snippets sometimes showed older limits, so current page bodies took precedence. No signup, account, resource, or deployment was created. Prices are USD.

### Serious application hosts

**Vercel Hobby — recurring $0, personal/noncommercial only.** Current monthly allowances include 100 GB fast transfer, 10 GB origin transfer, 1 million function invocations, 4 active CPU hours, and 360 GB-hours provisioned memory; exceeding allowances can suspend functionality rather than purchasing extra Hobby usage. These are separate quotas, not interchangeable. Sidequest's intended personal use fits the restriction. [Hobby plan](https://vercel.com/docs/plans/hobby), [pricing](https://vercel.com/pricing).

Native FastAPI support uses the Python runtime, including lifespan events. Static assets can be served through the CDN; the default Python bundle limit is 500 MB. The existing nested backend needs explicit entrypoint/import-path and build packaging, not a rewrite to JavaScript. There is no durable application filesystem for SQLite. [FastAPI deployment](https://vercel.com/docs/frameworks/backend/fastapi), [Python runtime](https://vercel.com/docs/functions/runtimes/python).

Current limits list one concurrent Hobby deployment, 100 deployments/day, 45-minute builds, and 50 domains/project. Hobby functions allow up to 300 seconds; a gaming session does not occupy a function for its whole duration. Provider/custom domains support HTTPS; a domain registration is a separate expense. Git integration supports automatic deployments. [Platform limits](https://vercel.com/docs/limits), [Git deployment](https://vercel.com/docs/deployments/git), [domains](https://vercel.com/docs/domains/working-with-domains).

Cold function initialization and PostgreSQL wake-up remain possible; no guaranteed overall cold-start duration was found. Inactive production functions can be archived within two weeks, previews within 48 hours; invoking them restores execution, with an additional cold-start delay. CDN assets do not require starting Python. The filesystem is read-only except temporary scratch storage, which is unsuitable for persistent SQLite. No fixed Hobby trial expiry or mandatory monthly renewal was documented. [Runtime lifecycle/filesystem](https://vercel.com/docs/functions/runtimes), [SQLite limitation](https://vercel.com/kb/guide/is-sqlite-supported-in-vercel).

**Payment-method evidence gap:** the current official pages establish free Hobby and capped usage but do not explicitly promise card-free signup in their text. No card is expected for ordinary Hobby hosting; account-specific verification remains untested. Verify that at onboarding and stop if a paid plan/payment requirement appears. Create Neon directly on its Free plan, avoiding a marketplace offer with separate billing terms. [Marketplace terms](https://vercel.com/legal/integrations-marketplace-service-terms).

**Render Free — recurring $0 Python service; card-free deployment is officially advertised.** It sleeps after 15 minutes without traffic and wakes in about a minute. It provides 750 running hours/workspace/month. Local writes disappear on sleep, restart, and redeploy; no free persistent disk. Free Render PostgreSQL expires after 30 days, so it is not the database for this architecture. Free services are positioned for hobby/testing rather than guaranteed production availability. [Free services](https://render.com/docs/free), [card-free hosting explanation](https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026).

Hobby includes **5 GB outbound traffic/month**, including external database traffic, and **500 build-pipeline minutes/month**. With no payment method, excess traffic suspends services and exhausted build minutes stop new builds. Leave billing unconfigured to enforce the $0 ceiling. [Bandwidth](https://render.com/docs/outbound-bandwidth), [build pipeline](https://render.com/docs/build-pipeline).

The Free instance has 512 MB RAM. Native Python deployment runs Uvicorn on the assigned port; use one worker initially. Managed TLS and custom domains are supported, with two custom domains included in Hobby; use the free provider URL. Native runtimes include a general build toolchain, but verify Python/Node version pins and the combined frontend build before adoption. [Pricing](https://render.com/pricing), [FastAPI guide](https://render.com/docs/deploy-fastapi), [native runtimes](https://render.com/docs/native-runtimes).

Push-based auto-deployment is available, but a **pre-deploy migration command is paid-only**. The fallback should initially run explicit migrations securely from the owner's machine before publishing a schema-dependent revision. Do not run migrations inside each request or rely on an ephemeral build-time SQLite file. [Deploy lifecycle](https://render.com/docs/deploys).

**Cloudflare Pages — recurring free static frontend for the split option.** Static bandwidth is unmetered, with no API-process cold start for assets. Free limits include 500 builds/month, one simultaneous build, 20-minute timeout, 20,000 files, 25 MiB/file, and 100 custom domains/project. It offers Git deployment and HTTPS/provider URLs. No card is advertised for starting the free platform; separate paid products should remain disabled. Pages does not supply a durable application SQLite file or host this CPython/SQLAlchemy backend unchanged. Cloudflare currently directs new projects toward Workers, though Pages remains available. [Pages product](https://pages.cloudflare.com/), [limits](https://developers.cloudflare.com/pages/platform/limits/), [Pages documentation](https://developers.cloudflare.com/pages/), [free platform](https://www.cloudflare.com/plans/).

### Persistent database candidates

**Neon Free — chosen; recurring $0, explicitly no time limit or card.** Current allowances: 100 CU-hours/project/month, 1 GB PostgreSQL storage/project, 5 GB public transfer/project, ten branches/project. Compute sleeps after five minutes; storage persists independently. Short wake-up latency is expected, not a measured Sidequest guarantee. Free instant recovery covers up to six hours or 1 GB of changes; scheduled backups are not included. No application build/runtime or frontend domain is supplied by this database choice. [Pricing](https://neon.com/pricing), [October storage increase](https://neon.com/blog/neon-free-plan-1-gb-per-project).

The current plan documentation adds a 20 GB account-wide PostgreSQL storage cap. Compute/network exhaustion suspends compute until reset or upgrade; storage exhaustion blocks storage-growing operations. These quota limits do not delete data. There is no one-week project-pausing requirement described in that policy; compute sleeping is distinct from deleting a database. Do not infer immunity from account closure or future service changes. Use encrypted DB connections, small bounded pools, and connection validation after sleep. [Plan details](https://neon.com/docs/introduction/plans), [connection security](https://neon.com/docs/connect/connect-securely).

**Supabase Free — credible alternative database, not selected.** Its recurring $0 plan supplies a 500 MB database and 5 GB egress; two active projects are allowed. Projects pause after a week of inactivity, an inconvenient recovery step for occasional personal gaming. Free users are advised to export their own off-site dumps. It would still require the PostgreSQL port and does not run the existing Python API through its database service. Current signup/payment verification was not performed; this is a screened alternative, not a fully verified replacement plan. [Pricing](https://supabase.com/pricing), [backup policy](https://supabase.com/docs/guides/platform/backups).

### Other providers screened out

| Provider | Current classification and Sidequest reason |
| --- | --- |
| GitHub Pages | Recurring free static hosting for public repositories; no Python backend or durable user database. Limits include 1 GB published site, soft 100 GB/month transfer and 10 builds/hour. Git-based deployment is possible, but project-path asset bases and API routing need work. Keeping code on GitHub does not make this a complete application host. [Limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits), [availability](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages). |
| Netlify | Recurring free static option, currently 300 shared credits/month; production deploys consume 15 credits, bandwidth 20/GB, requests 2/10,000. Exhaustion can pause projects. No advantage over a same-origin Python deployment; it does not preserve the existing backend as a normal Python service. Do not use remembered legacy bandwidth/build quotas. [Free plan](https://www.netlify.com/pricing/pro-vs-free/), [credit accounting](https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/billing-faq-for-credit-based-plans/). |
| Railway | There is now a recurring **$1/month Free-plan allowance**, separate from the initial $5/30-day trial. It is not correct to call Railway trial-only. However, the allowance does not establish that this Python service plus persistent volume stays free under actual usage. Trial-volume retention is also limited. Not selected without measured budget/retention verification. [Current trial and Free plan](https://docs.railway.com/pricing/free-trial). |
| Fly.io | New-account trial lasts seven days or two VM-hours, whichever first. Continued hosting requires paid billing; historical free allowances do not establish a new $0 architecture. [Trial](https://fly.io/docs/about/free-trial/). |
| Koyeb | A free web instance exists: 512 MB, 0.1 vCPU, 2 GB local SSD, no persistent volume; it sleeps after an hour. **Requires a card.** Current FAQ describes a $29 authorization hold and a prorated charge for the selected signup plan, which defaults to Pro; downgrading later is not a clean free-onboarding promise. Not selected for the strict budget. [Instances](https://www.koyeb.com/docs/reference/instances), [billing FAQ](https://www.koyeb.com/docs/faqs/pricing), [sleep](https://www.koyeb.com/docs/run-and-scale/scale-to-zero). |
| PythonAnywhere | Free accounts have 512 MiB filesystem storage and one worker/web app with monthly expiry/renewal. This could preserve SQLite in account storage. **FastAPI ASGI now exists experimentally**, but its long-term pricing is explicitly unsettled; it lacks normal static-file mappings and has limited deployment controls. Free outbound networking is restricted. Stable ongoing free ASGI hosting and automatic Git deployment were not established, so it is not a dependable primary/fallback. [Free account limits](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/), [experimental ASGI](https://help.pythonanywhere.com/pages/ASGICommandLine/), [pricing](https://www.pythonanywhere.com/pricing/). |
| Cloudflare Workers/D1 | Python Workers exist through Pyodide; this is not evidence that the current synchronous SQLAlchemy driver/filesystem/transaction setup runs unchanged. D1 is a service binding, not a persistent local SQLite file. Potentially inexpensive, but adapting persistence/runtime adds unnecessary risk to accepted V0.1 behavior. [Python runtime](https://developers.cloudflare.com/workers/languages/python/), [D1 overview](https://developers.cloudflare.com/d1/). |

These screened providers are not equally proven finalists. Unverified signup, bandwidth, ASGI pricing, or retention details are reasons not to promote them, rather than gaps filled with assumptions.

## 4. SQLite persistence and PostgreSQL port

SQLite remains appropriate for **local** Sidequest. A stable file, a single process/instance, enforced foreign keys, writer serialization, and verified backups are sufficient at this scale. Hundreds of games or thousands of sessions alone do not force PostgreSQL.

| Architecture | Safe production SQLite? | Reason |
| --- | --- | --- |
| Vercel function | No | Runtime storage is not a durable shared database. A temporary file can vanish and different instances would have different libraries. |
| Render Free | No | Runtime writes are ephemeral; persistent disk requires paid service. [Persistent disks](https://render.com/docs/disks). |
| Cloudflare static + either API host | No | Static hosting does not fix the API's storage. |
| PythonAnywhere experimental ASGI | Conditional | Account files can hold SQLite, but stable free ASGI pricing/operations are unresolved. Requires migration on the durable path, renewal and off-site copies. |
| Client-only browser | Different architecture | IndexedDB persists locally subject to browser eviction/device loss; it is not the backend SQLite database. |

Uploading SQLite with every deploy, committing it to Git, or copying it to object storage after requests would introduce stale copies, overwrite risks and unsafe concurrent writes. A snapshot used for backup is not a shared transactional database. Sleeping must never reset the library or active session.

The PostgreSQL port is **moderate and concentrated**, not a connection-string-only change:

1. Add `DATABASE_URL` with explicit dialect handling and a synchronous driver. Preserve default local SQLite and `SIDEQUEST_DB_PATH`; reject conflicting configuration. Skip directory creation, SQLite pragmas and SQLite transaction hooks for PostgreSQL. Use TLS and bounded connections appropriate for short-lived functions.
2. Add a separate PostgreSQL numbered migration stream without editing the applied SQLite `001_initial.sql`. Replace SQLite JSON/`typeof`/`strftime` checks, question-mark parameters and `sqlite3.complete_statement` assumptions with PostgreSQL equivalents. Preserve title/range/status/timestamp validation, foreign keys, composite game/goal relationship and one-active-session partial uniqueness. Make generated IDs and JSON null behavior explicit. Preserve migration checksum/history validation separately per dialect.
3. Review `UTCDateTime`: it currently strips offsets before storage and reattaches UTC on retrieval. Choose a tested PostgreSQL timestamp representation and preserve aware-UTC API semantics. Do not accidentally reinterpret local time or change recency inputs.
4. Replace SQLite-wide `BEGIN IMMEDIATE` session serialization. PostgreSQL needs an explicit transaction-level serialization strategy covering start revalidation and finish, including the **absence** of an active row. A transaction-scoped PostgreSQL advisory lock is a small single-user option; locking a nonexistent row is insufficient. Keep the unique index and atomic updates as database defenses, and return the existing conflict behavior on races.
5. Test library edits versus lifecycle validation, concurrent starts/finishes, history/snapshot preservation, recency, rollback and reopening on both dialects. Validate that aggregate timestamps used by recommendations have identical meaning. Do not touch the scorer.
6. If real local data needs importing, stop local writes, copy its SQLite backup, transfer games/goals/sessions with original IDs, timestamps and **stored snapshots unchanged**, reset PostgreSQL ID sequences, and verify counts, relationships and representative history. SQL dialects differ; do not feed a SQLite `.dump` directly to PostgreSQL. Retain the original backup and code tag.

Likely affected files: `database.py`, `migrate.py`, `models.py`, lifecycle transaction handling in `session_routes.py`, dependency/configuration files, additional dialect migration files and tests. SQLAlchemy already handles much ordinary CRUD/query construction. No repository/service abstraction, ORM replacement, migration framework, async rewrite, or schema redesign is needed. The frozen scoring policy stays byte-for-byte unchanged.

## 5. Architecture comparison

**Option A: one continuously running FastAPI service serving React and `/api`.** Render + Neon is the straightforward version. Add static mounting and a narrowly scoped HTML fallback after API routes; nonexistent `/api` routes must remain API errors. Relative fetch works unchanged, CORS is unnecessary, and one build deploys both halves. A cold service delays the initial HTML as well as API calls. Shared external DB makes both desktop and phone see the same active session/history. Maintenance is one application deployment, one DB and an application login.

**Selected Option A variant: one Vercel deployment/origin with CDN assets and FastAPI functions.** Build React once, package the Python app, and route API before SPA fallback. No second publicly exposed API host. Provider production protection covers the same domain used by relative fetch. Process restarts cannot affect sessions because their state is in PostgreSQL. App import/lifespan and connection cleanup must be tested on the host; lifespan is supported, but no in-memory state or filesystem persistence may be assumed. The packaging/routing work is somewhat host-specific, balanced by avoiding an application account/password system.

**Option B: Cloudflare static frontend + Render API + Neon.** The UI loads while the API is sleeping and frontend bandwidth is cheaper. But two builds/providers, logs and URLs must be coordinated. Direct cross-origin fetch needs a public build-time API URL, backend origin allowlist, JSON preflights and credential configuration. CORS is not authentication. Cookies between unrelated provider domains create Safari cross-site complications; a same-origin `/api` proxy would avoid those but adds proxy code/configuration and must not leave the upstream API unauthenticated. Owning a common custom domain also helps but is not a $0 assumption. This is extra maintenance for one user; not selected.

**Option C: React + IndexedDB only.** Static hosting can be free, but JavaScript would take over CRUD, relationships, validation, migrations, session lifecycle/history and deterministic ranking. Porting the frozen Python scorer requires exact parity tests for formulas, explanations, ordering, suitability and near ties; it is not merely deleting FastAPI. Desktop and iPhone databases would differ without synchronization. Manual import/export invites collisions and stale histories; eviction/device loss needs explicit backup. Adding a sync service reintroduces a backend and authentication. This discards too much accepted V0.1 architecture and fails the shared-data objective as proposed.

## 6. Minimum internet security and phone access

Unauthenticated exposure would let strangers read games/goals/notes/history, request recommendations, edit/archive/restore library records, complete goals, start an unwanted session, finish the owner's session, and pollute preserved history. DELETE library routes archive rather than physically delete, but that does not make unauthorized mutation acceptable. Validation/foreign keys protect invariants, not ownership. **Authentication is a prerequisite.** HTTPS, obscure URLs and CORS alone do not solve it.

| Single-user gate | Assessment |
| --- | --- |
| Vercel Authentication, All Deployments | Recommended for chosen host. Owner logs into Vercel on desktop and iPhone. No Sidequest user table/signup/reset system. Verify every production, preview, branch and generated URL and `/api` path is gated; disable share links, bypass secrets and exceptions unless explicitly needed. **Standard Protection excludes production domains.** [Scope](https://vercel.com/docs/deployment-protection), [login mechanics](https://vercel.com/docs/deployment-protection/methods-to-protect-deployments/vercel-authentication). |
| One owner password + secure cookie session | Recommended Render fallback: server-side password hash, signed expiring Secure/HttpOnly cookie, CSRF protection, login throttling, manual secret rotation; fail closed if production secrets are absent. No registration or multiple accounts. Portable but needs more implementation/tests. |
| HTTP Basic over HTTPS | Smallest portable gate, with strong server-side credentials and constant-time verification. Browser password dialogs/logout and iPhone ergonomics need checking; it still needs CSRF consideration. A reasonable temporary private tool gate, less pleasant than provider login. |
| Allowlisted OIDC identity | Good long-term portable option, but provider client configuration, callback handling and another dependency are unnecessary for current owner-only hosting. |
| Shared token in frontend bundle/URL | Reject. Anyone with the assets/URL gets the credential; query tokens leak through history/logs. |

For the selected deployment, rely on the provider access gate only after unauthenticated HTTP checks prove enforcement. Verify identity/account restrictions and enable account MFA. Keep mutation endpoints JSON-only and add/check origin/CSRF protection where needed; a valid login cookie is not permission for another site to issue writes. DB credentials stay backend-only, TLS is required, and debug details/secrets must not appear in browser builds or logs. The database must not be exposed through an unauthenticated generated REST API.

Both devices use one HTTPS bookmark and the same authoritative DB; reload recovers an active session. No native app or device synchronization subsystem is needed. Later acceptance must include actual iPhone Safari login, expiry/re-login, library edits, start/reload/finish, history, and sleep recovery. Read-only calls can retry connection failures; never blindly replay session mutations after an uncertain timeout. Existing conflict handling helps, but deployment latency needs verification rather than assumed compatibility.

## 7. Backups and recovery

Use standard **PostgreSQL custom-format `pg_dump` backups**, downloaded to the owner's computer, plus a second private off-provider copy. Export at least weekly while in use, after important batches of sessions, and immediately before migration/import. Retain several dated weekly dumps and a pre-migration copy; a weekly schedule accepts up to one week of lost edits. Use an appropriate PostgreSQL client version, TLS/direct connection, and securely supplied credentials rather than passwords in shell history. Keep backups and secrets out of Git. [Neon backup strategies](https://neon.com/docs/manage/backups), [dump/restore procedure](https://neon.com/docs/import/import-from-postgres).

Include all tables, constraints, sequences, migration metadata, active sessions and historical JSON snapshots; an ordinary UI history export is not a complete recovery artifact. Preserve the corresponding app commit/migration version. Neon short-window instant restore is useful for recent mistakes but does not replace an off-provider backup or survive provider loss.

Recovery: pause application writes, restore into a **new empty compatible PostgreSQL database** using `pg_restore` with ownership options appropriate to the target, verify schema/history/row counts/foreign keys/IDs/snapshots/active recovery, then change the backend connection and restart. Never overwrite the only good database before validating restoration. Test this with sample data before importing personal history, and repeat periodically. A provider outage/discontinuation becomes restore-to-another-PostgreSQL-host rather than data recreation. If both free database tiers disappear, reevaluate hosting in a new report; paid infrastructure is not implicitly authorized.

## 8. Ranked decision matrix

All rows assume authentication and portability work is completed before internet exposure; none describes today's repo as deploy-ready.

| Rank | Frontend / backend / DB | Monthly cost / payment | Persistence and cold starts | Changes / deployment / maintenance | Authentication / backup | Main risk |
| --- | --- | --- | --- | --- | --- | --- |
| **1** | **Vercel CDN + Python FastAPI in one Hobby project / Neon** | **$0 within caps**; Neon explicitly no card; Vercel card-free onboarding expected, needs account-level confirmation | External durable DB; variable function cold start plus DB wake | Moderate PG port + one build/entrypoint/static routing; Git auto-deploy | Owner-only provider gate; off-site dumps | New protection/packaging integration must be proven; free quotas/no SLA |
| **2** | **Render serves React + FastAPI / Neon** | **$0 within caps**, no card under advertised free onboarding | Same durable DB; whole app sleeps/wakes | Same PG port + static serving + login; familiar Uvicorn; Git auto-deploy | Owner password/cookie; same dumps | Slow initial load; bandwidth/suspension; no free migration hook |
| **3** | **Cloudflare static / Render FastAPI / Neon** | **$0 within caps**, free platform accounts | Same DB; UI remains available during API sleep | PG port + API base/CORS or proxy + login; two deployments | Upstream API must be gated; same dumps | More moving parts and Safari credential behavior |

No overall numeric “best” score is invented. Ranking follows the user's priorities: ongoing free, durable data, one-user security, preserving Python, and reducing deployment/maintenance work. The recent free production gate makes Vercel strongest despite its function packaging requirements. Render is easier to reason about as a process, but would require its own login and delay the whole application on wake.

If the **application host** disappears, use the Render fallback and keep Neon. If **Neon Free** disappears, reassess Supabase's then-current plan and restore an off-site PostgreSQL dump only after verifying its signup, pause/restoration and retention rules. This is a contingency, not a claim of an unconditional free guarantee.

## 9. Expected future repository changes and small implementation sequence

No changes below were executed. New reports should record each implemented/verified stage; this report must not later be rewritten as deployment evidence.

| Step | Future task | Reviewable completion evidence |
| --- | --- | --- |
| **1** | Add portable database configuration and dialect-specific engine setup, retaining local SQLite. | Configuration tests; existing SQLite startup/CRUD/lifecycle behavior passes; no scorer or applied migration changes. Unsupported/unmigrated DBs fail clearly. No cloud access. |
| **2** | Add explicit PostgreSQL migration stream and correct transaction/UTC behavior. | Isolated PostgreSQL integration tests including concurrent start/finish and library revalidation; full backend regression. Use an available local test DB; agree on test setup separately rather than assuming Docker or creating a cloud resource. |
| **3** | Build one production frontend/API origin locally and prepare Vercel entrypoint/build packaging. | Production assets and `/api` work together; unknown API paths stay JSON errors; correct Node/Python pins, no local data/secrets packaged; frontend tests/build and frozen scorer hash pass. No deployment yet. |
| **4** | Prepare security and backup acceptance procedures plus any required CSRF/configuration safeguards. | Local security tests and sample-data dump/restore. Document All Deployments, owner access, no bypasses, preview DB isolation, and fail-closed deployment checklist. No bespoke login unless provider gate proves inadequate. |
| **5** | After explicit deployment authorization, verify live free onboarding and create an empty, protected staging project/DB. | Confirm Hobby/Free, payment requirements and current caps; protect before loading data; no personal data in previews. Configure backend-only secrets and Git integration, no paid marketplace resources. |
| **6** | Run explicit migrations, then deploy and test staging with fictional data. | Anonymous requests to all URLs/API routes denied; owner works on desktop/iPhone; cold/restart/redeploy preserve data; concurrent lifecycle, recommendation explanation and backup restoration pass. Record actual latency. |
| **7** | After staging review, import backed-up personal data and complete production acceptance. | IDs/history/snapshots verified; all nine V0.1 criteria plus internet/security checks pass. Record commit, restore drill and budget checks in a new report. |

For future Git workflow, Vercel Git integration can rebuild on a production-branch push; GitHub Actions are optional for regression checks. **Migrations stay an explicit release operation**, run securely from the owner's machine initially. Do not run them per cold start or from every preview build; do not point arbitrary preview commits at production data. Code rollback is not database rollback. Use backward-compatible changes or a planned brief write pause. No workflow has been created here.

Expected additions are limited to deployment/database configuration, a PostgreSQL driver and migration stream, transaction/UTC compatibility, static/entrypoint/build configuration, deployment security checks, persistence/integration tests and backup documentation. There is no product expansion, auth user model, cloud queue, Docker requirement, scorer tuning, or client scoring port.

## 10. Risks, unknowns and next task

The application is not currently internet-ready: production routing, non-SQLite persistence and an access gate are blockers. Current official documentation supports the recommended shape, **not a tested Sidequest deployment**. Vercel card verification for this account, mixed frontend/backend packaging, gate coverage, Safari login and cold-start response handling require future validation. If any invalidates the free/private architecture, stop for review or use the documented fallback; do not silently upgrade.

Free plans offer no durable availability promise. Provider terms may change; quotas can stop service. Measure DB growth because full recommendation snapshots can dominate history storage. Keep pools small and monitor actual compute/transfer/build usage; one user is plausibly well within allowances, but that is an inference, not a benchmark. Do not add uptime pings to defeat sleep. A lost Vercel login or removed gate setting can affect access/security; preserve account recovery and verify settings after material deployment changes.

**Exact recommended next implementation task:**

> Implement Deployment Step 1 only: add optional `DATABASE_URL` configuration and dialect-aware engine initialization while preserving `SIDEQUEST_DB_PATH` and the current default SQLite path. Define precedence/conflict validation, keep SQLite foreign-key and transaction hooks SQLite-only, avoid filesystem writes in external-database mode, and add focused configuration tests. Preserve all current SQLite migrations, application contracts, and `backend/app/scoring.py`; run the existing backend suite. Fail clearly for unsupported or unmigrated targets. Do not yet add a PostgreSQL schema, deploy, create provider resources/accounts, add real secrets, or begin V0.2. Record the result in the next numbered report.

Review decisions before later stages: willingness to use Vercel owner login on the phone; acceptance of cold starts/quota suspensions for $0; PostgreSQL production with SQLite retained locally; and backup frequency/loss tolerance. No answer is needed to complete this investigation.

## 11. Investigation preservation

Only this report and the reports index were created/updated. Application source, frontend, dependency files, schema/migrations, frozen scorer and reports 001–010 were preserved. No tests, builds, resource creation, secrets, authentication implementation, deployment workflows, commits, pushes, or deployments were performed. V0.1 remains complete at its accepted baseline; V0.2 is unstarted.
