# 018 — Session Outcome Insights

Date: 2026-10-04 (America/Los_Angeles).
Status: implementation and local verification complete; no deployment.
Preceding research: [017 — Session Outcome Signal Investigation](017_session_outcome_signal_investigation.md).
Production scoring policy remains `v0.1-final-004`.

## 1. Goal

Expose useful, read-only evidence about previous sessions for a selected game, without affecting what Sidequest recommends. The owner can see completed-session quantity, enjoyment variation, recent outcomes and recorded contexts without opening every History record.

All implementation and testing were repository/local operations. No provider, production database, secrets, backup/recovery or account configuration was accessed or changed.

## 2. Relevant Report 017 findings

Report 017 was read before implementation. Enjoyment, completed counts, timestamps and start-context snapshots are usable descriptive evidence. Duration has ambiguous interpretation, progress is free text, and goal completion is not persisted as a reliable session-attributed flag. Existing 3 ratings cannot distinguish deliberate selection from the former preselected default.

No investigated history-ranking model justified adoption. In particular, restricting influence to near ties did not prevent feedback loops. None of M1, M2, M2cap, M3exp, M3linear, M4tie or M5context was connected to production.

## 3. Existing behavior and inspected state

Inspected the report index, session/recommendation reports 006 and 007, library/session models, schemas and routes, History, recommendation UI, Library, finish UI and existing tests. Report 018 was the next available number.

Library already selects one game and shows its quests, with archive/restore behavior. Session completion requires a backend-validated integer rating 1–5, but the frontend previously initialized it to 3. Completed History uses immutable titles/context/recommendation evidence; active history is separate. Game deletion is archival through the API, and database relationships restrict destructive deletion.

The working tree already contained unrelated .gitignore/Visual Studio changes, an untracked Report 017 and its index entry. Those were preserved. Report 017's experiment and tests were already tracked; no research model was changed during this milestone.

## 4. Outcome-summary contract

Added **GET `/api/games/{game_id}/outcomes`** to the existing library router. No existing endpoint contract changed.

| Field | Meaning |
| --- | --- |
| game_id | Existing game identity, including archived games |
| completed_session_count | All-time number of this game's completed sessions across goals |
| average_enjoyment | Arithmetic mean of recorded 1–5 ratings, rounded to two decimals; null when count is zero |
| rating_distribution | Five ordered objects: rating 1–5 and nonnegative count, including zero-count ratings |
| recent_sessions | At most five completed sessions, newest first |
| by_desired_experience | Observed experience groups with count, average and five-rating distribution |
| by_energy | Observed start-energy groups with the same counted aggregate structure |

Each recent item contains session_id, goal_title_snapshot, UTC finished_at, enjoyment_rating, recorded desired_experience and recorded energy. Each context group identifies its dimension value or null for unavailable evidence. Unobserved groups are omitted; missing context never removes the session from overall evidence.

The response is Pydantic typed, disallows extra fields and documents ranges/nullability through OpenAPI. It contains no confidence percentage, success score, prediction, recommendation weight or inferred preference.

Responses:
- 200: existing game, including no-history and archived games.
- 404: game does not exist.
- 422: invalid/nonpositive/out-of-range ID, using existing RecordID validation.
- 409: a completed record contains invalid enjoyment data; a safe message explains that insights are unavailable. Invalid ratings are never silently dropped or replaced.
- Existing database availability handling remains unchanged.

There are no query overrides, writes, new tables or migration.

## 5. Aggregation semantics

1. Select only `game_id = requested game` and `finished_at IS NOT NULL`.
2. Include all completed sessions, across all goals and regardless of current game/goal archive or completion state.
3. Validate each rating as integer 1–5. Historical rating 3 remains included.
4. Overall and context counts/distributions/means use **all completed evidence**, not only the recent five.
5. Recent order is finished_at descending, then session ID descending, matching existing History order. Same-timestamp records have deterministic ordering.
6. Context comes only from `situation_snapshot`; recent goal titles come only from `goal_title_snapshot`. Current energy requirements, tags, goal state or titles do not reinterpret history.
7. Experience groups use progression, chill, challenge, novelty order. Energy uses low, medium, high. An unavailable/null group comes last when needed.
8. Validate each context dimension independently. Missing/invalid dimension values go to its unavailable group. The other dimension may remain usable.
9. Existing UTCDateTime handling normalizes database timestamps to UTC and JSON emits UTC timestamps. The UI renders browser-local date/time, consistent with History.
10. No clock-based cutoff, weighting, decay, confidence gate, future-rating prediction or session-success classification is applied.

The mean is a descriptive arithmetic summary of ordinal ratings, not an empirical enjoyment probability. Two-decimal rounding uses Python round; the UI formats two decimals consistently. Distribution and evidence counts remain visible alongside every displayed average.

