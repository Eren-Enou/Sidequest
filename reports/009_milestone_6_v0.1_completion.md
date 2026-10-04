# Milestone 6: browser completion and final V0.1 verification

Date: 2026-10-03 (America/Los_Angeles)  
Milestone: 6  
Outcome: **Interface implemented; final acceptance blocked. Do not declare V0.1 complete.**

## 1. Summary and scope

The browser now supports active-session inspection, editable duration suggestions, finishing, and snapshot-based history. The complete small-library loop passed in an actual browser, including reload recovery and subsequent completed-play recency. However, the requested larger-library test uncovered a pre-existing backend integration defect: exact numeric equality in recommendation snapshot validation rejects legitimate floating-point totals and produces HTTP 500 on session start. Even an unselected audit candidate can prevent starting a valid winner.

All 410 existing backend tests and 51 frontend tests pass, and the production build passes. These results do not override the observed browser failure. Backend behavior and frozen scoring were not modified to work around it. The issue requires a focused, separately reviewed integration fix and another numbered verification report.

This report supplements reports 004–008 without rewriting them. No V0.2 work, new runtime dependencies, schema changes, scoring changes, pagination, search, authentication, or external integrations were introduced.

## 2. Real-user feedback incorporated

The first Milestone 5 user test found adding games/goals simple, most fields understandable, and recommendations useful as decision support. Detailed explanations were sometimes skippable but not annoying. No major visual problems or immediate need to override recommendations were reported. The open questions were the meaning of friction, estimating goal duration, and larger-library behavior.

This is qualitative usability evidence, not a weight-calibration dataset. Changes address wording and the missing finish/history flow. The dark charcoal, restrained warm accent, typography, compact cards, and expandable explanations remain. Broader visual identity work remains deferred.

## 3. Terminology

Game forms now ask **“How hard is it to get started?”**, with helper text: “The effort between deciding to play and getting into the activity — not game difficulty.” Backend `friction` is preserved with all six values:

| Backend value | UI description |
| --- | --- |
| 0 | Jump right in |
| 1 | Very easy |
| 2 | Easy |
| 3 | Some effort |
| 4 | A hassle |
| 5 | Big commitment |

Library metadata says “Getting-started effort”; the explanation heading says “Getting started,” and factor inputs humanize the internal field. Original backend factor reasons are displayed verbatim, so the technical word may still occur inside a saved explanation. It is no longer the primary UI label.

Goal forms ask **“Useful session length”** with: “About how much time would make a session working on this goal feel worthwhile? A rough estimate is fine. In minutes, not total goal-completion time.” It still sends positive integer `estimated_minutes`; the Experiment 003 duration rule is unchanged. A multi-session goal can remain open after recording progress.

## 4. Active-session workflow

Successful start opens Active session. Its view uses saved game/goal titles, backend start timestamp, original situation, selected score/suitability, and the shared expandable “Why this?” renderer. Backend recovery runs on app load. Reload returns to Tonight with an active banner/navigation action; selecting Active session reconstructs the persisted record.

Elapsed seconds are calculated locally from the saved start timestamp, updated once per second, clamped to zero for a future local-clock reading, and cleaned up on unmount. There are no timer writes or automatic finish requests. The backend remains authoritative for lifecycle state. The clear **“Finish Sidequest”** action opens the finish form.

## 5. Finish workflow

The form suggests rounded elapsed minutes with a minimum of one because the API requires positive duration; users can edit it to account for breaks. An edited duration is not overwritten by subsequent timer ticks. Enjoyment uses simple descriptions on a 1–5 select, progress is required nonblank free text, notes are optional, and goal completion is explicitly opt-in.

The existing finish API receives all five fields. Progress is trimmed; empty optional notes become null. Native controls and explicit submit validation reject invalid duration/nonblank progress before a write; the backend validates again. A pending-request guard and disabled form prevent repeated submission. Optional goal completion relies on the existing atomic backend transaction.

Success clears active state, shows a concise confirmation, and opens the completed History detail. On an error, the UI reads the session: if it already finished (including a lost successful write response), the saved result is shown without another write. Otherwise the error remains and active state is refreshed. A recoverable conflict preserves the draft while that session remains active. Unsaved drafts are not persistent.

