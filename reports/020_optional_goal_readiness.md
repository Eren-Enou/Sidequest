# 020: Optional Current/Later Goal Readiness

Date: 2026-10-04 (America/Los_Angeles). Status: implemented and verified locally; deployment not performed.

References: [019](019_goal_progression_model_investigation.md), [004](004_milestone_1_final_policy.md), [005](005_milestone_2_database_library_api.md), [006](006_milestone_3_recommendation_api.md), [007](007_milestone_4_session_lifecycle.md), [008](008_milestone_5_react_library_recommendation.md), [010](010_v0.1_snapshot_validation_fix.md), [017](017_session_outcome_signal_investigation.md), [018](018_session_outcome_insights.md), PROJECT.md and current implementation.

## 1. Executive summary

Implemented one additional fact: an active goal can be **current** or deliberately saved for **later**. Multiple current goals remain valid. Later goals are withheld before scoring and cannot start new sessions. Existing goals default to current, frozen calculations remain unchanged, and existing active sessions/history remain usable.

The baseline working tree contained uncommitted Report 019, its two research files and its index entry. Last commit was `53c02f4 Add session outcome insights`; Report 019 was not tracked/committed. That work was preserved. Report 020 was the next unused number. Reports 001–019 and both migration-001 files remain unchanged.

## 2. Product behavior implemented

Create current goals by default, optionally create later goals, explicitly move active goals in either direction, and see separate Library sections. Later is a planning exclusion, never a lower score. No successor, queue, dependency, ordering, counter, recurrence, progress bar, metadata override or outcome ranking was introduced.

## 3. Current/later semantics

Current means ready to consider for a session, subject to all existing rules. Later means saved for the future and not considered yet. Current is neither exclusive focus nor a guarantee of recommendation. Several current and several later goals may coexist for a game.

## 4. Lifecycle/readiness separation

Lifecycle remains active/completed/archived. Readiness matters only for active goals under an unarchived parent. Completed/archived goals and archived games retain the frozen lifecycle exclusions regardless of readiness. Parent archival has precedence in the audit; no score is produced for an inactive pair.

Completed/archived records may retain their prior readiness as inert metadata. Readiness PATCH on those records returns 409; restore/reopen is the explicit action for making them usable again. Other metadata edits remain allowed as before. Active readiness edits under an archived parent cannot make the goal recommendable; parent restoration restrictions remain intact.

## 5. Database/schema changes

Goal gains `readiness`: non-null, server and ORM default current, allowed values current/later. Existing IDs, relationships, lifecycle/timestamps, session uniqueness and saved JSON remain intact. No table or other domain column was added. Migration SQL remains the authoritative constrained schema.

## 6. SQLite migration

New `backend/migrations/002_goal_readiness.sql` uses one ALTER TABLE ADD COLUMN with TEXT NOT NULL DEFAULT 'current' and named CHECK `ck_goal_readiness`. All existing active/completed/archived goals read current. No table rebuild, FK disabling, ID regeneration or JSON rewrite is needed.

## 7. PostgreSQL migration

New `backend/migrations/postgresql/002_goal_readiness.sql` retains the required dialect header and adds VARCHAR(7) with the same default/nullability/CHECK semantics. Real PostgreSQL 18 execution passed on a temporary cluster bound only to loopback. Production Neon was never accessed.

Both streams reach migration 002 using the unchanged runner: explicit invocation, transaction/lock handling, contiguous numbering, dialect checks, applied-history checksums and CRLF/LF normalization. Migration 001 files and their checksums were not edited or regenerated.

## 8. API changes

Existing goal routes remain; no progression service or new route is needed. POST `/api/goals` accepts optional readiness default current. Goal responses expose it. PATCH `/api/goals/{id}` accepts an explicit readiness update for active goals. Invalid values/null return 422; inactive readiness edits return 409. Omitting readiness on PATCH preserves it. Metadata edits never promote a later goal.

GET goal/list responses retain existing lifecycle filters. Completion and archival preserve readiness as inert metadata; restoring/reopening inactive goals resets it to current. Restore of an already-active later goal is an idempotent no-op; promotion uses PATCH. New clients need no readiness field in session-start requests.

## 9. Recommendation eligibility boundary

The persisted adapter loads the same single query of game/goal pairs and completed-game recency. It partitions active later pairs under active games before the single frozen scorer call. Only current active pairs can be scored. Inactive pairs continue through the frozen scorer for lifecycle exclusions.

