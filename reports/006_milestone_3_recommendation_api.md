# 006: Milestone 3 recommendation API

Date: 2026-10-03 (America/Los_Angeles). Status: complete; acceptance satisfied; ready for Milestone 4 review. Milestone 4 has not begun.

References: PROJECT.md, IMPLEMENTATION_PLAN.md, [004](004_milestone_1_final_policy.md), [005](005_milestone_2_database_library_api.md). Historical reports 001-005 were not edited. Production policy remains v0.1-final-004.

## Endpoint and validation

POST `/api/recommendations` returns 200 for all four valid product outcomes, including abstention. Invalid requests return 422 using FastAPI/Pydantic validation. JSON must contain exactly four required fields:

| Field | Accepted values |
| --- | --- |
| available_minutes | Strict positive integer; booleans, strings, fractional values rejected |
| energy | low / medium / high |
| social_preference | solo / social / either |
| desired_experience | progression / chill / challenge / novelty |

Available minutes are transient scorer input, so no SQLite integer storage limit is imposed. Request-supplied timestamps and policy overrides are not accepted.

## Response contract

| Field | Meaning |
| --- | --- |
| status | Frozen engine's no_eligible / no_good_fit / clear_recommendation / multiple_equivalent |
| engine_version, evaluated_at | Frozen policy identifier and its normalized UTC evaluation time |
| context | Validated situation inputs |
| weights, minimum_suitability, near_tie_margin | Actual engine configuration; thresholds remain heuristic |
| winner | Frozen engine's first display choice, or null on abstention |
| recommendations | Ordered suitable choices within the frozen near-tie margin |
| ranked | Every eligible scored candidate, including unsuitable audit entries |
| excluded | Candidate identity/inputs and all engine-provided hard-exclusion reasons |

Each scored entry includes the complete candidate, total `score`, `suitability`, `suitable`, `unsuitable_reasons`, seven-factor `breakdown`, and ordered `factors`. Each factor has name, points, weight, input dictionary, and reason. Datetimes become UTC JSON strings and domain tuples become JSON arrays. Scores serialize as numbers with no added rounding. The breakdown sums to total; suitability is the frozen sum of time, energy, and experience contributions.

The projection does not calculate a new score, reorder results, infer statuses, or apply another gate. In particular, winner is taken from the engine's recommendations, not from the raw ranking. In multiple_equivalent, winner means first deterministic display choice, not a uniquely superior recommendation. Both abstention states have null winner and empty recommendations; no_good_fit preserves eligible unsuitable entries and explanations in ranked.

## Persisted mapping and recency

One synchronous SQL query joins Game/Goal pairs and outer-joins a grouped completed-session subquery. The adapter returns plain immutable Candidate objects:

| Domain field | Persistence source |
| --- | --- |
| game_id, goal_id, game_title, goal_title | Game/Goal IDs and current titles |
| interest, friction | Game.current_interest and Game.friction |
| energy_required, social_mode, experience_tags | Game fields; tags converted to tuple |
| estimated_minutes, goal_priority | Goal.estimated_minutes and Goal.priority |
| game_archived, goal_status | Game.archived_at is not null; Goal.status |
| last_completed_session_at | MAX(PlaySession.finished_at), grouped by game_id, excluding null finishes |

History recency is shared across every goal of a game; it is not latest insert ID, latest start, or per-goal history. The UTC datetime column type also converts the aggregate result to an aware datetime. No completed history yields null. Unfinished sessions never count, even if started more recently. Completed history remains relevant even when its original goal is no longer active.

All persisted pairs are loaded for audit. Only active pairs survive the scorer's lifecycle eligibility rules; this implements the requested active recommendation semantics while preserving the scorer's archived/completed exclusions. No duplicate lifecycle, social, time, energy, or suitability policy is embedded in SQL. Games without any goals produce no synthetic candidates or exclusion entries.

## Time, persistence, and architecture

`get_evaluation_time` captures `utcnow()` once per request. FastAPI dependency overrides allow fixed aware timestamps in tests. That one value is supplied to the scorer, which uses it for recency and returns its normalized UTC value for response metadata. The adapter never reads the clock. A spy test confirms exactly one clock capture and exactly one frozen `scoring.recommend` invocation per valid request.