## 6. History workflow

History navigation loads completed sessions in backend order. Cards prioritize local date, snapshot game/goal titles, actual minutes, enjoyment, and progress. Internal IDs and engine version are not prominent in the list. Inspecting a record loads the individual endpoint and shows notes, start/finish timestamps, original context, score, suitability, factors, and policy version.

All historical identity/explanation data comes from saved session snapshots; History does not consult current games/goals or rerun recommendations. Empty, loading, and retry states are provided. A shared SessionEvidence component renders saved evidence in both Active session and History. No new routing/state-management framework was added.

## 7. Actual browser feedback loop

Environment: installed production Vite bundle, in-app browser, isolated API at `127.0.0.1:8016`, preview at `127.0.0.1:5176`. A new explicitly migrated SQLite file was created under:

`C:\Users\Aaron\AppData\Local\Temp\sidequest-m6-2cc0e119fc794aa18edf629e5c124751\smoke.sqlite3`

The personal database was not used. The test tab and its two temporary servers were closed after observation; the database/screenshots remain as local evidence. Normal browser operation did not require Swagger, direct API calls, or database manipulation.

Actions actually performed in the browser:

1. Added **Moonlit Orchard**: interest 4, getting-started effort 1, low energy, solo, progression.
2. Added **Harvest the autumn crops**: useful session 30 minutes, priority 2.
3. Requested 45 minutes, medium energy, either play preference, progression.
4. Inspected all seven backend explanation factors.
5. Started the accepted recommendation; reloaded; selected Active session; inspected saved context/score and finish controls.
6. Edited the suggested one-minute duration to 30, selected enjoyment 4, entered progress “Harvested the autumn crops and stocked the greenhouse.” and notes “Next time: plant winter seeds.” Goal completion remained unchecked.
7. Saved; active controls cleared, confirmation appeared, and History opened the saved detail.
8. Expanded saved factors; requested the same recommendation again; observed completed-session recency in the new explanation.
9. Renamed the game to “Moonlit Orchard — renamed” and goal to “Winter planting,” archived the game, reloaded, and inspected History. Original titles and original factors remained.

Start was at `2026-10-04T04:08:00Z` (browser displayed 2026-10-03 21:08); finish was at `2026-10-04T04:08:10.720206Z`. The 30-minute actual duration was deliberately user-confirmed synthetic play time, demonstrating that wall-clock elapsed time is not silently equated with actual play.

| Factor | Original saved points | Subsequent recommendation points |
| --- | ---: | ---: |
| Interest | 18.75 | 18.75 |
| Goal priority | 7.5 | 7.5 |
| Time fit | 10 | 10 |
| Energy fit | 30 | 30 |
| Experience fit | 20 | 20 |
| Getting started (`friction`) | -2 | -2 |
| Recent play | 0 | Approximately -3 |
| Total | 84.25 | Displayed 81.25 |
| Suitability | 60 | 60 |

The new evaluation at approximately `2026-10-04T04:08:16Z` showed the completed timestamp and a small positive elapsed-days value; raw recency was slightly above -3 as the penalty fades continuously. History still showed 84.25 and recency zero. Only formatting rounds values; JavaScript does not score or compute recency.

Screenshots saved locally: `history.png` (expanded factors), `history-summary.png` (normal list/detail), in the same temporary directory. A narrow History viewport was visually inspected at 390×844; measured document client/scroll widths were both 375 pixels, with no horizontal overflow. The temporary viewport override was reset. These are smoke observations, not a cross-browser certification.

## 8. Larger-library test

`frontend/scripts/seed_smoke_library.py` adds fictional data through existing library API routes, without database shortcuts or scoring code. It requires an explicit base URL and documents use only against an isolated database. Every run creates new records.

The seed adds 12 games with three goals each. Including the browser-created pair, the observed library had **13 games / 37 goals**, with three archived games after the browser archival, three completed goals, three archived goals, and other goals active (some under archived parents). Before the browser archive, the seed itself had two archived games. Inputs vary across all energy/social modes, interests 1–5, efforts 0–5, all four experience tags, priorities 1–3, and session chunks 5–120 minutes.

