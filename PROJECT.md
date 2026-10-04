# Sidequest

## Product purpose

Sidequest is a personal gaming session recommendation web application that answers:

> What should I play right now, and what should I accomplish during this session?

It connects a user's games and goals to their available time, energy, social preference, and desired experience. Recommendations must be deterministic, inspectable, and explainable. Session history provides a record for future analysis.

## V0.1 scope

- Add, view, edit, and archive games.
- Add, view, edit, complete, and archive goals associated with games.
- Collect available minutes, energy (low/medium/high), solo/social/either preference, and one desired experience (progression/chill/challenge/novelty).
- Rank eligible game/goal pairs using explicit scoring rules.
- Show the highest-ranked recommendation, its total score, and each factor's calculation. Handle an empty eligible set clearly.
- Start a session from a recommendation and finish it with actual duration, enjoyment, progress, and notes.
- Preserve completed session history across application restarts.

## Explicit non-goals

- LLM recommendations, chat assistants, machine learning, or adaptive weighting.
- Accounts, authentication, multiple users, or cloud synchronization.
- Storefront integrations, library imports, automatic play tracking, or friend matchmaking.
- Analytics dashboards, achievements, notifications, scheduling, or mobile applications.
- Docker, microservices, queues, deployment infrastructure, or premature performance work.
- Rich goal hierarchies, task dependencies, and elaborate progress metrics.

## Proposed architecture

- **Frontend:** React with JavaScript, built with Vite. A small set of screens for the library/goals, recommendation form/result, active session, and history. Standard React state and fetch are sufficient initially.
- **Backend:** Python/FastAPI with request/response validation, SQLAlchemy, and a local SQLite database. Use synchronous database access for simplicity.
- **API:** JSON over HTTP under `/api`. The backend owns validation, timestamps, eligibility, scoring, and session transitions.
- **Recommendation engine:** a pure Python module receiving candidate data, situation input, and an explicit evaluation time. It returns ranked results and structured factor explanations without database or HTTP dependencies.
- **Persistence:** one SQLite file in `backend/data/`, excluded from Git. Enable foreign-key enforcement. Introduce a simple explicit schema migration workflow with the persistence milestone; do not rely on table creation to alter existing schemas.
- **Development:** two local processes (Vite and FastAPI). Use a Vite `/api` proxy to avoid unnecessary development CORS configuration. No production hosting decision is required yet.

Keep SQLAlchemy models, API schemas, routes, and scoring in a few modules. Introduce additional layers only when actual complexity warrants them. No generic repository or service framework is planned.

## Initial data model

All records have integer IDs. Store timestamps in UTC; display them in the browser's local timezone. Enum values are validated by the backend. Use database constraints for required values, ranges, and relationships where practical.

### Game

| Field | Meaning |
| --- | --- |
| id, title | Identity and required display name |
| notes | Optional free text |
| current_interest | Integer 1-5; default 3; user-maintained interest |
| friction | Integer 0-5; default 0; setup/coordination effort |
| energy_required | low, medium, or high |
| social_mode | solo, social, or both |
| experience_tags | One or more of progression, chill, challenge, novelty; small validated JSON list |
| archived_at | Null while active |
| created_at, updated_at | Audit timestamps |

### Goal

| Field | Meaning |
| --- | --- |
| id, game_id, title | Identity, required game foreign key, required display name |
| notes | Optional free text |
| estimated_minutes | Positive estimate for a useful session on this goal, not total completion time |
| priority | Integer 1–3; default 2 |
| status | active, completed, or archived |
| created_at, updated_at, completed_at | Lifecycle timestamps |

Energy, social mode, and experience tags belong to the game in V0.1; per-goal overrides are deferred. Goals can span multiple sessions. Marking a goal complete is explicit, never inferred from notes.

### PlaySession

| Field | Meaning |
| --- | --- |
| id, game_id, goal_id | Identity and required foreign keys |
| game_title_snapshot, goal_title_snapshot | Preserve what was played if titles later change |
| started_at, finished_at | Backend timestamps; null finish indicates the active session |
| actual_duration_minutes | Positive user-confirmed duration on finish; default suggested from elapsed time |
| enjoyment_rating | Required integer 1–5 on finish |
| progress | Required text describing accomplishments on finish |
| notes | Optional session notes |
| situation_snapshot | Validated JSON copy of recommendation inputs |
| recommendation_snapshot | Engine version, evaluation time, factor inputs/contributions, and total |

One active session at a time. Starting and finishing must enforce this rule and reject repeated finish requests. Archived games and completed/archived goals remain referenced by history; V0.1 uses archive instead of hard deletion.

### Situation (request object, not a separate table)

`available_minutes` is a positive integer; `energy` is low/medium/high; `social_preference` is solo/social/either; `desired_experience` is one of the four experience values. Persistent preference profiles are deferred. Store these inputs with a started session.

## Recommendation-engine concept

The ranking unit is an active goal paired with its active game. A game without an active goal cannot be recommended in V0.1; the UI should explain that adding a goal makes it eligible.

### Eligibility

Exclude archived games, non-active goals, social-mode mismatches (both accepts either explicit preference; the either preference accepts every mode), and goals whose estimated minutes exceed available minutes. Energy is a soft score, allowing users to choose a demanding game when they have low energy. If nothing qualifies, show why candidates were excluded and suggest adjusting inputs or goal estimates. Do not silently relax filters.