Existing database constraints require situation_snapshot to be a JSON object and normally prevent invalid ratings. Tests verify nonobject contexts are rejected at persistence. Objects with missing or invalid dimension values are explicitly represented as unavailable. A defensive type check also handles nonobject projections without borrowing mutable library state. The insights projection does not validate or recompute the unrelated full recommendation snapshot.

## 6. Rating semantics decision

FinishForm now initializes enjoyment_rating to an empty string, rendered as **Choose a rating…**. The select is required. Browser validation prevents ordinary blank submission; an explicit JavaScript integer/range check also rejects programmatic submission and a selection cleared back to the placeholder.

Selecting any 1–5 option converts it to a number and sends the existing finish payload. Duration, progress, optional notes and optional whole-goal completion retain their existing semantics. Backend SessionFinish validation is unchanged.

This is a prospective UI improvement, not historical backfill or provenance tracking. No old ratings were rewritten, marked invalid or excluded. No migration was needed. Other clients sending valid ratings remain permitted by the existing API; the database still does not record whether a selection was made through this UI.

## 7. Backend implementation

`app/outcomes.py` owns aggregation and a named five-session recent limit. `app/outcome_schemas.py` owns the typed descriptive contract. The existing `app/routes.py` exposes the GET route, reusing its session dependency, ID validation and game existence check.

The endpoint performs two SELECTs: game existence and a single completed-session projection. SQLite's normal read BEGIN is also observed in the query test. The projection loads only ID, saved goal title, finish timestamp, rating and situation snapshot; it does not load recommendation JSON or traverse ORM relationships. It performs no commit, flush, mutation or scorer call.

Simple in-memory aggregation over one selected game's evidence is appropriate for the personal scope. Memory/work scale with that game's completed sessions, while response size stays bounded by five recent rows and the small fixed context/rating categories. No N+1 relationships, caching service, chart dependency or infrastructure were added.

## 8. Frontend implementation

In **Library → select game → Show outcome insights**, an inline panel displays:
- completed count and a counted average;
- an accessible enjoyment-distribution table with all five ratings;
- up to five recent session dates/times, ratings, saved goal titles and recorded experience/energy;
- descriptive experience and energy tables with explicit session-count columns;
- an expandable **About this evidence** explanation for sparse/context/default-rating limitations.

It uses existing Sidequest styling and lightweight HTML/CSS. No whole-app redesign or second History page was introduced. The panel is collapsed by default and only fetches when opened for the selected game. Switching games resets it; stale responses are ignored. Opening archived games' insights works normally. Refresh reloads completed evidence; failures have a retry button and are never presented as an empty history.

The existing History and recommendation components were not changed. Existing lifecycle tests now explicitly choose a rating during setup; their prior assertions remain intact.

## 9. Empty/sparse-history behavior

No completed history displays **No completed session history yet.** The UI displays no artificial zero average or empty distribution tables. The API still provides a useful zero count, null mean, five zero distribution bins, and empty recent/context arrays.

One session explicitly shows **1 completed session** and its average **across 1 completed session**. The same quantity remains adjacent for larger samples. Context tables put count next to mean, including one-session groups. No significance labels, confidence percentages or statistical thresholds were introduced. The evidence explanation notes that small groups can vary considerably.

## 10. Context breakdown behavior

Experience and start energy were selected because Report 017 exposed conflicting historical outcomes across these dimensions, and both are recorded directly. Each is a separate descriptive breakdown, not a contextual scoring model or joint conditioning algorithm.

For example, a game with two recorded chill ratings 1 and 3 and one challenge rating 5 shows:
- Chill: two sessions, average 2.00.
- Challenge: one session, average 5.00.

This describes the recorded rows and makes the uneven sample sizes visible. It does not say the owner will enjoy challenge more or claim the context caused the rating. Counts within each dimension partition the completed-session evidence, including unavailable groups.

Social/time breakdowns and finer combined contexts are deferred to avoid crowding a small panel or inventing arbitrary time buckets. Neither was repurposed as a quality signal.

## 11. Historical-data limitations

- Older rating-3 rows may represent explicit selection or acceptance of the old default; all remain included. The panel's expandable explanation acknowledges this.
- Ratings are subjective and ordinal. Their mean can hide variability; the distribution is presented prominently.
- Game-level summaries combine goals and self-selected sessions. The bounded recent list shows saved goal titles, but does not infer per-goal success.
- Start energy/experience may not describe the whole session, and separate marginal groups do not control confounding.
- Duration/progress/goal status do not become synthetic success or quality metrics.
- Missing context cannot be reconstructed from current game fields. It is labeled unavailable.
- Full History retains its existing stricter snapshot contract. Insights do not repair malformed legacy recommendation snapshots or claim they are valid.
- No real production/personal data was examined and no causal or predictive improvement was measured.

