# 008: Milestone 5 React library and recommendation interface

Date: 2026-10-03 (America/Los_Angeles). Status: complete; Milestone 5 acceptance satisfied. Milestone 6 has not begun.

Reviewed PROJECT.md, IMPLEMENTATION_PLAN.md, README.md and reports [004](004_milestone_1_final_policy.md), [005](005_milestone_2_database_library_api.md), [006](006_milestone_3_recommendation_api.md), [007](007_milestone_4_session_lifecycle.md). Reports 001-007 and every backend/app Python module match the SHA-256 values captured before this task. No backend incompatibility or product/scoring change was needed.

## Frontend architecture and files

Created the React + JavaScript + Vite application in frontend/:

```text
index.html
package.json, package-lock.json
vite.config.js
src/
  main.jsx, App.jsx, api.js, styles.css
  components/UI.jsx, Recommendation.jsx
  forms/LibraryForms.jsx
  views/Library.jsx, Tonight.jsx
  test/setup.js, App.test.jsx
```

App owns navigation and backend-authoritative active-session recovery. Each view owns its forms/data/request state. The API module wraps relative `/api` fetch requests and converts response errors into readable messages. No JavaScript scoring, ranking, acceptance threshold, global state framework, router library, UI framework, or generic data-access framework was introduced.

The only runtime dependencies are React and React DOM. Vite, its React plugin, Vitest, Testing Library, jest-dom, and jsdom are development dependencies. Direct versions are pinned and the npm lockfile is checked in. A formatter was run as a temporary tooling command without adding a runtime dependency.

Vite listens on loopback, defaults to strict port 5173, and proxies `/api` to localhost:8000. SIDEQUEST_API_TARGET may override the backend target at server startup; browser URLs remain relative. Local preview inherits this proxy. No backend CORS or deployment changes were needed. Production hosting remains deferred.

## Visual/product decisions

A dark charcoal interface, warm amber accent, strong system typography, compact cards and journal panels, restrained borders, and clear primary actions. Tonight pairs a compact situation form with a decision panel. Library pairs a selectable game shelf with a quest journal. No gradients, charts, animation effects, fantasy ornament, image-generation assets, emoji-heavy styling, or remote font dependency.

CSS adapts the columns into stacked panels on narrow screens. Native selects, number inputs, checkboxes, radios and details/summary controls provide familiar keyboard behavior. Inputs use explicit labels; helper text is connected with aria-describedby rather than folded into the label. Navigation exposes aria-current, game selection aria-pressed, messages use alert/status roles, and focus outlines remain visible. Factor signs and text convey positive/negative points independently of color.

## Library workflows

- Game creation/edit exposes title, 1-5 interest, 0-5 setup friction, energy requirement, solo/social/both mode, one or more experience tags, and notes.
- A shelf checkbox shows archived games. Archive preserves records; restore reverses it. A selected archived game remains understandable in its detail panel even when hidden from the normal shelf.
- Selecting a game loads its goals including archived/completed records. Goal creation/edit exposes title, useful-session minute estimate, 1-3 priority, and notes. Status is shown and changed only through explicit complete, archive, restore or reopen actions.
- Archived parent restrictions follow the existing API: add/reopen/complete controls are disabled until the parent is restored. Metadata editing and goal archive remain available.
- Empty shelves and goal sets explain how to become recommendable. Editor cancellation and field validation are explicit. Goal editing never sends a game reassignment; forms omit server-owned fields.
- Pending writes disable mutation controls and a ref guards duplicate submissions. Failed writes keep editors open. If a write succeeds but refresh fails, the editor closes and the message distinguishes the saved change from the refresh failure, discouraging duplicate creation. Retry library reloads goals as well as games.

## Tonight, recommendations, and explanations

The question is "What should I play right now?" The four controls build the existing RecommendationRequest exactly. Changing situation inputs removes the old result/start choice, preventing a result from being used with different inputs. Switching back from Library mounts a fresh Tonight view rather than retaining an old recommendation.

The renderer consumes the backend's status and recommendation choices directly:

