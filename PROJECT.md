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

### Production V0.1 policy (engine version `v0.1-final-004`)

Milestone 1 is complete. The accepted policy follows Eligibility -> Situational Suitability -> Preference Ranking -> Recommendation. The pure module `backend/app/scoring.py` has no API, persistence, or frontend dependencies. Its final decision is documented in reports/004_milestone_1_final_policy.md.

| Factor | Maximum | Calculation | Role |
| --- | --- | --- | --- |
| Interest | 25 | `25 * (interest - 1) / 4`, interest 1-5 | Preference ranking only |
| Goal priority | 15 | `15 * (priority - 1) / 2`, priority 1-3 | Preference ranking only |
| Time fit | 10 | Ratio r = estimate / available: `20r` below 0.5; 10 from 0.5 to 0.9; `10 - 20(r - 0.9)` above 0.9 | Suitability and ranking |
| Energy fit | 30 | Sufficient energy: 30; one level above: 15; two above: 0 | Suitability and ranking |
| Experience fit | 20 | Match requested tag: 20; otherwise 0 | Suitability and ranking |
| Friction | -10 maximum | `-10 * friction / 5`, friction 0-5 | Ranking cost only |
| Recent play | -3 maximum | `-3 * max(0, 1 - elapsed_days / 7)`; never played: 0 | Ranking cost only |

Social compatibility is eligibility only; there are no constant social points. Hard filters remain lifecycle, time, and social mode. Energy is soft and can be offset by the other situational factors; a demanding favorite is still possible when its experience/time fit passes the suitability gate.

**Suitability = time fit + energy fit + experience fit.** These represent the current time window, capacity, and desired experience. Only suitability below 25 causes soft abstention. The 25-point threshold is a provisional heuristic, not an empirically calibrated confidence measure. Interest, priority, friction, and recency do not change suitability or acceptance. There is no minimum-total gate. A low-interest or below-50-total candidate may therefore be recommended when it fits the situation.

Rank suitable candidates by the sum of all seven factors descending, then priority descending, goal ID ascending, and game ID ascending. Return suitable candidates within 3 points inclusive of the best suitable score as near-equivalent choices, in that deterministic order. This margin is a provisional presentation convention, not confidence. The first display choice is available via winner; it is not a uniquely better option when there are multiple equivalents.

Outcomes are `no_eligible` (hard filters leave nothing), `no_good_fit` (eligible options exist, but all have suitability below 25), `clear_recommendation` (one option within the near-tie band), and `multiple_equivalent` (more than one). An eligible audit list retains every score, including unsuitable candidates, with suitability and reasons. Recommendations contain only suitable choices; do not select directly from the audit list.

Results expose raw score, a breakdown summing to score, factor weights/inputs/reasons, suitability, acceptance reasons, ordered choices, exclusions, policy version, evaluation time, weights, threshold, and near-tie margin. Keep calculations unrounded. Display rounding must not determine acceptance or ranking. Default positive maxima total 100; eligible audit totals may be negative. Accepted candidates have suitability at least 25 and at most 13 penalty points, so their default total is at least 12. Scores are points, not percentages.

Use an explicit timezone-aware evaluation timestamp, normalized to UTC. Only last completed play per game contributes to recency. Elapsed days = nonnegative elapsed seconds / 86,400; future last-play timestamps are treated as just played. Equal inputs produce equal results regardless of input order; duplicate goal IDs are invalid. No implicit clock, randomness, external service, or LLM is used.

Known limitations: binary game-level tags, heuristic boundaries, unknown continuation/social readiness, subjective estimates, and no actual setup-time allowance. The time rule is continuous but the suitability gate remains categorical. Frozen baseline and experimental modules are retained under backend/experiments/ for historical comparison; production does not import them.

At session start, the backend revalidates the selected pair and recalculates its score from the supplied situation and current data. Store the resulting snapshot rather than trusting a client-supplied score. If the prior recommendation is no longer eligible, return a clear conflict and request a fresh recommendation.

## V0.1 acceptance criteria

1. A user can manage games and goals; edits and archives persist after restart.
2. Invalid enum values, missing titles, nonpositive time estimates, and invalid ratings receive understandable validation errors.
3. All four situation inputs affect eligibility or scoring as documented.
4. Recommendations expose suitability and complete score explanations, deterministic near-equivalent choices, and distinct no_eligible/no_good_fit outcomes with reasons.
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

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the proposed sequence. Milestone 1 is complete with the adopted production policy; subsequent milestones await review.