The endpoint is a read/evaluate operation. No ORM objects are changed, flushed, or committed; the per-request database session closes its read transaction. No recommendation table, snapshots, schema changes, migration, dependencies, or API session transitions were introduced. Integration checks compare both SQLite logical dumps and file SHA-256 before/after repeated requests and application reopen.

New modules: app/recommendations.py (explicit adapter and single scorer call), app/recommendation_schemas.py (JSON contract/projection), tests/test_recommendation_api.py. Updated app/routes.py and app/main.py expose/document the route. README.md, IMPLEMENTATION_PLAN.md, and reports/README.md record completion. The prior library test's route-scope assertion was expanded to allow precisely this authorized recommendation endpoint; its other scope protections remain. Existing test cases were not removed.

## Example result

For Moonlit Orchard (interest 4, friction 1, low energy, solo, chill/progression) and Harvest autumn crops (30 minutes, priority 2), no completed history, evaluate at 2026-10-03T19:00:00Z:

```json
{"available_minutes":45,"energy":"low","social_preference":"solo","desired_experience":"progression"}
```

Result excerpt (the actual response also includes candidate inputs, every factor's inputs/weight/reason, configuration, ranked entries, and recommendation choices):

```json
{
  "status": "clear_recommendation",
  "engine_version": "v0.1-final-004",
  "evaluated_at": "2026-10-03T19:00:00Z",
  "winner": {
    "score": 84.25,
    "suitability": 60.0,
    "suitable": true,
    "unsuitable_reasons": [],
    "breakdown": {
      "interest": 18.75,
      "goal_priority": 7.5,
      "time_fit": 10.0,
      "energy_fit": 30.0,
      "experience_fit": 20.0,
      "friction": -2.0,
      "recent_play": 0.0
    }
  },
  "excluded": []
}
```

The goal uses two-thirds of the available time, so gets full time points; energy is sufficient and the experience matches. Interest and priority add preference points; friction subtracts two. No history produces no recency penalty. This was generated through the actual response projection with the frozen scorer and matches the persisted-library integration example.

## Tests and frozen-policy regression evidence

Command from backend: `.venv/Scripts/python.exe -m pytest -q`.

**345 passed in 10.86s**: all 315 previous cases (239 Milestone 1, 76 Milestone 2) plus 30 recommendation integration cases. Focused integration run: 30 passed in 3.70s. No failures or warnings.

The new cases cover all 20 requested integration behaviors: expected persisted winner; candidate mapping and direct-scorer totals, suitability, factors, inputs and explanations; latest completed finish across goals; unfinished history ignored; archived game, archived goal and completed goal; insufficient time and both directions of social incompatibility; empty library/no-goal game; all four outcomes; stable near-tie ordering and repeated fixed-time results; score sums; policy version; unchanged database; and equivalent results after reopening. Additional validation cases cover missing fields and strict values. Tests explicitly protect removal of the total-score gate and prevent an unsuitable raw leader from becoming the displayed winner.

All API tests use migrated temporary isolated SQLite files. Completed/active history is inserted directly through ORM fixtures because session lifecycle routes are outside scope.

Frozen scorer SHA-256 after implementation:

`b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a`

This exactly matches Report 005 and the user's required hash. scoring.py was not edited during this milestone; existing Git modifications to it predate this task. No integration incompatibility or scoring change was needed.

## Limitations and readiness

Full audits intentionally include all persisted goal pairs; response size grows with library size. Pagination and audit truncation are deferred for this small personal application. There is no synthetic game-only recommendation and no per-goal energy/social/tag override. The endpoint exposes deterministic policy results, not calibrated confidence or guaranteed enjoyment. Existing suitability and near-tie heuristics remain unchanged.

Actual recommendations use the live backend clock, so recency can change scores between requests; reproducibility requires identical inputs, persisted state, and evaluation time. Returned recommendations are transient and can become outdated after library edits. There is no session creation/history API or recommendation persistence yet.

Milestone 3 acceptance criteria are satisfied. Milestone 4 can reuse this adapter/projection while implementing start-time revalidation and immutable session snapshots, but requires separate authorization. No Milestone 4 implementation was started.
