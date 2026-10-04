# Implementation plan

Status: Milestones 1-4 complete (reports 004-007). Milestones 5-6 remain unstarted and require further user direction.

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

## 5. React library and recommendation interface

- Initialize React/JavaScript with Vite, a development API proxy, and basic styles.
- Build game/goal management and the situation form.
- Display the winning game/goal, factor contributions, total, and empty-state guidance.
- Handle loading, validation, and API errors with clear messages.

Done when the user can maintain the library and get an explained recommendation in the browser. Verify a production build and the actual browser flow.

## 6. React sessions and V0.1 verification

- Add start/finish controls, active-session recovery on page load, and history views.
- Suggest elapsed duration while allowing user confirmation/correction.
- Show completed session details, including progress, notes, and saved recommendation breakdown.
- Run the full acceptance loop, backend checks, frontend build, and browser smoke test.
- Finalize setup, migration, and local-data backup documentation.

Done when every V0.1 acceptance criterion in PROJECT.md is satisfied.

## First implementation recommendation

Milestones 1-4 are complete. Review reports/007_milestone_4_session_lifecycle.md before authorizing Milestone 5, the React library and recommendation interface. Frontend work remains unimplemented. The scoring policy is frozen; integration problems must be reported instead of silently changing it.
