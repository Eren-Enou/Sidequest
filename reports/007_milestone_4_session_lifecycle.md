# 007: Milestone 4 session lifecycle and history API

Date: 2026-10-03 (America/Los_Angeles). Status: complete; acceptance satisfied; ready for Milestone 5 review. Milestone 5 has not begun.

Reviewed PROJECT.md, IMPLEMENTATION_PLAN.md and reports [004](004_milestone_1_final_policy.md), [005](005_milestone_2_database_library_api.md), [006](006_milestone_3_recommendation_api.md). Reports 001-006 were preserved. Production scorer v0.1-final-004 remains frozen.

## Scope and files

Implemented Recommendation -> Start -> Active Session -> Finish -> History through FastAPI and the existing SQLite schema. No React, analytics, learned policy, authentication, infrastructure, separate recommendation-history table, or event log was added.

Created app/session_routes.py, app/session_schemas.py, and tests/test_sessions_api.py. Updated app/main.py to register the session router, tests/test_library_api.py to allow the authorized session route scope, README.md, IMPLEMENTATION_PLAN.md, and reports/README.md. Existing model, database configuration, migration, recommendation adapter/projection, and scorer implementations were reused without edits. No new dependencies or migrations were necessary.

## Endpoint contracts

| Method | Route | Success / behavior |
| --- | --- | --- |
| POST | /api/sessions/start | 201 SessionRead; revalidate and begin accepted choice |
| GET | /api/sessions/active | 200 SessionRead or JSON null when none |
| POST | /api/sessions/{session_id}/finish | 200 SessionRead; complete exactly once |
| GET | /api/sessions | 200 list of completed sessions |
| GET | /api/sessions/{session_id} | 200 active/completed SessionRead; missing ID returns 404 |

Start request:

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

IDs are strict positive SQLite-range integers. The nested situation reuses RecommendationRequest. Unknown fields (including client snapshots, scores, timestamps) are rejected with 422.

Finish request:

```json
{
  "actual_duration_minutes": 30,
  "enjoyment_rating": 4,
  "progress": "Harvested crops",
  "notes": "Save seeds next time",
  "mark_goal_completed": false
}
```

Duration is required, strictly integer, positive, and within SQLite storage range. Enjoyment is a strict integer 1-5. Progress is required strict string, trimmed and nonblank. Notes are optional strict string or null: omission/null stores null, empty string is preserved. mark_goal_completed is a strict boolean defaulting false. Missing/invalid/extra fields return 422 without changing the active session.

## Start-time revalidation and selection

The lifecycle writer obtains a SQLite BEGIN IMMEDIATE transaction before reading state. Starting checks for an existing active session, confirms both live records exist (404 otherwise), and verifies their relationship (409 if mismatched). It captures one aware backend operation timestamp and normalizes it to UTC. Start cannot precede the current game/goal creation/update timestamps; this guards against a backward clock producing evidence before the state it describes.

The Milestone 3 evaluate adapter loads current library/history and invokes the frozen scorer once at this timestamp. Its response projection is reused. Selection must match both game and goal IDs in the returned recommendations set. A near-equivalent non-winner is allowed. An eligible suitable candidate outside the near-tie band is not a current choice and is rejected, as are excluded/unsuitable pairs. no_eligible and no_good_fit cannot start a session.

A failed recommendation-choice check returns 409 with a message requesting a fresh recommendation and the complete recalculated response under detail.recommendation. The endpoint does not trust the prior client result or require a recommendation token. If library edits leave a choice valid, the session starts with fresh evidence; edits that remove it from current choices cause conflict.

An active-session conflict includes active_session_id. An identity mismatch returns relationship guidance. These preconditions need not invoke scoring because no session can start in those states.

## Explicit snapshot schema and preservation

The existing PlaySession fields store IDs, current game/goal title snapshots, started_at, and these JSON objects:

```text
situation_snapshot: RecommendationRequest
recommendation_snapshot:
  snapshot_version: 1 (required)
  selected: ScoredCandidateRead
  evaluation: RecommendationResponse
```