Readiness is not passed as a new Candidate lifecycle value. Candidate still accepts only active/completed/archived. No weights, suitability, durations, penalties, ordering, near ties or outcome calculations changed. Current pairs retain exactly their original factor values; the set of competing candidates intentionally changes after an explicit move to later.

## 10. Audit/explanation behavior

Later pairs appear in the existing `excluded` collection with Candidate identity/input metadata and this reason:

> Goal is planned for later and is not currently considered; make it current to recommend it.

There is no score, suitability or factor breakdown for such a pair. The adapter merges these unscored exclusions in deterministic goal-ID/game-ID order. Existing hard exclusions and eligible fit audits remain intact. All-later libraries produce no_eligible; a later goal is never promoted merely to avoid abstention.

Current recommendation responses explicitly identify `eligibility_version="goal-readiness-020"` while `engine_version` remains `v0.1-final-004`. This is a deliberate eligibility contract change outside the frozen engine, not a claim that engine hash alone describes the whole API policy. Candidate metadata is unchanged; readiness exclusion reasons and the eligibility marker provide the needed evidence without duplicating live Goal fields into old candidate schemas.

## 11. Session-start readiness recheck

Start still acquires the existing SQLite writer reservation or PostgreSQL transaction advisory lock shared by library writes. It re-evaluates persisted state using the readiness-aware adapter and accepts only a member of the current recommendation choices. If a previously recommended goal is moved later, start returns the existing 409 stale-choice response with a refreshed recommendation and later exclusion reason. No row is inserted.

No separate weak preflight or client-supplied readiness assertion is trusted. Existing parent/lifecycle/time/social/suitability and accepted-band validation remains authoritative. Existing concurrent writer/session tests pass on both dialects.

## 12. Active-session behavior

Readiness affects future starts only. An already-active session can be read/reloaded and finished after its goal moves later, including optional explicit whole-goal completion. Its snapshot is not rewritten. No cancellation or automatic successor is introduced. The finish route's existing archive/timestamp/atomicity restrictions remain unchanged.

## 13. Historical snapshot compatibility

Kept the original `RecommendationResponse` and `RecommendationSnapshot` version-1 reader. Added small subclasses for the current eligibility response and new snapshot **version 2**, whose evaluation requires the explicit eligibility marker. SessionRead uses a discriminator on snapshot_version to read either version. The existing numerical consistency validator is inherited, including Report 010's tolerances and exact evidence membership checks.

New starts write version 2. Existing version-1 JSON is not backfilled or rewritten; no readiness is inferred from live rows. New snapshot selected metadata remains the frozen Candidate shape; accepted membership under the recorded eligibility version establishes that the selected goal was current at start. Historical candidate JSON does not require a readiness field.

Tests read unchanged version-1 history after migration and readiness/title changes, compare full snapshots, exercise numerical consistency on old evidence, and reject missing/wrong versions and missing version-2 eligibility markers. Migration tests compare saved JSON exactly. New v2 corruption tests continue checking membership, score, factors, context and timestamp, rather than accidentally passing solely on a version mismatch.

## 14. Restore/reopen semantics

Completed or archived → active + current, with completed_at cleared as before. UI actions explicitly say "Reopen goal as current" or "Restore goal as current." Parent must be unarchived. Repeated restore on an already-active record stays a no-op, preserving existing idempotence. Restoring a game alone does not reset its child goals' readiness.

## 15. Library UI

Small additions to the existing quest journal: Current goals, Later, Completed and Archived sections with the existing cards/actions. Current copy explicitly allows several goals. Later copy explains recommendation exclusion. Active cards offer Move to later/Make current. Goal forms default current and allow an intentional later selection. Inactive editors do not offer readiness changes.

The form omits readiness on metadata-only edits unless the owner changes the selector; this avoids sending a stale readiness value unnecessarily. Existing saving locks/ref prevent duplicate actions. Failed writes retain the displayed grouping and show errors; successful writes are followed by authoritative reload. Existing saved-but-refresh-failed wording and stale goal-read protection remain.

No global redesign, new framework, drag-and-drop, sort controls or CSS system was added. Completed/archived sections remain visible rather than adding another collapse interaction.

## 16. All-later/no-current UX

All active goals later: "All active goals for this game are saved for later. Make one current when you're ready to work on it." No-current with completed/archived goals offers add/reopen guidance. No goals retains its own add-goal empty state. Archived games retain restore-parent guidance.

Current-but-too-long/social-incompatible goals remain current in Library; Tonight explains their actual exclusions. Unsuitable eligible goals remain in the fit audit. Tonight's ordinary no-eligible guidance now includes reviewing current/later goals, while each withheld pair has its specific explanation. Later is never displayed with numerical score or labeled low priority.

