# 016 — Vercel routing compatibility correction

Date: 2026-10-03 (America/Los_Angeles).
Scope: fix the staging-import routing rejection only.
Status: repository correction verified; ready for owner commit/push and retry.
**No successful deployment has occurred yet.** No import, deployment, cloud
resource creation, Neon change, secret configuration or personal-data action
was performed in this task.

## Live provider evidence

The owner reported that Vercel New Project detected Services, backend FastAPI
(Internal), frontend Vite, and configuration from vercel.json, then rejected:

```text
Rewrite at index 0 has invalid `source` pattern "^/api(?:/.*)?$".
```

No deployment was created. This is stronger evidence than the local structural
checks recorded in reports 014/015. Those historical reports remain unchanged.

## Root cause and current official syntax

The source was written as an anchored raw regex and checked with Python
`re.fullmatch`. Vercel's rewrite source parser interprets a path-pattern grammar;
the standalone optional noncapturing group in this source is rejected by its
parser. Python acceptance did not validate that grammar. The anchored frontend
fallback had the same class of syntax problem and also needed correction.

Current [Services routing documentation](https://vercel.com/docs/services/routing)
shows `/api/(.*)` followed by `/(.*)` with service destination objects. Service
selection is first-match, preserves the original path and is final: a backend
404 does not try the frontend. An explicit `/api` rule covers the bare prefix,
which `/api/(.*)` alone does not match.

[Rewrite documentation](https://vercel.com/docs/routing/rewrites) supports named
path parameters containing patterns, including a negative-lookahead example
`/:path((?!uk/).*)`. The frontend fallback now uses that supported pattern form
with its existing API and assets exclusions. The same page also contains raw
anchored-regex examples; those do not override the live rejection of this exact
source. This fix uses patterns validated by the published routing parser rather
than assuming all JavaScript or Python regular expressions are accepted.

## Old routing configuration

Top-level:

```json
"rewrites": [
  { "source": "^/api(?:/.*)?$", "destination": { "service": "backend" } },
  { "source": "/(.*)", "destination": { "service": "frontend" } }
]
```

Frontend-service fallback:

```json
"rewrites": [
  { "source": "^/(?!api(?:/|$)|assets(?:/|$)).*$", "destination": "/index.html" }
]
```

## New routing configuration

Top-level:

```json
"rewrites": [
  { "source": "/api", "destination": { "service": "backend" } },
  { "source": "/api/(.*)", "destination": { "service": "backend" } },
  { "source": "/(.*)", "destination": { "service": "frontend" } }
]
```

Frontend-service fallback:

```json
"rewrites": [
  { "source": "/:path((?!api(?:/|$)|assets(?:/|$)).*)", "destination": "/index.html" }
]
```

Only these sources and the extra bare-prefix rule changed in vercel.json.
Services, roots, framework settings, build commands, backend entrypoint,
headers, protection preparation and bundle settings are unchanged.

## API isolation and preserved contract

- `/api` selects backend through the first rule.
- `/api/`, `/api/games`, `/api/sessions/start`, nested finish paths, unknown API
  paths and repeated slashes under `/api/` select backend through the second.
- Original paths and FastAPI route declarations remain unchanged. No prefix
  stripping, destination path override, external origin or redirect was added.
- The frontend catch-all is last. Selected backend requests cannot fall through
  to it when FastAPI returns a 404/405.
- Frontend fallback separately excludes the `api` and `assets` path segments;
  missing assets cannot become React HTML. Near-prefix names such as `/apiary`,
  `/apiculture` and `/assets-gallery` remain frontend paths.

## Parser verification and tests changed

For a direct local reproduction, installed the published
`@vercel/routing-utils@6.6.0` into a temporary directory outside the repository,
without authentication or deployment. `getTransformedRoutes` reproduced the
owner's exact error for the old API rule and accepted both the new top-level
rewrites/headers and the new frontend fallback. This is a published-tool check,
not a claim that Vercel's hosted project parser or runtime has already accepted
the next import.

Replaced raw source matching in `test_production_packaging.py` with compilation
by pinned `path-to-regexp@6.3.0`, the patched parser also used in Vercel's
[routing implementation](https://github.com/vercel/vercel/blob/main/packages/routing-utils/src/superstatic.ts).
Compilation uses Vercel's strict, case-sensitive, slash-delimited options;
only emitted regexes are then matched locally. Both old sources must fail
compilation. Config assertions enforce the explicit documented rule order.
Cases cover bare/trailing/nested/unknown/repeated-slash API paths, session start,
frontend near-prefix boundaries and missing assets. Header source also compiles.

The parser is a development-only dependency in frontend/package.json/lock, used
by Python packaging tests through Node; it is not imported by the browser app.
Run `npm ci` in frontend before the full backend packaging suite. No frontend
source, application build command or runtime dependency changed. The persistent
dependency uses the patched parser rather than introducing the routing utility's
legacy parser dependency into the application repository.

Focused packaging/routing result: **26 passed in 3.59 seconds** (previous 17
cases preserved/updated plus nine added cases). No provider UI settings were
mocked as evidence of a successful deployment.

## Complete regressions

| Check | Result |
| --- | --- |
| Complete backend `pytest -q --tb=short` | **607 passed, 2 intentional skips**, 64.80 seconds |
| Existing Step 4 backend baseline | All 598 previously passing cases remain passing |
| Real PostgreSQL | All 48 existing persistence/maintenance cases passed on isolated local PostgreSQL 16.3; includes real transfer and backup/restore |
| Focused packaging/routing | **26 passed** |
| Complete frontend `npm test -- --run` | **51 passed**, two files, 11.92 seconds |
| Production frontend `npm run build` | Passed, Vite 8.3.2, 26 modules; same HTML/CSS/JS artifact names and sizes as before |
| Published Vercel routing utility | New top-level and frontend rules accepted; old API rejection reproduced exactly |
| `git diff --check` | Passed |

Tests used only temporary SQLite paths and disposable PostgreSQL databases in
the separate loopback cluster from Step 4, restarted for this task. The cluster
was stopped after testing; the installed PostgreSQL service and personal data
were not modified. No cloud connection was used.

## Frozen scorer and historical preservation

Scorer SHA-256 remains exactly:

```text
b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a
```

Compared pre-task and final SHA-256 values for reports **001–015: all 15
unchanged**. No production Python, schema, scoring, database, session,
authentication-preparation or frontend behavior changed. DEPLOYMENT.md remains
unchanged. This new report records the live-discovered correction instead of
rewriting reports 014/015 to imply earlier provider acceptance.

## Files changed and next action

- vercel.json: supported API and fallback source syntax.
- backend/tests/test_production_packaging.py: parser-backed syntax and boundary checks.
- frontend/package.json and package-lock.json: one pinned development-only parser.
- reports/README.md: new numbered index entry.
- reports/016_vercel_routing_compatibility_fix.md: this historical record.

Ready for the owner to **commit/push and retry Vercel import**. Hosted parser
acceptance, build/runtime success and the security/routing acceptance checklist
remain unverified until that retry and separately authorized staging work.
No deployment was attempted here. Stop after this compatibility correction.
