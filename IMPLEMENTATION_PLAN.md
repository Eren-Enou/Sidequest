# Implementation plan

Status: proposed; do not begin implementation until the user reviews this plan.

Each milestone should produce a small reviewable result. Update the README as runnable commands become available.

## 1. Deterministic recommendation engine

- Set up the Python dependency manifest and pytest.
- Define lightweight typed candidate/situation/result structures and input validation.
- Implement eligibility, five score factors, stable tie handling, and structured explanations in a pure module.
- Add focused tests for boundaries, empty sets, incompatibility, ties, recency, and repeatability using a fixed evaluation time.

Done when documented examples produce expected rankings and explanations without a database, web server, or external calls. This validates the product's central behavior before UI work.

## 2. Database and library API

- Add FastAPI, synchronous SQLAlchemy, SQLite foreign-key enforcement, and request/response schemas.
- Create Game, Goal, and PlaySession tables with constraints and an explicit initial migration. Choose a small migration mechanism here and document its use.
- Implement game/goal create, list, edit, archive, and goal-completion routes.
- Test validation, relationships, archive behavior, and data persistence using a temporary SQLite database.

Done when the library can be managed through API calls and data survives reopening the database.

## 3. Recommendation API

- Add a recommendation endpoint accepting the four situation inputs.
- Load candidates and completed-session recency, evaluate at one backend timestamp, and call the scoring engine.
- Return winner, ordered alternatives, factor calculations, version, and exclusions.
- Test integration between persisted candidate/history data and the ranking result.

Done when library records yield the documented explanation and empty sets return useful reasons.

## 4. Session lifecycle and history API

- Add start, active-session, finish, and history endpoints.
- Enforce a single active session with transaction/database protection, including concurrent start attempts.
- At start, validate/recalculate the chosen recommendation and save titles, situation, and scoring snapshots.
- At finish, require valid actual duration, enjoyment, and progress; optionally mark the goal completed in the same transaction.
- Test duplicate start/finish, invalid inputs, snapshot preservation after edits, and restart recovery.

Done when an entire session can be recorded and inspected through the API with stable historical explanations.

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

Begin with milestone 1 after review. Agree on goal eligibility and score weights first, then make those rules executable and testable. Keep database and UI work in subsequent milestones so scoring decisions remain easy to inspect.
