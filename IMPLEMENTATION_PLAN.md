# Implementation plan

Status: Milestones 1-6 complete. Sidequest V0.1 is complete after the focused snapshot-validation acceptance repair and final re-verification in report 010. The scorer remains frozen at v0.1-final-004.

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

## 6. React sessions and V0.1 verification — complete

- Add start/finish controls, active-session recovery on page load, and history views.
- Suggest elapsed duration while allowing user confirmation/correction.
- Show completed session details, including progress, notes, and saved recommendation breakdown.
- Run the full acceptance loop, backend checks, frontend build, and browser smoke test.
- Finalize setup, migration, and local-data backup documentation.

Done when every V0.1 acceptance criterion in PROJECT.md is satisfied.

Completed: full active-session view, editable elapsed-duration suggestion, finish validation/feedback/recovery, and snapshot-based History. Usability wording clarifies getting-started effort (0–5) and useful session length without changing scoring. Report 009 preserves the initial larger-library blocker. The focused authorized repair changes only snapshot score/sum numerical equivalence, with relative/absolute tolerance 1e-12 and finite-score protection. All 436 backend tests (410 existing + 26 new), 51 frontend tests, and production build pass. The previously failing browser scenario and larger-library alternative/challenge start/finish flows pass with original stored evidence intact. All nine PROJECT acceptance criteria are satisfied; reports 001-009 and the frozen scorer are unchanged. Report 010 records final acceptance.

## V0.1 completion decision

V0.1 is complete. No further milestone, deployment, or V0.2 work has begun. Preserve the accepted scorer and immutable historical reports. Any later investigation or feature requires a separate user request and a new numbered report where applicable.
