# 019: Goal Progression Model Investigation

Date: 2026-10-04 (America/Los_Angeles). Status: research complete; no production change authorized or made.

References: reports [004](004_milestone_1_final_policy.md), [005](005_milestone_2_database_library_api.md), [006](006_milestone_3_recommendation_api.md), [007](007_milestone_4_session_lifecycle.md), [008](008_milestone_5_react_library_recommendation.md), [010](010_v0.1_snapshot_validation_fix.md), [017](017_session_outcome_signal_investigation.md), [018](018_session_outcome_insights.md); PROJECT.md and current production source/tests. Report 019 was the next unused number. Reports 001–018 remain immutable.

## 1. Executive summary

The current model is sufficient for short lists of independently actionable objectives, parallel MMO activities, one-shot objectives, and repeatable practice. It already supports goals spanning sessions and explicit whole-goal completion. It does not know whether an active objective is actionable now or a future plan. Priority and title order cannot safely supply that missing fact.

**M2, optional current/later readiness with multiple current goals, is the strongest minimal persistent extension when users want to record future objectives in Sidequest.** Keep lifecycle separate: active/completed/archived remains the lifecycle; current/later applies to active plans. Do not introduce dependencies, automatic promotion, numeric tracking, or recurrence scheduling. Retain M0 for users who only create actionable goals. A small post-completion next-step prompt is useful but cannot replace readiness for an already populated future plan.

This is a design recommendation, not proof of improved real-world recommendations. Fourteen authored scenarios and 22 new research probes establish mechanics and expose counterexamples; they do not measure owner behavior, enjoyment, accuracy, or elapsed maintenance time. Production remains unchanged and the frozen scorer is preserved.

## 2. Product question and investigation method

Which smallest concept helps Sidequest say what to accomplish now without becoming a quest planner? A goal should describe a recognizable accomplishment or a repeatable practice focus; a session should record what actually happened toward it.

Inspected models, both initial migration dialects, library schemas/routes, recommendation adapter/scorer/projection, session routes/schemas, Library/GoalForm/FinishForm/App/History/recommendation components, existing persistence/recommendation/lifecycle tests, and the referenced reports. Read actual code rather than relying on old milestone descriptions.

`backend/experiments/progression_019.py` contains fictional A–M scenarios plus N, explicit planning facts and six eligibility interpretations. It imports the production scorer, never a database or network. M5's workflow is assessed qualitatively; its static scoring equals M0. M1 is display ordering only, not a hidden queue. No experiment code is imported by production. Additional API probes use migrated temporary SQLite databases. No hosted data, local personal library, provider, or secret was accessed.

## 3. Exact current model and behavior

| Area | Actual contract |
| --- | --- |
| Goal identity | Integer id, required immutable game_id; title up to 200 characters; optional free-text notes |
| Session estimate | Positive estimated_minutes, meaning a useful session chunk, not total remaining effort |
| Preference | Integer priority 1–3, default 2; no readiness meaning |
| Lifecycle | status active/completed/archived; created_at, updated_at, nullable completed_at |
| Constraints | Required parent; completed requires completed_at; active requires null completed_at; completion cannot precede creation; archived can retain prior completion timestamp |
| Completion | Explicit complete endpoint, or optional mark_goal_completed at session finish; never inferred from title, notes, or progress |
| Reopening | Completed/archived goal becomes active, clearing completed_at; parent must be unarchived |
| Archival | Goal archive retains records and any prior completed_at; game archive does not rewrite child status |
| Editing | Title, notes, estimate and priority editable; no reassignment, order, readiness, dependencies, counters or recurrence |
| Recommendation load | All persisted game/goal pairs loaded for audit; inactive pairs are excluded by scorer; game without goals has no synthetic candidate |
| Shared attributes | Interest, energy requirement, social mode, experience tags, friction and completed-game recency shared by all goals of a game |
| Goal-specific score | Estimate and priority can differ; IDs break ties, not semantic chapter order |
| Session finish | Positive confirmed duration, explicit rating, required progress text, optional notes; whole-goal completion defaults false |
| History | Immutable start-time titles/context/full scoring evidence; completed sessions listed separately from active session |

Default goal list includes completed goals, hides archived goals/archived parents unless requested, and sorts by ID. The frontend requests archived goals too and renders a flat list. Game archive visibility has a shelf toggle; goals have no comparable current/completed grouping. No-goal games get an add-goal prompt. A game with only completed/archived goals is not the same UI empty state.

Finishing a session sends the user to History; it does not create, activate, select or start the next goal. Start re-evaluates current recommendations and accepts only a choice in the frozen accepted band; an otherwise eligible goal outside that band cannot be started through the current start endpoint. Partial progress leaves the goal active unless explicitly completed.

## 4. Current limitations

Active means recommendable, even for "Chapter 4" before Chapter 2. Future plans can win on higher priority, or appear among near ties. Free-text prerequisite notes have no effect. Lowering priority does not exclude a goal. Creation order gives stable display/tie ordering, not progression semantics.

Archiving future work and restoring it later is an available workaround, but conflates future intent with abandoned/hidden work and requires extra actions. Creating only the next goal is also valid, but future plans must then live elsewhere or be remembered. Neither limitation means all users need more state.

A separate limitation is **game-level activity fit**: leveling, gold farming and PvP within the same MMO inherit the same energy/social/tags. Current/later cannot fix this when all three are actionable. Do not disguise that limitation as a readiness problem or add overrides during this investigation.

## 5. What already works well