| Fictional game | Energy / mode | Interest / effort | Tags | Goal minutes |
| --- | --- | --- | --- | --- |
| Quiet Harbor | low / solo | 4 / 0 | chill, progression | 10, 25, 45 |
| Cloud Garden | low / both | 4 / 0 | chill, progression | 15, 30, 45 |
| Iron Summit | high / solo | 5 / 2 | challenge, progression | 20, 45, 90 |
| Rift Patrol | high / social | 5 / 5 | challenge | 30, 60, 120 |
| Lantern Roads | medium / solo | 3 / 1 | novelty, progression | 15, 35, 70 |
| Moss & Mirrors | low / solo | 2 / 0 | novelty, chill | 5, 20, 40 |
| Star Cartographers | medium / both | 4 / 3 | novelty, challenge | 20, 50, 100 |
| Cozy Caravan | low / social | 3 / 4 | chill | 10, 30, 60 |
| Ember Circuit | high / both | 4 / 1 | challenge | 10, 25, 60 |
| Clockwork Isles | medium / solo | 1 / 2 | progression | 15, 45, 90 |
| Ancient Tides (archived) | medium / both | 5 / 3 | progression, novelty | 20, 40, 80 |
| Winter Vault (archived) | high / social | 2 / 5 | challenge | 30, 60, 120 |

Browser observations:

- Library showed 10 active games, or 13 with Show archived checked. Selecting Iron Summit showed three goals with clear active/completed states; Star Cartographers showed archived/active goals and the appropriate actions. The shelf remained understandable but required scrolling. Only the selected game's goals are expanded.
- For **45 / low / solo / progression**, the API returned 15 eligible ranked candidates and 22 exclusions. Quiet Harbor's 25-minute chapter and Cloud Garden's 30-minute chapter were two equivalent choices, each score **93.75**, suitability **60**. Both radio choices were usable; Cloud Garden was selected. Explanations were collapsed by default. Expanding the audit showed lifecycle, time, and social reasons and two unsuitable energy/experience options.
- The expanded audit is long at 37 goals. Its default collapsed state keeps the main recommendation readable; opening every explanation would be verbose. No search/pagination infrastructure was added and no scoring was tuned from these synthetic observations.
- For **90 / high / either / challenge**, the API returned 22 eligible candidates and 15 exclusions, with Iron Summit's 45-minute chapter as the clear **96-point / 60-suitability** winner. Presentation remained usable, but clicking Start selected quest failed. This serious functional issue prevents final acceptance.
- No obvious layout problem or visible lag appeared while browsing/selecting/recommending. This is a limited qualitative observation, not a performance benchmark. The failure was surfaced as an unavailable/busy message with refresh guidance; it did not create a session.

## 9. Blocking counterexample and diagnosis

The actual browser start, followed by a direct HTTP reproduction, returned **500**. The backend traceback ended at `RecommendationSnapshot.consistent_evidence` in `backend/app/session_schemas.py`: **“Snapshot breakdown must sum to score.”** Active remained null and the one completed history record remained intact.

The validator checks every eligible audit entry using `item.score != sum(item.breakdown.values())`. The scorer's original factor contributions can contain both integers and floats; projection to `dict[str, float]` converts them to floats. On the tested Python 3.12 runtime, summing the converted contributions can differ by one floating-point rounding unit from the original total. This does not represent a different scoring policy or corrupted explanation. Exact equality rejects the numeric representation change.

A two-candidate reproduction is sufficient; no database, recency, archived records, or frontend code is needed:

| Candidate | Useful minutes | Energy / mode | Tags | Interest / priority / effort | Score |
| --- | ---: | --- | --- | --- | ---: |
| Iron Summit | 45 | high / solo | challenge | 5 / 3 / 2 | 96 |
| Cloud Garden | 30 | low / both | chill, progression | 4 / 3 / 0 | 70.41666666666666 |

Situation: 90 minutes, high energy, either, challenge. Both are active, never played. Evaluation time: `2026-10-04T04:10:00Z`.