## 12. Tests

Final complete backend command from backend, with provider/test PostgreSQL configuration removed from the child process and isolated temporary SQLite import configuration:

```text
.venv/Scripts/python.exe -m pytest -q --tb=short
665 passed, 50 skipped in 27.28s
```

This comprises all 635 previous passing tests plus **30 new outcome tests**. The 50 skips remain 48 opt-in PostgreSQL integration/maintenance cases and two existing SQLite/dialect cases. No PostgreSQL instance, hosted database or backup/restore operation was run; skipped cases are not claimed as passed.

New backend coverage: empty contract/OpenAPI, every 1–5 rating including historical 3, all-time distributions/rounded means, bounded deterministic recent ordering, active exclusion, other-game isolation, multi-goal evidence, immutable snapshot grouping/titles after library edits, sparse groups, unavailable/invalid contexts, existing database JSON constraints, archive/completion preservation, missing/invalid IDs, UTC normalization, exactly two SELECTs/no writes/unchanged SQLite file, forbidden scorer invocation, recommendation invariance after insights and rating-only changes, malformed-rating refusal, and an actual start/finish/History/insights API loop preserving snapshots.

Frontend command from frontend:

```text
npm test -- --run
68 passed (3 files), 12.79s
```

All 51 existing cases and **17 new cases** pass. Coverage includes no history, one session, multiple ratings/distribution, bounded recent outcomes, counted context rows, old-default explanation, unavailable context, loading/retry/refresh, stale-response protection, selected/archived Library integration without shelf-wide calls, read-only endpoint use, blank rating refusal through both click and submit, all five explicit numeric choices and cleared-selection refusal. Existing History/recovery/recommendation loop tests remain functional; their assertions were not weakened.

Verification is automated API/rendering coverage, not a claim of a manual hosted or browser smoke test. No deployment acceptance was repeated.

## 13. Production build verification

`npm run build` passed with Vite 8.3.2: 27 modules transformed, 181ms.
Artifacts: index.html 0.47 kB, CSS 9.80 kB, JS 256.67 kB (gzip 78.52 kB).
No new dependencies were added. Build artifacts remain ignored.

`git diff --check` passed. Git's existing LF/CRLF conversion notices are informational, not whitespace failures.

## 14. Scorer hash verification and historical preservation

Verified frozen `backend/app/scoring.py` SHA-256:

```text
b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a
```

It matches the required before/after value exactly. SHA-256 checks for reports **001–017** match those captured before this milestone. No historical report was edited, including the initially untracked Report 017. This new report is the next immutable record.

## 15. Files changed

Created:
- `backend/app/outcome_schemas.py`
- `backend/app/outcomes.py`
- `backend/tests/test_outcomes_api.py`
- `frontend/src/components/OutcomeInsights.jsx`
- `frontend/src/test/OutcomeInsights.test.jsx`
- `reports/018_session_outcome_insights.md`

Updated:
- `backend/app/routes.py`: descriptive GET endpoint.
- `frontend/src/api.js`: read-only outcome request.
- `frontend/src/views/Library.jsx`: selected-game panel.
- `frontend/src/forms/FinishForm.jsx`: explicit rating selection.
- `frontend/src/styles.css`: panel/table styling.
- `frontend/src/test/Sessions.test.jsx`: explicit rating choice in existing lifecycle setup.
- `README.md`: capability/API/semantics guidance.
- `reports/README.md`: append 018, preserving the existing 017 entry.

No model, migration, scoring, recommendation adapter, History, session backend, deployment, security, database configuration, maintenance or dependency file changed. Existing unrelated owner/editor working-tree changes were left intact. No commit, push or deployment was performed.

## 16. Recommendation ranking is unchanged

**Production recommendation behavior remains identical.** Eligibility, suitability, interest, priority, friction, recency, thresholds, near ties, deterministic ordering and acceptance are unchanged. Outcomes are only returned by their descriptive GET route; no outcome-history adjustment reaches recommendation evaluation.

Existing scoring fixtures and integration tests pass. A new fixed-clock regression confirms that reading insights and changing only a historical enjoyment rating leave the complete recommendation response identical. Reading insights does not write session history.

## 17. Deferred questions and recommended next milestone

The acceptance criteria for this local implementation are satisfied. The feature is ready for review, with hosted verification/deployment requiring separate authorization.

Recommended next product milestone: review insight usefulness and rating semantics using owner-reviewed examples, then refine only descriptive presentation if needed. Decide whether social/time or goal-specific summaries would answer a real question before expanding the contract. Do not adopt outcome ranking merely because evidence is now visible.

Potential future research includes context confounding, explicitly chosen-rating provenance, ordinal mean presentation and large-history SQL aggregation. No schema change, new outcome metric, ranking model, account system, or next milestone was started.