Independent goals compete transparently; parallel goals are supported; whole-goal completion is explicit; repeatable practice can remain active across sessions; estimates represent useful chunks; archive/reopen preserves history; snapshots survive renames and later metadata changes. Free-text progress handles diverse accomplishments without units or invented completion percentages.

M0 is preferable when the owner maintains only a few currently actionable goals. M5 may be enough if objectives are deliberately created just in time. No migration is warranted solely to rearrange a short list.

## 6. What a goal means

Use a concrete intention such as "Reach the next story checkpoint," "Defeat the final boss," "Practice defensive positioning," or "Craft one upgraded item." Completion means the owner says the whole intention is done, not that a session ended.

"Finish chapter 2" may span sessions. "Practice PvP" may intentionally have no terminal point; a session records the specific practice and outcome. "Improve gear" is valid free text but weak guidance; replacing it with a useful next accomplishment improves clarity without numeric state. Do not parse verbs or notes to classify or complete goals.

## 7. Competing models

| Model | New concept | Benefit | Failure / cost | Judgment |
| --- | --- | --- | --- | --- |
| M0 flat | None | Minimal; parallel and recurring practice work | Future active plans compete prematurely | Keep as baseline/default usage |
| M1 ordered flat | Per-game position, display only | Readable planned sequence | Does not change eligibility; reordering maintenance | Not sufficient for progression |
| M2 current/later | Explicit readiness; multiple current | Stores future intent without recommending it | Manual promotion, stale later plans, potentially empty current set | Strongest bounded extension |
| M3 queue | Ordered head; completion promotes next | Convenient strict linear sequence | Blocks parallel/repeatable/branching work; direction changes require queue edits | Reject general default |
| M4 dependencies | Prerequisite edges | Represents true prerequisites | Cycles, edits, reopening, AND/OR/XOR semantics, migrations/UI | Not justified |
| M5 completion workflow | Explicit next-step prompt; nearly unchanged schema | Just-in-time next-goal creation; less navigation | Cannot exclude already active future plans; prompt fatigue | Useful complement or simpler alternative |

No M6: adding another hybrid does not resolve a demonstrated gap better than an optional readiness field plus ordinary completion controls. Models are not graded by completeness or synthetic success percentages.

The reproducible comparison uses the same scores for every retained candidate under every model. M2 only withholds authored later goals; M3 only exposes the first active goal per game; M4 requires all authored prerequisites completed. M0/M1/M5 retain every active pair. Completed records still pass through the frozen scorer for exclusion auditing. No production eligibility was changed.

## 8. Linear progression: scenario A

Fictional RPG: Chapter 2 (priority 2), Chapter 3 (priority 3), Chapter 4 and Finish story (priority 2), all 30-minute useful chunks. Only Chapter 2 is authored current; dependency chain is 2→3→4→finish. Available 60 minutes, medium energy, solo, progression.

M0/M1/M5 recommend Chapter 3 at 93.75; Chapter 2 scores 86.25. A later chapter's priority wins because the model has no prerequisite fact. Equalizing priority would admit all four near-equivalent choices; ID order merely puts Chapter 2 first. M2/M3/M4 initially expose Chapter 2 only. After explicit completion, M2 requires manual promotion; M3/M4 move to Chapter 3 under their additional rules. M5 can offer creation of Chapter 3 if it was not precreated, but its prompt cannot make the original populated library correct by itself.

Recommendation: store Chapter 2 current and future chapters later if the user wants a plan. Do not turn priority into a sequence marker. The named chapter prerequisites here are fictional authored facts, not inferred game knowledge.

## 9. Parallel MMO progression: scenarios B and F

B has leveling, gold farming, PvP practice and professions, all independently actionable; F has main story, companion quest and an optional dungeon. All are current, priority 2, 30 minutes. M0/M1/M2/M4/M5 expose all four B goals (three F goals) at 86.25 and return multiple_equivalent. M3 restricts each game to its head, throwing away valid choices.

This falsifies the claim that all progression should be a queue, and the claim that readiness improves every library: M2 provides no ranking advantage here. The shared game-level fit factors cannot distinguish activities. Current/later should allow several current goals and require no additional classification action for the all-current case.

## 10. Repeatable practice: scenario C

Practice PvP and Explore new map are both current. All models except M3 expose both at 86.25; M3 leaves practice at the head indefinitely if the owner correctly does not complete it. Keep practice active; record session-specific progress; archive it when no longer relevant.

No repeatable flag, repeat counter, daily reset or automatic reopening is justified. A future explicit "practice focus" display label might aid wording, but would need actual confusion evidence. Recency remains completed-session recency per game, not "times this repeatable goal succeeded."

## 11. One-shot and branching objectives: scenarios D and E

D's final boss (priority 3) scores 93.75 in all models before completion; explicit completion removes it. Do not invent a successor. E has mutually exclusive faction A/B campaigns, both initially possible; all models except M3 show both at 86.25. M3 picks faction A solely because of queue position. A dependency graph with both roots cannot express "choosing A abandons B" without another exclusion mechanism.

The owner can choose one direction, keep that goal current and put the other later or archive it. Later means still intended; archive better represents a rejected branch. M2 does not enforce mutual exclusion and must not claim to. An exclusive-choice graph is disproportionate to this application.

## 12. Current/later readiness and falsification

M2 answers "May this be considered now?" independently of importance. Current is permission to compete, not a promise of selection or suitability. Later is an explicit planning exclusion, not a score penalty. Multiple current goals remain valid.