Cloud Garden's complete projected breakdown:

```json
{
  "interest": 18.75,
  "goal_priority": 15.0,
  "time_fit": 6.666666666666667,
  "energy_fit": 30.0,
  "experience_fit": 0.0,
  "friction": 0.0,
  "recent_play": 0.0
}
```

Projected sum: `70.41666666666667`; original score: `70.41666666666666`; difference: `-1.4210854715202004e-14`. Iron Summit's own sum is exactly 96. The unrelated non-winning candidate blocks its snapshot. The larger fixture also exposed this issue for Lantern Roads and Cozy Caravan.

Reproduce from `backend/` with the existing virtual environment:

```python
from datetime import datetime, timezone
from app.scoring import Candidate, SessionContext, recommend
from app.recommendation_schemas import RecommendationRequest, response_from_result
from app.session_schemas import RecommendationSnapshot

context = RecommendationRequest(available_minutes=90, energy="high",
    social_preference="either", desired_experience="challenge")
candidates = [
    Candidate(game_id=1, goal_id=1, game_title="Iron Summit",
        goal_title="Advance chapter", estimated_minutes=45,
        energy_required="high", social_mode="solo",
        experience_tags=("challenge",), interest=5, goal_priority=3, friction=2),
    Candidate(game_id=2, goal_id=2, game_title="Cloud Garden",
        goal_title="Advance chapter", estimated_minutes=30,
        energy_required="low", social_mode="both",
        experience_tags=("chill", "progression"), interest=4,
        goal_priority=3, friction=0),
]
result = recommend(candidates, SessionContext(**context.model_dump()),
    evaluated_at=datetime(2026, 10, 4, 4, 10, tzinfo=timezone.utc))
response = response_from_result(result, context)
for item in response.ranked:
    print(item.candidate.game_title, repr(item.score),
          repr(sum(item.breakdown.values())))
RecommendationSnapshot(snapshot_version=1,
    selected=response.winner, evaluation=response)  # raises ValidationError
```

This diagnostic was actually executed and reproduced the exception. The existing automated suite did not catch this projection boundary. No backend fix or expected-failure test was added during this frozen-backend milestone. A suitable follow-up is a narrowly bounded numerical-consistency check with regression tests for start and persisted readback, plus rejection of materially inconsistent evidence. Do not round/change production scores, drop audit entries, relax suitability, or modify weights. The exact correction requires review before implementation.

## 10. Automated verification