### Implemented scoring rules (engine version `v0.1`)

The pure Python engine is implemented in `backend/app/scoring.py`. It consumes validated frozen domain objects representing flattened game/goal pairs, a session context, and a required timezone-aware evaluation timestamp. It has no runtime dependencies beyond Python's standard library.

| Factor | Weight | Calculation |
| --- | --- | --- |
| Interest | 25 | `25 * (interest - 1) / 4`, interest 1-5 |
| Goal priority | 15 | `15 * (priority - 1) / 2`, priority 1-3 |
| Time fit | 15 | `15 * estimated_minutes / available_minutes` |
| Energy fit | 15 | Full points if energy is sufficient; half if requirement is one level above; zero if two above |
| Social fit | 10 | Full points for every eligible candidate |
| Experience fit | 20 | Full points for a matching game experience tag, otherwise zero |
| Friction | -10 maximum penalty | `-10 * friction / 5`, friction 0-5 |
| Recent play | -10 maximum penalty | `-10 * max(0, 1 - days_since_last_completed_session / 7)`; never played receives no penalty |

Positive weights total 100; penalties can reduce scores below zero (the theoretical default range is -20 to 100). Scores are points, not percentages, and are not clamped. Weights are centralized in an immutable `ScoringWeights` object and may be supplied explicitly for experiments; results retain the weights used. Persist those weights with future recommendation snapshots.

Time fit favors using more of the available window. Estimates describe a useful chunk of play. Interest and friction are user-maintained game attributes; priority and estimated time belong to goals. The domain candidate calls the interest field `interest`; persistence can map `current_interest` to it.

Social preference `either` accepts solo, social, and both. Explicit solo/social preferences reject the opposite exclusive mode. All eligible modes earn full social points, so this factor currently contributes a constant rather than distinguishing ranks.

Only completed-session history contributes to recent play. The caller supplies the last completed session timestamp per game. Use timezone-aware timestamps and normalize evaluation time to UTC. Compute elapsed days from elapsed seconds / 86,400, clamping future last-play timestamps to zero elapsed days. Never played and seven-or-more days ago have no penalty. Novelty remains a manually assigned experience tag.

Rank by unrounded total descending, then priority descending, then goal ID ascending (game ID is a final stable key). Goal IDs must be unique in the input. Excluded candidates are ordered by ID and retain all applicable exclusion reasons. Empty input or an entirely ineligible set returns no winner without relaxing filters.

Each scored result exposes a numeric `breakdown`, whose values sum directly to `score`, plus factor weights, input values, and plain-language reasons. Keep calculations unrounded; the eventual UI may round for presentation. Results retain engine version, weights, and evaluation time. Equal inputs produce equal results regardless of candidate input order. There is no implicit clock, randomness, or LLM call.

At session start, the backend revalidates the selected pair and recalculates its score from the supplied situation and current data. Store the resulting snapshot rather than trusting a client-supplied score. If the prior recommendation is no longer eligible, return a clear conflict and request a fresh recommendation.

## V0.1 acceptance criteria

1. A user can manage games and goals; edits and archives persist after restart.
2. Invalid enum values, missing titles, nonpositive time estimates, and invalid ratings receive understandable validation errors.
3. All four situation inputs affect eligibility or scoring as documented.
4. An eligible set yields a stable highest-ranked pair and visible, auditable factor breakdown; empty sets show actionable exclusion reasons.
5. Focused tests cover factor boundaries, eligibility, recency, ties, and identical-input repeatability.
6. A recommended pair can start a session; a second active session is rejected. Finish records duration, enjoyment, progress, and notes, with an optional explicit goal-completion action.
7. Session history survives restart and retains recommendation inputs/explanations even after game or goal edits and archives.
8. A full local smoke test completes the add-game → add-goal → recommend → start → finish → history loop.
9. Recommendation generation makes no LLM or external-service calls.

## Assumptions requiring review

- This is a single-user local application.
- Every recommendation targets a goal, and each session is associated with one game and one goal.
- Time and social compatibility are hard filters; energy is a soft preference.
- Goal estimates represent a useful session chunk, not the total time remaining.
- Text progress and a five-point enjoyment rating are sufficient initially.
- Only one session can be active, including across browser refreshes.
- The initial weights and recency window are product hypotheses; changes require an engine-version update.

## Experiment and report preservation

Store investigations in `reports/` as numbered Markdown files, starting with
`001_milestone_1_engine_evaluation.md`. Allocate each new investigation the next
number greater than every existing report number: `002_<short_descriptive_name>.md`,
`003_<short_descriptive_name>.md`, and so on. Never reuse numbers or overwrite a
previous experiment report, including an uncommitted report from an earlier run.

Reports are immutable historical records. Once committed, never rewrite a report
to represent a later experiment. Repeat investigations after changes in a new
numbered report that references the earlier report. Preserve original inputs,
engine configuration, test outcomes, and observed results. Corrections or later
interpretations belong in a new report rather than replacing historical evidence.

Maintain `reports/README.md` as the mutable index. For every new report, record its
number, title, date, milestone, one-sentence purpose, and outcome/status. Never use
a repeatedly overwritten generic `report.md` for experiment results. Use the
user's local date for the report date and explicit timestamps for engine inputs.

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the proposed sequence. Milestone 1 is implemented; subsequent milestones await review.