Evaluation is the full Milestone 3 projection: context, status, engine_version, evaluated_at, weights, heuristic thresholds, winner, accepted alternatives, eligible ranking/audit, and exclusions. Selected holds the actual chosen candidate, total, suitability/decision/reasons, breakdown, and each factor's weight, inputs, points, and explanation. This preserves near-equivalent selection independently of deterministic display winner. Titles and context are stored explicitly rather than through arbitrary ORM serialization.

RecommendationSnapshot validates the supported version, accepted outcome, membership/suitability of selection, winner matching first choice, choice membership in saved ranking, breakdown totals, factor contributions, and aware evaluation time. SessionRead additionally validates IDs/titles against selected evidence, saved context against evaluation, start/evaluation time equality, and temporal ordering. Validation runs before commit at start/finish and on API reads. Corrupted or unsupported payloads are not silently treated as valid evidence.

There is no snapshot-update or session-edit endpoint. Finish changes completion fields only. History reads saved JSON without invoking scoring or loading live titles. Later title, estimate, interest, priority, tag, friction, and archive changes cannot rewrite the stored snapshot through this API. Tests also forbid scorer invocation during historical retrieval, proving history does not recalculate under a later implementation.

These checks validate saved evidence structure/consistency, not a second scoring policy. Suitability, acceptance, factor calculations and ranking remain exclusively owned by the frozen engine.

## Active recovery and concurrency

Active retrieval queries finished_at IS NULL; no in-memory flag is used. The existing partial unique index independently prevents two active rows, including external/direct writes. BEGIN IMMEDIATE reserves the SQLite writer before active checks and recommendation reads, serializing lifecycle writers. A second concurrent start observes the committed active row and returns 409. Transactions/sessions/connections close and roll back on exceptions; the begin-immediate connection flag is cleared on cleanup.

The integration concurrency test uses two real threads, separate TestClients/connections, a barrier, and the same temporary file. Results are exactly one 201 and one 409, with one stored row. Concurrent finishes likewise yield one 200 and one 409, preserving the first accepted progress/result. The inherited five-second SQLite lock timeout may return 503 with retry guidance under sustained unrelated writer contention; there is no retry queue.

Reopening the application recovers the same active session; completing it and reopening again preserves its history and snapshots.

## Finish transaction and temporal behavior

Finish captures one aware UTC operation timestamp and checks session existence, unfinished state, and finished_at >= started_at. It records user-confirmed duration, enjoyment, trimmed progress, and optional notes. Elapsed duration is not forced to equal actual_duration_minutes; the product explicitly accepts a user-confirmed value. Finishing at the same timestamp is allowed by the existing schema, provided the submitted duration is positive.

With mark_goal_completed=true, goal status/completed_at/updated_at and session completion are flushed and committed in one transaction. An already-completed goal stays completed without overwriting its completion timestamp. An archived game/goal blocks optional completion with 409 and leaves the session active; users can restore it or finish without completing the goal. Goal completion time cannot precede the current goal state. Ordinary finish remains allowed after live records are archived.

Database failure during either write rolls back the entire transaction. A test injects an IntegrityError on the session UPDATE while optional goal completion is pending and confirms both the goal and session remain unchanged. Existing constraint-conflict handling returns 409 without exposing SQL details.

Repeat finish is explicitly a conflict (409), not an idempotent overwrite or new row. There is no history-edit path. The writer lock also prevents concurrent finish requests from both changing the same active row.

## History and recency feedback

GET /api/sessions returns completed rows only, ordered finished_at descending then ID descending. Individual retrieval accepts active or completed rows and returns 404 for missing IDs. Responses expose snapshot titles, start/finish, actual duration, enjoyment, progress, notes, saved situation, and complete saved explanation. History remains readable after game/goal archive or rename. No pagination, search, aggregation or analytics was introduced.