Counterexamples: B/F gain no new recommendation value; G's vague objective is not made concrete; H has no goal to classify; I has no successor to promote; K retains same-game near ties. In M, Chapter 2 is complete with 25 minutes remaining and a 20-minute Chapter 3 marked later: M2 yields no_eligible until the owner promotes it, while M3/M4 automatically expose it. In N, 120-minute current encounter cannot fit 30 minutes; later 20-minute task could fit but remains withheld. This abstention is correct if later reflects a true prerequisite; undesirable if the label is stale convenience. Do not auto-promote to conceal the distinction.

For N, offer review of later goals or a smaller genuinely useful current chunk. Do not silently lower the current estimate, ignore prerequisites, or reinterpret priority. If the 120-minute estimate meant total effort rather than useful-session length, correcting that input is better than introducing readiness machinery.

M2 is worth its state only if recording future plans is a real owner need. Main risk: forgotten promotion causes apparent lack of options. Later must stay visible in a labeled section and abstention guidance must identify withheld plans. There is no evidence supporting expiry timers, inferred readiness or automatic promotion.

## 13. Ordering

M1 permits a readable sequence but every active goal still competes. Treating the first goal as the only eligible one changes M1 into M3; changing score tie-breaking to position changes frozen policy. Neither is a display-only improvement.

IDs are not user-editable positions. Reopening an old goal keeps its old ID. Editing a title does not reorder it. For a personal library, current/later sections plus existing deterministic IDs are sufficient initially; drag-and-drop order and bulk resequencing are deferred.

## 14. Dependencies

M4 can encode A but has unnecessary costs: cycle detection, missing edges, prerequisites archived instead of completed, completed prerequisites reopened, AND/OR branches, and relationship editing. E additionally needs mutual exclusion, not merely prerequisites.

No scenario establishes a need for arbitrary DAGs. Owner-authored current/later covers the intended exclusion with less metadata. Text notes can retain planning context without being executable rules. Dependencies are rejected for the smallest milestone.

## 15. Automatic promotion

M3 saves promotion actions for a true linear queue, but makes false assumptions for B/C/E/F/J. Completing a goal does not imply wanting its next neighbor, having unlocked it, or having time/energy for it. Archiving a queue head is not completion. Repeatable heads may never clear.

Keep promotion explicit. A completion prompt may show existing later goals as choices but should not activate the first one, rewrite priority, start a new session or imply dependency satisfaction. No successor should be invented for D/I.

## 16. Numeric progress

Not justified. Chapters, gear, skills and practice do not share meaningful units. Counters require target units, partial increments, correction semantics, ownership of session attribution, reopening behavior and migration. "50% complete" would be manufactured for most current goals.

Keep required progress text and explicit whole-goal completion. An owner can write a level or chapter checkpoint in the text without making Sidequest maintain a counter. No LLM extraction or note inference.

## 17. Structured completion workflow and falsification of M5

The existing finish form already asks whether the whole goal is complete and otherwise keeps it active. M5 must add useful continuity, not duplicate this checkbox. After a successful whole-goal completion, a skippable "What next?" can link to another existing goal or a prefilled new-goal form for that game. Partial session completion should not force next-goal maintenance.

M5 is enough for just-in-time A: create Chapter 2, finish/complete, create Chapter 3. It improves I's all-completed empty guidance and M's remaining-time handoff. But with A's four goals already active, M5's unchanged eligibility still recommends Chapter 3 too early. It cannot store future plans separately without a readiness concept or archive workaround. It also cannot clarify G automatically.

Prompt risks: extra interruption after every practice session, confusing session completion with goal completion, accidental goal creation, and extra failure handling. Restrict any future prompt to explicit whole-goal completion, make skipping safe, and keep session finish committed even if a later separate goal action fails. Do not start the next session automatically. Any remaining-time recommendation needs a fresh user-confirmed context, not an inferred subtraction from reported duration.

## 18. Recommendation/scoring interaction

Conceptual future pipeline: lifecycle/readiness eligibility → existing hard time/social eligibility → situational suitability → preference ranking → accepted choices. Readiness belongs before scoring. It must not add points or alter suitability. Interest/priority do not unlock goals.

Frozen production factors: interest 25, priority 15, time 10, energy 30, experience 20, friction penalty up to 10, recency penalty up to 3. Suitability remains time+energy+experience ≥25; no total-score gate. Near ties remain within 3 points of best suitable score; order total descending, priority descending, goal ID then game ID ascending. All are existing heuristics, not calibrated measures.

An added readiness filter would intentionally change the future API's candidate eligibility contract even if scoring.py is byte-identical. It requires explicit implementation authorization, transparent withheld reasons, regression tests and documented version/contract handling. Do not silently pass `goal_status="later"` to the frozen Candidate: it accepts only active/completed/archived. Existing full audits load all pairs; a future adapter must deliberately preserve visibility of later exclusions without fabricating scores or forcing invalid frozen-domain values.

This report's separate `withheld` results are research metadata, not a new production response field. No session outcomes influence scores. Starts must recheck readiness as well as accepted-choice membership if readiness is later adopted.

## 19. Priority

Keep priority as importance among eligible suitable choices. A low-priority current task is still ready; a high-priority later task is still not ready. A demonstrates the priority/readiness conflict; tests also reduce current priority to 1 and confirm readiness interpretation still admits it.

Using priority 1 to park future goals is unreliable: it leaves them eligible, can recommend them when other candidates fail, and loses the user's importance information. No new priority levels or weights are proposed.

