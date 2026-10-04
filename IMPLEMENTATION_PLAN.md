# Implementation plan

Status: Milestones 1-5 complete (reports 004-008). Milestone 6 interface implemented and verified; final acceptance is blocked by a backend snapshot validation defect found during larger-library testing (report 009). V0.1 is not yet declared complete.

Each milestone should produce a small reviewable result. Update the README as runnable commands become available.

## 1. Deterministic recommendation engine - complete

- Set up the Python dependency manifest and pytest.
- Define lightweight typed candidate/situation/result structures and input validation.
- Implement eligibility, seven score factors, suitability-only abstention, and near-equivalent recommendations, stable tie handling, and structured explanations in a pure module.
- Add focused tests for boundaries, empty sets, incompatibility, ties, recency, and repeatability using a fixed evaluation time.

Done when documented examples produce expected rankings and explanations without a database, web server, or external calls. This validates the product's central behavior before UI work.

## 2. Database and library API - complete

- Add FastAPI, synchronous SQLAlchemy, SQLite foreign-key enforcement, and request/response schemas.
- Create Game, Goal, and PlaySession tables with constraints and an explicit initial migration. Implemented an explicit versioned SQL runner with transactional upgrades and normalized-content checksums; see README.md.
- Implement game/goal create, list, edit, archive, and goal-completion routes.
- Test validation, relationships, archive behavior, and data persistence using a temporary SQLite database.

Completed: games/goals can be managed through API calls, data survives reopening a file database, and all 315 tests pass. Report 005 records the schema, routes, and remaining limitations.

## 3. Recommendation API - complete

- Add a recommendation endpoint accepting the four situation inputs.
- Load candidates and completed-session recency, evaluate at one backend timestamp, and call the scoring engine.
- Return winner, ordered alternatives, factor calculations, version, and exclusions.
- Test integration between persisted candidate/history data and the ranking result.

Completed: POST /api/recommendations maps persisted library/history into the frozen scorer once at one backend timestamp, preserving all four outcomes, choice ordering, factor explanations, exclusions, and unsuitable audit entries. All 345 tests pass (315 previous + 30 new). Requests are read-only and scoring.py matches the frozen SHA-256. Report 006 records the contract and evidence.

## 4. Session lifecycle and history API - complete

- Add start, active-session, finish, and history endpoints.
- Enforce a single active session with transaction/database protection, including concurrent start attempts.
- At start, validate/recalculate the chosen recommendation and save titles, situation, and scoring snapshots.
- At finish, require valid actual duration, enjoyment, and progress; optionally mark the goal completed in the same transaction.
- Test duplicate start/finish, invalid inputs, snapshot preservation after edits, and restart recovery.

Completed: start-time revalidation accepts any frozen recommendation choice, validated version-1 snapshots preserve explanations, active recovery/history survive restart, and finish optionally completes the goal atomically. SQLite writer transactions and the existing unique index protect concurrent starts; duplicate/concurrent finishes preserve history. All 410 tests pass (345 previous + 65 new), including the complete recommendation/start/finish/recency loop. Report 007 records decisions and limitations.

## 5. React library and recommendation interface - complete

- Initialize React/JavaScript with Vite, a development API proxy, and basic styles.
- Build game/goal management and the situation form.
- Display the winning game/goal, factor contributions, total, and empty-state guidance.
- Handle loading, validation, and API errors with clear messages.
- Start any accepted recommendation choice through the existing session API and recover the active session on reload, as explicitly added to Milestone 5 by the user's request.

Completed: React/JavaScript/Vite interface provides Tonight and Library, all game/goal management actions, four recommendation outcomes, complete expandable explanations, alternative selection, session start and active recovery. All 26 frontend tests and 410 backend tests pass; production build and actual browser smoke flow passed. Report 008 records architecture, evidence, and limitations. No finish/history UI was implemented.

## 6. React sessions and V0.1 verification — acceptance blocked

- Add start/finish controls, active-session recovery on page load, and history views.
- Suggest elapsed duration while allowing user confirmation/correction.
- Show completed session details, including progress, notes, and saved recommendation breakdown.
- Run the full acceptance loop, backend checks, frontend build, and browser smoke test.
- Finalize setup, migration, and local-data backup documentation.

Done when every V0.1 acceptance criterion in PROJECT.md is satisfied.

Implemented: full active-session view, editable elapsed-duration suggestion, finish validation/feedback/recovery, and snapshot-based History. Usability wording clarifies getting-started effort (0–5) and useful session length without changing scoring. All 51 frontend tests and 410 backend tests pass; production build and the small-library browser feedback loop pass. The 13-game / 37-goal smoke test exposes HTTP 500 on a valid session start: snapshot validation compares a projected float factor sum to the original scorer total with exact equality. An unselected audit candidate can block the winner. Report 009 contains a two-candidate reproduction. Backend code, scorer, and reports 001-008 remain unchanged. Completion is withheld pending a separately reviewed integration fix and verification recorded in report 010 or the next available number.

## First implementation recommendation

Review report 009's numeric snapshot-validation counterexample before continuing. The next required work is a small backend integration correction and regression coverage that preserves scorer output, ranking, and all saved evidence; then repeat affected browser and acceptance checks in a new immutable report. No post-V0.1 features should begin. The scoring policy and backend behavior were preserved during this milestone; the integration problem is reported for review rather than silently changed.