| Outcome | Presentation |
| --- | --- |
| clear_recommendation | One game/goal decision with score, suitability, session metadata and start control |
| multiple_equivalent | "A few equally good choices" with radio selection for every accepted option; no unique-best claim |
| no_good_fit | Available activities do not fit well enough; adjustment guidance; no start control |
| no_eligible | Nothing currently qualifies; guidance to adjust time/social preference or add an active goal; no start control |

Scores are points, not confidence percentages. Display formatting rounds to at most two decimal places without changing request data or applying decisions. "Why this?" expands all seven server factors with signed points, weights available in the response, input values and server explanations. The visible factor list shows contributions and inputs/reasons; it does not recalculate them. Exclusions and unsuitable audit entries are in a separate collapsed details section, preventing a large default audit dump.

## Start behavior and active recovery

Start sends only selected game_id/goal_id and the result's evaluated context to POST /api/sessions/start. The backend recalculates current acceptance. Any accepted equivalent option can be selected; JavaScript neither chooses from ranked audit results nor promotes an unsuitable candidate.

Successful start updates the active banner using the actual SessionRead returned by the backend and disables further starts. A ref plus disabled controls prevents accidental duplicate submission. On initial load/reload, GET /api/sessions/active recovers the saved session. Starting remains disabled until active state is known; a failed active check has a retry action. Request sequence tracking prevents a delayed older recovery response from overwriting newer state.

409 start errors show backend guidance and a refresh-recommendation action. Further starts are blocked until refreshed. The frontend also rechecks active state after a failed start, recovering sessions started in another tab and handling uncertain network outcomes without assuming the write failed.

No finish controls or History navigation were added. The README explains use of the existing API/docs to finish a session during this intermediate milestone. The user's explicit Milestone 5 start requirement extends the original plan; start/recovery was implemented now without beginning Milestone 6.

## Error, loading, and empty states

Library, goals, recommendation requests and starts show loading/saving state. Network failure gives backend-start/retry guidance. Backend validation arrays become field/message text. Server errors show an unavailable/busy message without raw tracebacks or error objects. Conflicts use readable backend state messages. Empty libraries, goal sets, no eligible candidates, and no good fit have useful next steps. A tag-less game cannot be saved; native required/min/step controls provide immediate form constraints while server validation remains authoritative.

## Automated tests

Frontend command: `npm test` from frontend/.

**26 tests passed**, one test file, final duration **9.39s**. Vitest/Testing Library drives real components and native controls against a deterministic fetch fixture. These are frontend interaction/contract tests, not a replacement for database tests or a live browser.

Coverage includes all 16 required behaviors: four-field request construction; clear, equivalent, no-good-fit and no-eligible rendering; signed factor explanations; accepted alternative selection; session-start body; stale/conflict handling; active recovery; game create/edit/archive/restore; goal create/edit/complete/reopen/archive/restore; and validation/error presentation. Additional cases cover duplicate starts, another-tab active conflict, situation-change invalidation, unknown active state blocking, empty shelves, tag requirements, network/server error sanitization, out-of-order recovery, goal-load retry, and saved-change/refresh-failure distinction.

The initial run caught helper text changing accessible label names; explicit labels and descriptions fixed it. Two test selectors were also corrected to distinguish the active banner from the equivalent-choice label and to give shelf buttons clear accessible names. Subsequent final tests passed without warnings.

Backend command: `.venv/Scripts/python.exe -m pytest -q` from backend/.

**410 tests passed in 12.68s**, no failures or warnings. All existing backend tests/files and backend product implementations are unchanged during this milestone.

Frozen scorer SHA-256:

`b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a`

All prior reports 001-007 also match their captured hashes. PROJECT.md was reviewed and left unchanged.

## Production build and dependency checks

`npm run build` succeeded with Vite 8.3.2, 22 transformed modules, final build time 138ms. Output: dist/index.html 0.47kB; CSS 8.20kB (2.59kB gzip); JavaScript 241.97kB (75.14kB gzip). Generated dist and node_modules stay ignored.