## 20. Duration and remaining time

Let r = useful estimate / available time. Above 1 is hard-excluded. Time points are 20r below 0.5, 10 from 0.5 through 0.9, and 10−20(r−0.9) above 0.9 through 1. No change proposed.

K's 30- and 45-minute goals both receive 10 in a 60-minute window and remain near ties. N excludes 120 minutes even though current; M's 20 minutes in 25 receives 10 once eligible. Readiness never overrides duration. Finishing early does not supply reliable remaining time automatically: actual_duration is user-confirmed and may differ from elapsed wall time. Ask for a fresh context before another recommendation.

## 21. Estimated maintenance cost

These are **illustrative interaction counts, not observed time, measured burden, or accuracy**. Count one create/complete/archive/restore/promote as one saved state operation; field selections within creation are listed separately. Assume four linear goals planned upfront, created in order, and each explicitly completed once. Navigation, retries and edit complexity are omitted. Hypothetical M3/M4 forms do not exist.

| Model/workflow | Saved operations for four-step chain | Additional decisions / caveat |
| --- | --- | --- |
| M0, all upfront active | 4 create + 4 complete = 8 | Does not protect sequence; cheap but incorrect for this fixture |
| M0 with archive workaround | 4 create + 3 archive + 4 complete + 3 restore = 14 | Three future goals temporarily misuse archive semantics |
| M1 display order | 8 plus any reorders | Still does not protect sequence; initial creation order assumed |
| M2 current/later | 4 create + 4 complete + 3 promote = 11 | Three later selections during creation; manual readiness reviews |
| M3 queue | 4 create + 4 complete = 8 | Assumes automatic head progression, no reorder; parallel exceptions add work |
| M4 edges entered at creation | 4 create + 4 complete = 8 | Three prerequisite selections; corrections/branch semantics omitted |
| M5 just-in-time | 4 create + 4 complete = 8 | Cannot store the future list as active goals; next-step prompts may reduce navigation only |

Parallel all-current goals add no promotion operations in M2 if current is default. A change of direction such as J requires putting level 40 later and making crafting current if necessary (one or two explicit changes); a queue requires reordering its head. A stale later set needs owner review. More state cannot be called zero-maintenance simply because its fields are optional.

## 22. History and session implications

Existing title/context/full recommendation snapshots are immutable through API paths. Goal title, estimate, priority/status at start are represented in selected candidate evidence. **Goal notes are not included in candidate/recommendation snapshots**, so editing planning notes does not preserve their original wording in session history. Session notes are separate finish-time text.

`mark_goal_completed` is a request flag, not a persisted per-session field. Current goal status/completed_at cannot reliably attribute an old session's goal completion, especially after reopen. Do not infer completion from progress prose, reconstruct historical readiness, backfill dependency satisfaction or recompute old explanations. Report 018 outcome summaries remain descriptive and unaffected.

If readiness is implemented later, preserve old snapshot_version=1 readers exactly. Record new start-time eligibility evidence explicitly with a deliberate versioned contract if necessary; do not require a new field in historical candidate JSON. An active session started before a goal is moved later should still be finishable; readiness affects future starts, not destruction or invalidation of saved sessions. Whole-goal completion still requires the existing archive restrictions and atomic finish behavior.

## 23. Schema and migration implications

M0/M5 require no progression column. M1 needs position and ordering operations. M3 adds ordering plus head/promotion rules. M4 needs an edge table, FK/cycle semantics and deeper operations. M2 can add a narrowly constrained `readiness` value current/later while retaining lifecycle status.

Proposed future M2 migration: explicit next SQLite and PostgreSQL migration, non-null readiness default current, CHECK of its two values; all existing goals map to current, so existing active eligibility initially remains identical. Completed/archived records keep their lifecycle and timestamps; readiness is irrelevant while inactive. No renames, regenerated IDs, session changes or historical backfill. Do not add `later` to the existing lifecycle enum merely to avoid naming a field: database constraints and the frozen Candidate enum would both need deliberate changes.

Proposed lifecycle semantics for review: new goals default current; later goals may be explicitly completed or archived as existing active goals can; restore/reopen explicitly means "Restore/Reopen as current" and resets readiness to current, preserving the existing action's recommendable meaning. UI wording must make this reset clear. Editing metadata must not promote a later goal. Archived parent keeps all children ineligible regardless of readiness. Later is not a second archival state.

Rollback is not provided by the current forward migration runner; restoring a backup and rolling back code is an operational decision, not dropping a column casually. Treat making all later goals current as a visible product change, not an invisible rollback. Future database tests must verify both dialects, constraints, defaults and reopen behavior. No migration was created or run in this investigation.

## 24. Minimal UI concepts

Library: Current, Later, and collapsed Completed/Archived sections for the selected game. Current may contain several goals. Simple "Move to later" / "Make current" controls; creation defaults current with an optional later choice. No drag-and-drop, progress bars or dependency editor.

No-current guidance should distinguish no goals, all goals completed, all plans later, time exclusions and poor situational fit. Later plans remain visible and reviewable rather than silently disappearing. Whole-goal completion can offer a skippable next-step link; partial completion should keep existing workflow. Tonight explanations must distinguish "later, not considered" from "eligible but unsuitable" and ordinary time/social exclusions. These are sketches, not implemented UI or tested usability claims.

## 25. Rejected alternatives