## 17. Priority interaction

Priority remains importance among eligible suitable choices. Tests admit low-priority current goals while withholding higher-priority later goals before the scorer sees them. Priority edits do not alter readiness. Multiple current near ties remain valid.

## 18. Time interaction

Current 120-minute goal with 30 minutes available is excluded for time. Later 20-minute high-priority goal remains withheld for readiness, even with a perfect duration fit. The result can be no_eligible. Estimates retain their useful-session-chunk meaning; no shortening, override or automatic promotion occurs.

## 19. Repeatable-goal behavior

Practice goals remain ordinary active current goals across sessions unless the owner explicitly completes them or moves them later. There is no repeatable flag, counter, schedule, automatic reopening or successor selection. Whole-goal completion remains explicit.

## 20. Outcome Insights regression

No outcome aggregation or frontend insight component changed. Full existing outcome tests pass. New integration tests compare the entire outcomes response after readiness/title changes and after reading old-version history: counts, mean/distribution, recent-session evidence and energy/experience groups are unchanged. The browser shows the fictional completed rating 4 and recorded medium/progression context. No outcome effect reaches ranking.

## 21. Browser verification

Used only `http://127.0.0.1:5178` with a separately migrated temporary fictional SQLite file and loopback backend port 8008. No hosted production navigation or data access occurred. Actual UI checks passed:

1. Created Amber Vale 020, current Finish chapter 2, later Finish chapters 3 and 4.
2. Library showed one current/two later; default creation was current.
3. Tonight recommended Chapter 2 at 80, suitability 60, while high-priority Chapter 3 was explicitly excluded without a score.
4. Made Chapter 3 current: two current goals displayed; it then ranked at 87.5 under the unchanged priority effect.
5. Moved Chapters 2/3 later: all-later guidance appeared and Tonight abstained with no start control.
6. Archived then restored Chapter 2: it became current. Started it, moved it later while active, and successfully finished with rating 4, progress text and explicit goal completion.
7. History retained original titles, situation, score 80/suitability 60 and explanation. Reopened completed Chapter 2 as current; other later goals stayed later. Outcome Insights showed the completed session's original rating/context.

Final fictional state: one game, three active goals (one current/two later), one completed session, zero active sessions. A local screenshot was captured and visually inspected outside the repository at `C:/Users/Aaron/AppData/Local/Temp/sidequest-readiness-020.png`; it is an ephemeral UI artifact, not historical report evidence stored in Git.

## 22. Migration verification

Each dialect's migration probe creates an actual migration-001-only schema using its unchanged historical script, seeds representative real API-generated records with version-1 snapshots, then upgrades to 002. Representative records include active/completed/archived goals, a completed session and an active session.

After upgrade: every old goal is current; complete row dictionaries match except the added field; IDs, lifecycle, completed_at and other timestamps match; sessions and saved JSON match exactly; migration-001 history/checksum is unchanged; both versions' checksums match current files; repeated upgrade is idempotent; API history/active reads succeed; current scores match the frozen scorer; duplicate active-row insertion still fails. NULL/invalid readiness fails database enforcement on both dialects. Existing FK/lifecycle/rollback/history-tampering tests continue passing.

The migration fixture's SQLite table reflection reports one known SQLAlchemy warning about unsupported reflection of the expression-based single-active index. The migration does not drop that index; the fixture directly verifies its enforcement by attempting a second active insertion. No warning was treated as an application failure or hidden data loss.

## 23. Backend test results

Baseline: **687 passed, 50 skipped**, 29.55s, before production edits. PostgreSQL was not enabled in that baseline. First focused readiness run: **53 passed**, 20.79s, both dialects (before two additional reopen cases).

Final full regression: **790 passed, 2 skipped, 1 warning**, 81.18s. All 687 baseline passing cases remain, the 48 formerly opt-in PostgreSQL cases ran successfully, and 55 new readiness cases passed (27 per dialect plus frozen-hash verification). The two skips are existing SQLite/dialect-only cases. The one reflection warning is documented in section 22. The final invocation explicitly enables only the temporary loopback PostgreSQL cluster and PostgreSQL 18 client tools, including the existing real backup/restore maintenance tests on fictional temporary databases. No production connection or personal SQLite import occurred.