Tested Node 24.13.0/npm 11.6.2. React/React DOM 19.3.0, React plugin 6.1.1, Vitest 5.0.3, Testing Library React 16.3.3/user-event 14.6.7, jest-dom 6.9.1, jsdom 29.1.1. The latest jsdom required a newer Node patch; the final pinned version supports the installed runtime. Final npm dependency audit reported zero vulnerabilities and no engine warnings.

## Actual browser verification

Used the Codex in-app browser against real Uvicorn and Vite, with an isolated migrated SQLite file at `C:/Users/Aaron/AppData/Local/Temp/sidequest_m5_browser_20261003/smoke.sqlite3`. Personal backend/data remained untouched (only .gitkeep). Test services used backend port 8015, development frontend 5175 and production preview 5176.

Observed browser actions:

1. Open Library with the empty-shelf guidance.
2. Create Moonlit Orchard using interest 4, friction 1, low energy, solo mode, chill/progression tags and notes.
3. Add Harvest autumn crops, 30-minute estimate, priority 2, and notes.
4. Open Tonight; select low energy and solo; request the 45-minute progression recommendation.
5. Verify game/goal, score 84.25, suitability 60; expand and inspect all seven contributions/reasons/inputs, including -2 friction and zero recent play.
6. Toggle the explanation using Enter, then start the accepted quest.
7. Verify the active banner and disabled duplicate-start control; reload and recover the same active session.
8. Check a 390px viewport: stacked layout and no horizontal overflow (observed content width 375px within 390px viewport); reset the override.
9. Open a fresh production-preview tab: recover active state, request/render the recommendation and full explanation, navigate the persisted library/goal journal, and confirm duplicate starts remain disabled. The final fresh production console had no warning/error entries.

No session was finished through the UI or API for cleanup. The isolated file intentionally retains that test active session and its snapshots. Both browser tabs and all three test servers were closed/stopped after evidence capture; temporary data and screenshot artifacts remain outside the repository.

Saved evidence: `C:/Users/Aaron/AppData/Local/Temp/sidequest_m5_browser_20261003/sidequest-active.jpg` and `sidequest-library.jpg`. These show the final production interface, recovered active session, explained recommendation and persisted journal.

During bulk source formatting, the development tab logged transient Vite websocket/hot-update and React hook errors; full reload recovered, and the final fresh production bundle had none. This was a development update observation, not a backend/scoring incompatibility. The first hidden Start-Process test-server launch command was rejected by automatic approval as "blocked by policy"; the test was completed using managed terminal sessions instead, without changing application behavior or requesting permission.

Live browser checks cover the core loop and production reading/recovery. Archive/restore/completion, equivalent/abstention states, error/conflict fixtures and request-shape edge cases were automated frontend checks, not additional claimed live-browser exercises.

## Known limitations and readiness

- No finish/history UI yet; existing API/docs can finish an active session. This intentionally prevents another browser start until backend state is cleared through its lifecycle.
- State is local React state; navigation/reload resets unsaved editor/situation fields and transient results. Active sessions are durable because they come from the backend.
- No polling/cross-tab push notifications. The UI checks active state on load and after failed start; reload picks up other external changes. Backend start-time revalidation remains authoritative.
- All library and audit data is fetched without pagination, consistent with the small personal scope. Large libraries or many equivalent choices create a longer page.
- No full accessibility audit or exhaustive device matrix was performed. Semantic controls, focus styling, accessible labels, automated interactions and one narrow-viewport check provide initial evidence.
- Production hosting/reverse-proxy configuration is deferred. Relative API URLs avoid baking a deployment address into the bundle; preview is only a local verification tool.

Milestone 5 acceptance is satisfied: usable library management, explained recommendations for all four outcomes, accepted-choice start and durable active recovery, 26 passing frontend cases, all 410 backend regressions passing, successful production build, and a real browser smoke loop. README and IMPLEMENTATION_PLAN now describe the runnable frontend. Milestone 6 can add finish/history UI and complete V0.1 verification after separate user review. No Milestone 6 implementation was started.