Reject chapter-name sorting, parsing prerequisite notes, priority-as-readiness, game-only fallback recommendations, automatic shortening of estimates, mandatory one-current-per-game, automatic next-goal creation/promotion, daily resets, default numeric completion, outcome-driven goal ranking and arbitrary dependency graphs. None is required to represent the demonstrated missing fact. Ordering can be added later only if list navigation itself proves painful.

## 26. Recommended direction

Approve **optional M2 current/later readiness** only if storing future objectives inside Sidequest is desired. It is the smallest persistent addition that fixes A/J without breaking B/C/F. Keep all-existing-goals-current migration compatibility and multiple current goals. Pair it with clear library sections and no-current guidance; defer a separate post-completion wizard.

If the owner prefers just-in-time goal creation, choose M5 alone and keep the schema. Its main improvement is continuity/navigation after explicit completion, not new recommendation intelligence. That is a credible lower-scope alternative, not a failed model. Do not implement both a queue and readiness to cover every scenario.

## 27. Weaknesses and human decisions

Synthetic readiness and prerequisites were authored by the investigator. They are not verified gaming facts or evidence that the owner will maintain them. All fictional activities deliberately share simple game fit attributes; the probe isolates progression rather than claiming realistic PvP energy classification.

Review: Do you want to store future plans in Sidequest? Will manual promotion be tolerable? Does "current" mean actionable rather than favorite or exclusive focus? Should restore/reopen explicitly reset to current? Is abstaining in N preferable to recommending a stale later plan? Is same-game activity-fit granularity a larger real problem than future plans? Should a next-step prompt wait until readiness proves useful?

The proposal risks stale readiness and false certainty; it cannot enforce dependencies or branch exclusivity. Empty current sets and multiple similar current goals remain possible. No measured owner maintenance or recommendation improvement is claimed.

## 28. Production change decision

**No production change in this investigation.** Recommend a bounded future goal-model extension, not immediate adoption. Scoring, models, migrations, API contracts, frontend and session lifecycle remain unchanged. No cloud, deployment, personal data, provider or credential operation occurred. The Report 018 feature remains independent.

## 29. Smallest next implementation milestone

Subject to owner review: "Optional current/later goal readiness." Limit scope to one constrained field with compatibility migration, goal create/edit/move semantics, multiple-current library sections, visible later/no-current guidance, and an explicit audited eligibility boundary/start-time recheck that preserves frozen scoring calculations and old session snapshots.

Required acceptance: existing goals behave identically after migration; later never scores/starts; multiple current remain allowed; priority cannot unlock later; time/social/suitability gates unchanged; completion/archive/reopen rules explicit; active sessions remain finishable; history remains readable and unchanged; both database dialects covered; existing outcome summaries unaffected. If an audit contract cannot preserve old readers without modifying frozen scorer, stop for policy/version review. No ordering, dependency, automatic promotion, numeric progress or recurrence field. Do not implement until separately authorized.

## 30. Tests and verification

Baseline complete backend: **665 passed, 50 skipped**, 27.37s. Baseline frontend: **68 passed**, 3 files, 13.27s. New focused research tests: **22 passed**, 1.19s. Final complete backend: **687 passed, 50 skipped**, 26.93s (all 665 prior tests plus 22 new probes). Final complete frontend: **68 passed**, 3 files, 13.15s. Production frontend build passed with Vite 8.3.2, 27 modules, 145ms. No failures. `git diff --check` passed.

Research coverage: A–N scores and input-order determinism across six models; score sums; M1/M5 static equivalence to M0; high-priority future displacement; priority-independent readiness; parallel and repeatable queue failure; manual promotion/remaining time; long-current exclusion; lack of branch exclusivity in graphs. Actual temporary-SQLite API checks demonstrate title/notes do not gate readiness, completion is explicit, progress text does not infer completion, no next goal is created, historical snapshots stay unchanged and goal notes/completion flags are not retrospectively available.

Skipped backend cases are the existing opt-in external PostgreSQL/maintenance and dialect-dependent cases; no PostgreSQL service or cloud test was started. This task's actual API probes use isolated SQLite only. No new UI code needs a new interaction test; the complete existing frontend suite/build protects the unchanged interface. Commands: backend `.venv/Scripts/python.exe -m pytest -q --tb=short`; frontend `npm test -- --run` and `npm run build`; `git diff --check`.

## 31. Files created/changed

- Created this immutable Report 019.
- Appended Report 019 to reports/README.md.
- Created backend/experiments/progression_019.py: fictional, standalone comparison runner.
- Created backend/tests/test_progression_019.py: 22 isolated research/API probes.

No production file or older report changed. No commit, push or deployment performed. Reproduce the full fixture results from backend with `.venv/Scripts/python.exe -m experiments.progression_019`; output contains only fictional metadata.

## 32. Frozen scorer and historical preservation

Before and after investigation: policy `v0.1-final-004`, scoring.py SHA-256 `b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a`, exact match. Reports 001–018 were hashed before investigation and compared afterward: all 18 match. Git status/diff confirms only the four files listed in section 31 are changed/created, with no production modifications.

### Scenario interpretations and surprises

This table explains the full numeric appendix below. Within a near tie, the first ID is a display convention, not proof of a better goal.