Commands: backend `.venv/Scripts/python.exe -m pytest -q --tb=short` with child-process `SIDEQUEST_TEST_POSTGRES_URL` pointed at the disposable loopback cluster and `SIDEQUEST_TEST_PG_BIN` pointing at the installed PostgreSQL 18 binaries; frontend `npm test -- --run`, `npm run build`; `git diff --check`. Production environment values/URLs were not used. No tests were deleted or weakened.

Existing tests were retained. Updated hardcoded current migration counts/CLI output to 002, copied complete streams for checksum/rollback tests, used version 3 for deliberately broken/future migration fixtures, updated current snapshot expectations/corruption readers to v2, and kept Report 010's synthetic historical payload explicitly version 1 without new eligibility metadata. An initial broad test-value replacement briefly affected a foreign-key assertion; it was corrected back to 1 before final verification. Initial expected-contract/test-selector failures were corrected without relaxing constraints or scoring checks.

New `test_goal_readiness.py` covers defaults, strict API validation, moves, omitted/metadata edits, reopen persistence, multiple current/later, scorer spy, priority/time conflict, lifecycle/parent precedence, restore semantics, stale start, active finish with/without goal completion, unchanged history/outcomes, v1 readers, v2 marker validation, SQL constraints, populated migrations/checksums and frozen hash.

## 24. Frontend test results

Baseline: **68 passed**, three files, 13.67s. Final: **79 passed**, three files, 13.05s. Eleven new cases cover multiple-current/grouping, all-later versus inactive guidance, default/explicit later creation, both moves, metadata omission, failed writes, duplicate submissions, stale game-selection reads, and unscored later audit/abstention. Existing lifecycle, stale recommendation, History and Outcome Insights cases remain and pass; only new request field/restore labels changed their expected contract.

## 25. Production build result

Baseline and final builds passed. Final `npm run build`: Vite 8.3.2, 27 modules, 182ms. No dependency, lockfile, Vite configuration, deployment packaging or provider routing changes were needed. The generated ignored dist output is not a source change.

## 26. Frozen scorer hash

Before and after: `backend/app/scoring.py` SHA-256

```text
b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a
```

Exact match; scoring.py was not edited. Reports 001–019 and both migration-001 files match their pre-task SHA-256 values. Migration runner/checksum behavior is unchanged. `git diff --check` passed.

## 27. Files changed

Created:

- backend/migrations/002_goal_readiness.sql
- backend/migrations/postgresql/002_goal_readiness.sql
- backend/tests/test_goal_readiness.py
- reports/020_optional_goal_readiness.md

Updated:

- backend/app/models.py, schemas.py, routes.py
- backend/app/recommendations.py, recommendation_schemas.py
- backend/app/session_schemas.py, session_routes.py
- backend/tests/test_database_configuration.py, test_library_api.py, test_persistence_contract.py, test_production_packaging.py, test_sessions_api.py, test_snapshot_numeric_consistency.py
- frontend/src/views/Library.jsx, forms/LibraryForms.jsx, components/Recommendation.jsx, test/App.test.jsx
- PROJECT.md, README.md, reports/README.md

Preserved pre-existing uncommitted Report 019 and its experiment/tests/index entry. No historical report, prior migration, scorer, database configuration, security, outcome implementation, History renderer, maintenance implementation or deployment file changed. No commit or push was performed.

## 28. Known limitations

Readiness is manually maintained; forgotten promotion can cause abstention. Multiple current goals can tie. Vague goals remain vague. Sidequest does not infer real prerequisites or exclusive branches. Repeatable goals remain ordinary goals. Same-game activities share game-level fit metadata. All-current libraries retain frozen ranking behavior. Completion does not produce a next objective. Other-tab writes may require refresh; no general revision/concurrency editor was added.

## 29. Deferred work

No ordering, queue, promotion automation, dependency graph, numeric progress, recurrence, next-goal prompt, templates, game integration or outcome ranking. Historical readiness is not backfilled. No infrastructure or broader feature work began.

## 30. Deployment status

**Not deployed.** No push, Vercel action, protection change, production Neon connection, production migration, secret change or personal-data transfer occurred. Child-process environment configuration was used only for isolated local verification; provider/runtime environment settings were not altered. Temporary local servers/cluster were stopped after verification.

## 31. Recommended next action

Review the implementation, explicit eligibility marker and snapshot-version compatibility, then commit this milestone (and the preserved Report 019 work if desired). A later separately authorized deployment must apply migration 002 through the existing direct maintenance/migration workflow before serving code that requires it; startup does not migrate. Do not treat local verification as proof of a hosted upgrade. No follow-up feature or deployment was begun.

Suggested commit message: `Add optional current/later goal readiness`
