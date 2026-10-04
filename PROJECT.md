# Sidequest

## Product purpose

Sidequest is a personal gaming session recommendation web application that answers:

> What should I play right now, and what should I accomplish during this session?

It connects a user's games and goals to their available time, energy, social preference, and desired experience. Recommendations must be deterministic, inspectable, and explainable. Session history provides a record for future analysis.

## V0.1 scope

- Add, view, edit, and archive games.
- Add, view, edit, complete, and archive goals associated with games.
- Collect available minutes, energy (low/medium/high), solo/social preference, and one desired experience (progression/chill/challenge/novelty).
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

`available_minutes` is a positive integer; `energy` is low/medium/high; `social_preference` is solo/social; `desired_experience` is one of the four experience values. Persistent preference profiles are deferred. Store these inputs with a started session.

## Recommendation-engine concept

The ranking unit is an active goal paired with its active game. A game without an active goal cannot be recommended in V0.1; the UI should explain that adding a goal makes it eligible.

### Eligibility

Exclude archived games, non-active goals, social-mode mismatches (both accepts either preference), and goals whose estimated minutes exceed available minutes. Energy is a soft score, allowing users to choose a demanding game when they have low energy. If nothing qualifies, show why candidates were excluded and suggest adjusting inputs or goal estimates. Do not silently relax filters.

### Proposed scoring rules (engine version `v0.1`)

Each eligible pair receives 0–100 points:

| Factor | Maximum | Calculation |
| --- | --- | --- |
| Time fit | 30 | `30 × estimated_minutes / available_minutes` |
| Energy fit | 25 | Map low/medium/high to 1/2/3. Award 25 if required energy ≤ available energy, 12.5 if one level above, 0 if two levels above. |
| Experience fit | 25 | 25 if the requested experience is among the game's tags, otherwise 0 |
| Goal priority | 10 | Priority 1/2/3 awards 0/5/10 |
| Variety | 10 | 10 if never played; otherwise `10 × min(days_since_last_completed_session / 7, 1)` for this game |

Time fit intentionally favors a goal that uses more of the available window. Estimates describe a useful chunk of play, so this policy can be revised after real use. Novelty is a manually assigned experience tag; variety is a separate recency factor.

Compute elapsed days as nonnegative UTC elapsed seconds divided by 86,400, using one supplied evaluation timestamp. Only completed sessions contribute to recency. Rank by unrounded total descending, then priority descending, then goal ID ascending. Round displayed values to two decimals; retain calculation precision internally. Equal inputs, candidate data, history, evaluation time, and engine version must yield equal results.

Return each factor's name, maximum, input values, awarded points, and plain-language reason alongside total and engine version. Also return exclusion reasons and the ranked alternatives for inspection, even if the UI initially highlights only the winner. No hidden randomness or LLM calls.

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

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the proposed sequence. Implementation is pending review.