| Scenario | Why the models produce the listed result | Surprise / practical implication |
| --- | --- | --- |
| A linear chapters | Chapter 3's priority adds 7.5 over Chapter 2; M2/M3/M4 withhold future chapters | Order alone and completion prompt do not prevent a premature recommendation |
| B parallel MMO | Four current goals share all score factors; queue exposes only leveling | Readiness adds no ranking benefit; queue removes valid alternatives |
| C practice | Both activities share score; queue head is practice | A nonterminal practice goal can block a queue indefinitely |
| D final boss | Single high-priority eligible suitable goal | No successor is required after explicit completion |
| E factions | Both root objectives have equal score and no prerequisites | Graphs do not express exclusive direction; a queue arbitrarily chooses A |
| F main/optional | Three independent current objectives share score | Main story is not automatically a prerequisite for optional work |
| G improve gear | Single active goal scores 86.25 under every model | A confident-looking clear choice can still describe a vague accomplishment; structure does not fix wording |
| H no goal | Empty candidate collection yields no_eligible under every model | Readiness/ordering cannot replace creating a useful objective; do not invent game-only fallback |
| I all completed | Both goals receive lifecycle exclusions, no scores, no_eligible | Auto-promotion has nothing left to promote; UI needs add/reopen guidance, not fabricated goals |
| J change direction | Level 40's higher priority wins M0/M1/M4/M5; M2 withholds it; queue still exposes its old head | Current/later expresses changed intent; dependency-free does not mean desired now; archival is another valid owner choice |
| K near ties | 30 and 45 minutes both lie on the duration plateau; equal totals 86.25 | Multiple current same-game choices remain; readiness cannot manufacture a unique winner |
| L partial progress | Goal stays active, all models score it 86.25 | No text inference or automatic completion/promotion; API probes confirm explicit checkbox controls status |
| M early completion | Completed Chapter 2 excluded; Chapter 3 fits 25 minutes and scores 86.25 if admitted; M2 withholds later | Manual promotion can interrupt continuation; a fresh context and explicit selection are safer than inferred remaining time |
| N 120/20 conflict | Current 120-minute goal excluded; later 20-minute goal scores 93.75 only in M0/M1/M5; M2/M3/M4 abstain | Abstention may reflect a real prerequisite or stale metadata; synthetic scores cannot decide which |

Post-completion D with its only goal completed yields no_eligible in all models, like I. Post-completion A exposes Chapter 3 automatically only under M3/M4; M2 needs promotion, while M0/M1/M5 had already admitted it. These transition probes are distinct from the appendix's explicitly stated static input states. No automatic behavior was added to production.

## Appendix: reproducible scenario inputs and full scoring comparisons

All inputs below are fictional. Fixed evaluation clock: 2026-10-04T19:00:00Z. Candidate defaults: game 1 Fictional RPG (game 2 Fictional MMO where stated), interest 4, low energy requirement, solo-only, progression/challenge tags, friction 0, no prior completed play, unarchived, active. Goal defaults: useful estimate 30 minutes, priority 2. Context defaults: 60 minutes, medium energy, solo, progression. Only listed overrides differ. The empty H scenario represents a game without any goals; it has no scorer candidate.

Planning current/position/prerequisites exist only in the experiment. Rank rows expose total, suitability and all seven factors. The recommendation list is the accepted near-tie set, not all ranked entries; first means deterministic display choice, not a uniquely better option. Withheld planning candidates have no score in that model. Existing lifecycle/time exclusions remain separately visible. Full machine-generated results follow.

### A. Linear RPG chapters