| Check | Result |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m pytest -q` from backend | **410 passed**, 13.39 seconds |
| `npm test` from frontend | **51 passed**, 2 files, 11.56 seconds |
| `npm run build` from frontend | Passed, Vite 8.3.2, 26 modules |
| `git diff --check` | Passed; normal Windows line-ending notices only |

The 26 prior frontend tests remain, with wording/full active fixtures updated where the new interface supersedes Milestone 5 expectations. **25 new frontend cases** cover terminology and preserved six-value mapping, useful-session semantics, full saved active evidence, real unmount/remount recovery, elapsed suggestion/edit preservation, invalid minutes, nonblank progress, enjoyment/notes/completion payloads, active clearing, repeated submission, recoverable conflicts, already-finished/lost-response recovery, keep-playing, empty/list/detail/history retry, snapshot identity after live edits, saved explanations, history remount, next server-returned recency, and the combined UI loop.

Frontend fetch mocks test interaction/payload/display behavior; they do not prove SQLite transactions or recency arithmetic. The unchanged backend suite covers those contracts. Actual browser evidence above uses the live backend and separately exposes the uncovered boundary.

## 11. Preservation and files

SHA-256 of `backend/app/scoring.py` remains:

`b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a`

All 12 backend application Python files and all eight historical reports were individually compared against hashes captured before implementation: **20 matched, none changed**. No backend migrations, tests, requirements, or database schema were changed. Existing unrelated `.vs` workspace changes were left untouched.

Created:

- `frontend/src/views/ActiveSession.jsx`, `History.jsx`
- `frontend/src/forms/FinishForm.jsx`
- `frontend/src/components/SessionEvidence.jsx`
- `frontend/src/test/Sessions.test.jsx`
- `frontend/scripts/seed_smoke_library.py`
- This new immutable report.

Changed: frontend `App.jsx`, `api.js`, `components/Recommendation.jsx`, `components/UI.jsx`, `forms/LibraryForms.jsx`, `views/Library.jsx`, `styles.css`, and `test/App.test.jsx`; README, implementation plan, PROJECT status, and report index. No runtime dependency additions or backend abstractions were required.

## 12. Explicit V0.1 acceptance review

| # | PROJECT criterion | Outcome and evidence |
| --- | --- | --- |
| 1 | Manage games/goals; edits/archives persist after restart | Satisfied: existing persistence/API tests; browser create/edit/archive and reload confirmed, including preserved history. |
| 2 | Understandable invalid enum/title/time/rating validation | Satisfied: existing backend validation tests, preserved form/API error tests, and new finish duration/progress/input cases. |
| 3 | All four context inputs affect documented eligibility/scoring | Satisfied: unchanged scoring/API tests; distinct live low/solo/progression and high/either/challenge results. |
| 4 | Suitability, complete explanations, deterministic equivalents, distinct abstention outcomes | Satisfied: frozen engine/API tests and prior frontend outcome cases; actual equivalent-choice selection and audit inspection. |
| 5 | Boundary, eligibility, recency, tie/repeatability tests | Satisfied: all existing 410 backend tests still pass, including Milestone 1 policy tests. Numeric snapshot projection gap is separately documented. |
| 6 | Recommended pair starts, second active rejected, finish records fields/optional completion | **Not fully satisfied**: small-library browser start/finish passes; existing atomic/conflict backend and new UI tests pass, but legitimate larger-library start returns HTTP 500. This is the completion blocker. |
| 7 | History survives restart and preserves original evidence after edits/archives | Satisfied for recorded sessions: backend reopen/history tests, frontend remount tests, browser reload after live rename/archive, original titles/factors retained. |
| 8 | Full local add → goal → recommend → start → finish → history smoke | Satisfied: actual browser loop plus subsequent backend recency; no Swagger/manual API needed for that loop. Larger-library failure limits general readiness. |
| 9 | Recommendation has no LLM/external-service calls | Satisfied: unchanged standard-library scorer and local SQL/API projection; no frontend scoring/external integration added. |

**Eight criteria satisfied; criterion 6 blocks final acceptance.** A successful single-library smoke and passing tests are insufficient to declare completion when another realistic fixture fails.

## 13. Known limitations and deferred opportunities

- Snapshot numeric consistency can currently prevent starting otherwise valid recommendations. This must be addressed before declaring V0.1 complete.
- Suitability threshold 25 and near-tie margin 3 remain provisional heuristics; tags and estimates remain user-maintained. There is no empirical confidence estimate, learning, social-readiness knowledge, or automatic play detection.
- Linear library/history and expanded audit lists can grow long. This dataset was usable with collapsed details; larger scale and long-term history are unbenchmarked. No new filtering, search, pagination, or analytics was added.
- Elapsed display depends on the local clock; actual play time is editable. Unsaved drafts/navigation state reset on reload, while persisted session state survives. Other-tab changes may require reload; no polling or synchronization service was introduced.
- History is inspectable and immutable through the API; there is no edit/delete/export UI. The small local application retains the existing explicit migration/backup workflow: stop the API before copying the configured SQLite file, and restore only compatible migration history.
- Broad visual identity, artwork, integrations, charts, notifications, learned recommendations, and cloud/multi-user support remain post-V0.1 opportunities, not work started here.

## 14. Completion recommendation and review decision

**Do not declare Sidequest V0.1 complete yet.** The requested browser interface is implemented, the normal small-library loop works, and preservation/regression/build checks pass. The larger-library observation found a real integration blocker and a minimal reproducible case. Review a focused backend snapshot-validation correction that preserves `v0.1-final-004` verbatim, then record the regression fix and repeated acceptance evidence in report 010 (or the next available number). Keep this report unchanged.

Milestone 6 stops at this review boundary. No backend repair, scoring tuning, or post-V0.1 feature development was performed.