The end-to-end test seeds Moonlit Orchard -> Harvest autumn crops, requests a recommendation, starts it, checks active retrieval, finishes, and recommends again with a controlled clock. Initial score is 84.25 and recent_play is 0. An unfinished session leaves the recommendation unchanged. Immediately after finish, recent_play is -3 and score is 81.25, with no special update/cache logic; the unchanged Milestone 3 MAX(completed finished_at) query provides feedback. The start-time snapshot stays at its original score/explanation.

## Complete test results

Command from backend: `.venv/Scripts/python.exe -m pytest -q`.

**410 passed in 17.00s**, no failures or warnings: all 345 previous cases plus 65 new lifecycle cases. The only adjustment to a prior test is its route-scope assertion permitting the newly authorized session endpoints; its frozen-score hash protection remains.

New tests cover all 30 requested behaviors: valid start; non-winner alternative; excluded/unsuitable/outside-band rejection; stale-library rejection; single active and concurrent starts; active/no-active/detail retrieval; restart recovery; finish validations and notes; optional completion; injected database rollback; duplicate/concurrent finish; deterministic history ordering; title/recommendation/engine-version preservation through edits/archives; version/structure/evidence validation; fixed and offset clocks/one capture; impossible ordering; completed/unfinished recency; full API loop; completed-history reopen; and composite foreign-key enforcement. Additional start-validation and history-no-recomputation checks protect server-owned evidence.

All automated tests use isolated migrated temporary SQLite files. No test uses the personal library database. Scoring.py SHA-256 remains:

`b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a`

## Decisions and known limitations

- Reused the initial schema and Milestone 3 projection; snapshots are versioned inside the existing JSON column. No migration or additional persistence abstraction was needed.
- Store the full evaluation audit as well as selected evidence. This is larger than a selected-only snapshot but preserves alternatives and reasoning at the moment of choice. A small local library makes this acceptable.
- Snapshot immutability is enforced by API write paths, not SQL triggers. External database tools can still modify JSON; application validation detects structural inconsistencies, not every possible malicious rewrite.
- Pre-Milestone-4 test fixtures used placeholder snapshot objects. They are not valid version-1 API session history. No fabricated migration/backfill reconstructs explanations that were never stored. Imported/manually inserted legacy or corrupted rows can fail response validation; a future explicit format migration is needed if actual legacy data exists.
- Version-1 readers reuse the current recommendation schemas. Future policy/schema changes must preserve old snapshot readers or add explicit version handling; never recompute historical explanations to fit a new schema.
- Start conflicts reflect current recommendation membership, not a comparison with a client revision. A changed but still accepted candidate is started using refreshed evidence.
- There is no cancellation, history correction, duplicate-start idempotency key, pagination, elapsed-duration suggestion UI, or frontend. These are not required for this milestone.
- SQLite serializes writers; this is suitable for the local personal scope. Extreme contention returns existing retry guidance, rather than adding infrastructure.

## Preservation and readiness

Historical report SHA-256 values match those captured before implementation:

| Report | SHA-256 |
| --- | --- |
| 001 | 321498eabc0741db9eac22988981bbc3e7ec948035369c732f0c1777b7b299bb |
| 002 | 100799e3a6df1d49614a3321d84a5add048fcab5b6f327135ab3543d2596f7aa |
| 003 | e6f32387a0c3e2fc412d808b237d9f22f02fab4cba10d2a50660de37c08ef390 |
| 004 | 714ae26c0da3adef95bb24c4676ac95c2a3a013921042a3da70e5f3170f0ae4a |
| 005 | 1f20a3e7aada67d1ee6b045a88d333beb97810475bf5366b8ae039113845b213 |
| 006 | ff6662f27c0a7a2ac77dbfc4db74fe8e3ebe31be12467f3c745e9ab9d8664d0b |

Milestone 4 acceptance criteria are satisfied: the full API loop works, one active session is durable and concurrency-safe, finish is atomic, and historical evidence survives restarts and library changes. No scoring policy change was required. Milestone 5 can build the React library/recommendation interface against these APIs after separate user review. No Milestone 5 work was started.