Context: `{'available_minutes': 60, 'energy': 'medium', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Chapter 2 | 30 | 2 | active | True | 1 | none |
| 2 | Chapter 3 | 30 | 3 | active | False | 2 | (1,) |
| 3 | Chapter 4 | 30 | 2 | active | False | 3 | (2,) |
| 4 | Finish story | 30 | 2 | active | False | 4 | (3,) |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | clear_recommendation: [2]; first 2 | none | none |
| M1 | clear_recommendation: [2]; first 2 | none | none |
| M2 | clear_recommendation: [1]; first 1 | 2: Explicitly later; 3: Explicitly later; 4: Explicitly later | none |
| M3 | clear_recommendation: [1]; first 1 | 2: Not queue head; 3: Not queue head; 4: Not queue head | none |
| M4 | clear_recommendation: [1]; first 1 | 2: Uncompleted prerequisite; 3: Uncompleted prerequisite; 4: Uncompleted prerequisite | none |
| M5 | clear_recommendation: [2]; first 2 | none | none |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 2 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M0 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M0 | 3 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M0 | 4 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 2 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 3 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 4 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M3 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 2 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 3 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 4 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |

### B. Parallel MMO goals

Context: `{'available_minutes': 60, 'energy': 'medium', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Leveling | 30 | 2 | active | True | 1 | none |
| 2 | Farm gold | 30 | 2 | active | True | 2 | none |
| 3 | Practice PvP | 30 | 2 | active | True | 3 | none |
| 4 | Train professions | 30 | 2 | active | True | 4 | none |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | multiple_equivalent: [1, 2, 3, 4]; first 1 | none | none |
| M1 | multiple_equivalent: [1, 2, 3, 4]; first 1 | none | none |
| M2 | multiple_equivalent: [1, 2, 3, 4]; first 1 | none | none |
| M3 | clear_recommendation: [1]; first 1 | 2: Not queue head; 3: Not queue head; 4: Not queue head | none |
| M4 | multiple_equivalent: [1, 2, 3, 4]; first 1 | none | none |
| M5 | multiple_equivalent: [1, 2, 3, 4]; first 1 | none | none |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M0 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M0 | 3 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M0 | 4 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 3 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 4 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 3 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 4 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M3 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 3 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 4 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 3 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 4 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |

### C. Repeatable practice

Context: `{'available_minutes': 60, 'energy': 'medium', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Practice PvP | 30 | 2 | active | True | 1 | none |
| 2 | Explore new map | 30 | 2 | active | True | 2 | none |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | multiple_equivalent: [1, 2]; first 1 | none | none |
| M1 | multiple_equivalent: [1, 2]; first 1 | none | none |
| M2 | multiple_equivalent: [1, 2]; first 1 | none | none |
| M3 | clear_recommendation: [1]; first 1 | 2: Not queue head | none |
| M4 | multiple_equivalent: [1, 2]; first 1 | none | none |
| M5 | multiple_equivalent: [1, 2]; first 1 | none | none |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M0 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M3 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |

### D. One-shot final boss

Context: `{'available_minutes': 60, 'energy': 'medium', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Defeat final boss | 30 | 3 | active | True | 1 | none |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | clear_recommendation: [1]; first 1 | none | none |
| M1 | clear_recommendation: [1]; first 1 | none | none |
| M2 | clear_recommendation: [1]; first 1 | none | none |
| M3 | clear_recommendation: [1]; first 1 | none | none |
| M4 | clear_recommendation: [1]; first 1 | none | none |
| M5 | clear_recommendation: [1]; first 1 | none | none |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 1 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 1 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 1 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M3 | 1 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 1 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 1 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |

### E. Choose one faction

Context: `{'available_minutes': 60, 'energy': 'medium', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Faction A campaign | 30 | 2 | active | True | 1 | none |
| 2 | Faction B campaign | 30 | 2 | active | True | 2 | none |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | multiple_equivalent: [1, 2]; first 1 | none | none |
| M1 | multiple_equivalent: [1, 2]; first 1 | none | none |
| M2 | multiple_equivalent: [1, 2]; first 1 | none | none |
| M3 | clear_recommendation: [1]; first 1 | 2: Not queue head | none |
| M4 | multiple_equivalent: [1, 2]; first 1 | none | none |
| M5 | multiple_equivalent: [1, 2]; first 1 | none | none |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M0 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M3 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |

### F. Main and optional objectives

Context: `{'available_minutes': 60, 'energy': 'medium', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Main story | 30 | 2 | active | True | 1 | none |
| 2 | Companion quest | 30 | 2 | active | True | 2 | none |
| 3 | Optional dungeon | 30 | 2 | active | True | 3 | none |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | multiple_equivalent: [1, 2, 3]; first 1 | none | none |
| M1 | multiple_equivalent: [1, 2, 3]; first 1 | none | none |
| M2 | multiple_equivalent: [1, 2, 3]; first 1 | none | none |
| M3 | clear_recommendation: [1]; first 1 | 2: Not queue head; 3: Not queue head | none |
| M4 | multiple_equivalent: [1, 2, 3]; first 1 | none | none |
| M5 | multiple_equivalent: [1, 2, 3]; first 1 | none | none |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M0 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M0 | 3 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 3 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 3 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M3 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 3 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 3 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |

### G. Vague objective

Context: `{'available_minutes': 60, 'energy': 'medium', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Improve gear | 30 | 2 | active | True | 1 | none |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | clear_recommendation: [1]; first 1 | none | none |
| M1 | clear_recommendation: [1]; first 1 | none | none |
| M2 | clear_recommendation: [1]; first 1 | none | none |
| M3 | clear_recommendation: [1]; first 1 | none | none |
| M4 | clear_recommendation: [1]; first 1 | none | none |
| M5 | clear_recommendation: [1]; first 1 | none | none |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M3 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |

### H. Backlog game without goals

Context: `{'available_minutes': 60, 'energy': 'medium', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | No goals | — | — | — | — | — | — |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | no_eligible: []; first None | none | none |
| M1 | no_eligible: []; first None | none | none |
| M2 | no_eligible: []; first None | none | none |
| M3 | no_eligible: []; first None | none | none |
| M4 | no_eligible: []; first None | none | none |
| M5 | no_eligible: []; first None | none | none |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | none | — | — | — | — | — | — | — | — | — |
| M1 | none | — | — | — | — | — | — | — | — | — |
| M2 | none | — | — | — | — | — | — | — | — | — |
| M3 | none | — | — | — | — | — | — | — | — | — |
| M4 | none | — | — | — | — | — | — | — | — | — |
| M5 | none | — | — | — | — | — | — | — | — | — |

### I. All planned goals completed

Context: `{'available_minutes': 60, 'energy': 'medium', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Chapter 2 | 30 | 2 | completed | True | 1 | none |
| 2 | Chapter 3 | 30 | 2 | completed | True | 2 | none |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | no_eligible: []; first None | none | 1: Goal is completed; only active goals are eligible.; 2: Goal is completed; only active goals are eligible. |
| M1 | no_eligible: []; first None | none | 1: Goal is completed; only active goals are eligible.; 2: Goal is completed; only active goals are eligible. |
| M2 | no_eligible: []; first None | none | 1: Goal is completed; only active goals are eligible.; 2: Goal is completed; only active goals are eligible. |
| M3 | no_eligible: []; first None | none | 1: Goal is completed; only active goals are eligible.; 2: Goal is completed; only active goals are eligible. |
| M4 | no_eligible: []; first None | none | 1: Goal is completed; only active goals are eligible.; 2: Goal is completed; only active goals are eligible. |
| M5 | no_eligible: []; first None | none | 1: Goal is completed; only active goals are eligible.; 2: Goal is completed; only active goals are eligible. |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | none | — | — | — | — | — | — | — | — | — |
| M1 | none | — | — | — | — | — | — | — | — | — |
| M2 | none | — | — | — | — | — | — | — | — | — |
| M3 | none | — | — | — | — | — | — | — | — | — |
| M4 | none | — | — | — | — | — | — | — | — | — |
| M5 | none | — | — | — | — | — | — | — | — | — |

### J. Change direction

Context: `{'available_minutes': 60, 'energy': 'medium', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Reach level 40 | 30 | 3 | active | False | 1 | none |
| 2 | Craft equipment | 30 | 2 | active | True | 2 | none |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | clear_recommendation: [1]; first 1 | none | none |
| M1 | clear_recommendation: [1]; first 1 | none | none |
| M2 | clear_recommendation: [2]; first 2 | 1: Explicitly later | none |
| M3 | clear_recommendation: [1]; first 1 | 2: Not queue head | none |
| M4 | clear_recommendation: [1]; first 1 | none | none |
| M5 | clear_recommendation: [1]; first 1 | none | none |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 1 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M0 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 1 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M3 | 1 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 1 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 1 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |

### K. Same-game similar scores

Context: `{'available_minutes': 60, 'energy': 'medium', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Story checkpoint | 30 | 2 | active | True | 1 | none |
| 2 | Companion checkpoint | 45 | 2 | active | True | 2 | none |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | multiple_equivalent: [1, 2]; first 1 | none | none |
| M1 | multiple_equivalent: [1, 2]; first 1 | none | none |
| M2 | multiple_equivalent: [1, 2]; first 1 | none | none |
| M3 | clear_recommendation: [1]; first 1 | 2: Not queue head | none |
| M4 | multiple_equivalent: [1, 2]; first 1 | none | none |
| M5 | multiple_equivalent: [1, 2]; first 1 | none | none |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M0 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M3 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |

### L. Partial progress leaves goal active

Context: `{'available_minutes': 60, 'energy': 'medium', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Finish chapter 2 | 30 | 2 | active | True | 1 | none |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | clear_recommendation: [1]; first 1 | none | none |
| M1 | clear_recommendation: [1]; first 1 | none | none |
| M2 | clear_recommendation: [1]; first 1 | none | none |
| M3 | clear_recommendation: [1]; first 1 | none | none |
| M4 | clear_recommendation: [1]; first 1 | none | none |
| M5 | clear_recommendation: [1]; first 1 | none | none |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M3 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 1 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |

### M. Goal completed with time remaining

Context: `{'available_minutes': 25, 'energy': 'medium', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Chapter 2 | 30 | 2 | completed | True | 1 | none |
| 2 | Chapter 3 | 20 | 2 | active | False | 2 | (1,) |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | clear_recommendation: [2]; first 2 | none | 1: Goal is completed; only active goals are eligible., Needs 30 minutes; only 25 available. |
| M1 | clear_recommendation: [2]; first 2 | none | 1: Goal is completed; only active goals are eligible., Needs 30 minutes; only 25 available. |
| M2 | no_eligible: []; first None | 2: Explicitly later | 1: Goal is completed; only active goals are eligible., Needs 30 minutes; only 25 available. |
| M3 | clear_recommendation: [2]; first 2 | none | 1: Goal is completed; only active goals are eligible., Needs 30 minutes; only 25 available. |
| M4 | clear_recommendation: [2]; first 2 | none | 1: Goal is completed; only active goals are eligible., Needs 30 minutes; only 25 available. |
| M5 | clear_recommendation: [2]; first 2 | none | 1: Goal is completed; only active goals are eligible., Needs 30 minutes; only 25 available. |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | none | — | — | — | — | — | — | — | — | — |
| M3 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M4 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |
| M5 | 2 | 86.25 | 60.0 | 18.75 | 7.5 | 10.0 | 30 | 20 | 0.0 | 0 |

### N. Long current versus short later

Context: `{'available_minutes': 30, 'energy': 'low', 'social_preference': 'solo', 'desired_experience': 'progression'}`.

| ID | Goal | Minutes | Priority | Lifecycle | Current? | Position | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Current long encounter | 120 | 2 | active | True | 1 | none |
| 2 | Later short task | 20 | 3 | active | False | 2 | (1,) |

| Model | Outcome / accepted goal IDs | Withheld | Excluded |
| --- | --- | --- | --- |
| M0 | clear_recommendation: [2]; first 2 | none | 1: Needs 120 minutes; only 30 available. |
| M1 | clear_recommendation: [2]; first 2 | none | 1: Needs 120 minutes; only 30 available. |
| M2 | no_eligible: []; first None | 2: Explicitly later | 1: Needs 120 minutes; only 30 available. |
| M3 | no_eligible: []; first None | 2: Not queue head | 1: Needs 120 minutes; only 30 available. |
| M4 | no_eligible: []; first None | 2: Uncompleted prerequisite | 1: Needs 120 minutes; only 30 available. |
| M5 | clear_recommendation: [2]; first 2 | none | 1: Needs 120 minutes; only 30 available. |

| Model | Ranked goal ID | Total | Suitability | Interest | Priority | Time | Energy | Experience | Friction | Recent play |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 2 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M1 | 2 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
| M2 | none | — | — | — | — | — | — | — | — | — |
| M3 | none | — | — | — | — | — | — | — | — | — |
| M4 | none | — | — | — | — | — | — | — | — | — |
| M5 | 2 | 93.75 | 60.0 | 18.75 | 15.0 | 10.0 | 30 | 20 | 0.0 | 0 |
