# 017 — Session Outcome Signal Investigation

Date: 2026-10-04 (America/Los_Angeles). Status: complete research; no production policy adoption.
Control: production V0.1, `v0.1-final-004`. All records in this investigation are fictional.
This is a new historical record; reports 001–016 were preserved.

## 1. Executive summary

Keep V0.1 unchanged. Enjoyment is the strongest recorded outcome signal, but the existing data cannot establish that adding it improves recommendations. Twenty synthetic scenarios, six adjustment magnitudes, asymmetric adjustments and repeated recommendation/play simulations expose meaningful failure modes.

The strongest general signal candidate for further research is M3exp: a bounded enjoyment adjustment with confidence shrinkage and age decay. At ±1 it limits single-session influence and retains the control's 25/5 selection distribution in the equal-enjoyment loop, although its longest streak increases from five to six. This is a behavioral observation, not evidence of predictive accuracy or an optimized coefficient.

M4's near-tie restriction protects large explicit preference gaps, but does **not** prevent feedback loops: it produces a 28-session streak at every tested magnitude, including ±1. M5's contextual variant corrects one important counterexample but fragments already sparse history. No tested ranking model warrants production adoption.

## 2. Research question

Can recorded play-session outcomes improve future deterministic recommendations while preserving explicit preferences, bounded influence, cold-start stability, explainability and resistance to feedback loops? Synthetic cases test behavior; there are no ground-truth recommendation labels, personal records or accuracy estimates.

## 3. Existing Sidequest behavior

The accepted pipeline is eligibility → situational suitability → preference ranking → recommendation. Historical reports [004](004_milestone_1_final_policy.md), [006](006_milestone_3_recommendation_api.md), [007](007_milestone_4_session_lifecycle.md) and [010](010_v0.1_snapshot_validation_fix.md) document the policy and integration.

Hard filtering rejects insufficient available time and explicit solo/social incompatibility. Suitability is time fit (up to 10), energy compatibility (up to 30) and experience match (20). Its threshold is 25. Preference cannot rescue an unsuitable candidate. Interest contributes up to 25, priority up to 15, friction subtracts up to 10 and recent play subtracts up to 3. These factors remain unchanged.

One interest step is 6.25; one priority step is 7.5; one friction step costs 2. Energy fit is full when requirements do not exceed energy, half for one level above and zero for two levels above. Time fit rises to full credit at half the available window, remains full through 90%, then declines to 8 at the full window. These rules and the 3-point near-tie band remain frozen heuristics. Ordering is descending score, descending priority, ascending goal ID, ascending game ID.

Only eligible, suitable candidates can receive experimental ranking influence. `no_eligible` and `no_good_fit` remain intact; experiments never change eligibility, suitability or acceptance.

## 4. Exact session/outcome information actually available

Repository inspection covered `backend/app/models.py`, schemas, session/recommendation routes, scoring, migrations and frontend finish/history flows.

| Information | Recorded meaning | Limit |
| --- | --- | --- |
| Game/goal IDs and title snapshots | Selected activity and goal at session start | Selection is not random; it may be an accepted alternative |
| started_at / finished_at | Backend timestamps; null finish identifies active sessions | Wall-clock time includes interruptions; no pause telemetry |
| actual_duration_minutes | Required positive integer on finish; owner can edit suggested elapsed minutes | Not an objective measure of engagement or satisfaction |
| enjoyment_rating | Required integer 1–5 on finish | UI starts at 3 (“Okay”); no flag distinguishes active rating selection from accepting the default |
| progress | Required nonblank free text | “No progress” is valid; no standardized units or success classification |
| notes | Optional free text | No reliable structured outcome semantics |
| situation_snapshot | Available minutes, energy, social preference, desired experience | Describes start context, not actual state throughout the session |
| recommendation_snapshot | Evaluation version, scores, factors, candidates, choices and selected item | Does not record all later rejected/exposed choices or counterfactual enjoyment |
| mark_goal_completed | Finish request changes current Goal status/completed_at | **Not saved as a session-level completion flag**; later goal edits prevent reliable retrospective attribution |

Completed sessions have finish timestamp, duration, rating and progress. Active sessions lack finished outcome fields and are excluded from outcome evidence. API history lists completed sessions separately from active state. Immutable start snapshots preserve historical attributes even if the library changes.

## 5. Candidate signal inventory

| Signal | Classification | Research use |
| --- | --- | --- |
| Enjoyment rating | Direct recorded outcome, with ordinal/default caveats | Primary experimental input |
| Completed-session count and age | Reliable derived evidence quantity/age | Confidence and decay, never raw popularity points |
| Rating mean, distribution, trend | Computable descriptive statistics | Mean/age models tested; variance only diagnostic |
| Energy/experience from context | Direct historical context | M5 conditional subgroup, not causal proof |
| Game-level history | Reliable grouping across goals | Each session counted once; shared game adjustment |
| Duration/budget ratio | Computable, ambiguous interpretation | Negative-control case N only |
| Progress or completion narrative | Free-text observation | Negative-control case O only; never parsed into outcome points |
| Session-attributed goal completion | Not reliably available | Rejected |
| Desire to continue / stopping reason / post-session energy | Not recorded | No invented proxy |
| Recommendation exposure/rejection and unplayed alternatives | Not sufficiently recorded | No inferred causal preference |

## 6. Signals rejected due to weak/ambiguous semantics

Short duration can mean a successful compact session, interruption or disappointment; long duration can mean delight, idle time or obligation. Available time is a budget, not a target. Goal estimated minutes describe a useful session, not completion of the entire objective. Neither ratio should become a quality score.

Free-text progress rewards progression unfairly if treated as universal success: a restful session can be enjoyable without measurable progress. No NLP or LLM inference was introduced. Current goal status/completed_at cannot prove which historical session completed the goal. Case O contains a fictional narrative, **not** a persisted completion flag.

Do not infer user preference from frequency alone, or infer recommendation success simply because the recommended game was played.

## 7. Evaluation criteria

We assessed responsiveness, sparse-history sensitivity, boundedness, deterministic ordering, aging, cold start, explicit preference protection, situational gates, recency interaction, near-tie boundaries, feedback loops, interpretability and implementation/data complexity. A plausible result is not a ground-truth label. No threshold was fitted to these scenarios.

## 8. Synthetic experiment design

Fixed clock: 2026-10-04T19:00:00Z. Default context: 60 minutes, low energy, solo, progression. A = **Sky Orchard**; B = **Ember Expedition**. Both have a fictional “Advance one chapter” goal, 30-minute estimate, low requirement, solo mode and progression tag unless specified.

Strong pair: A interest 5/priority 3/friction 0; B interest 3/priority 2/friction 0 (base scores 100 and 80 before recency). Close pair: both interest 4/priority 2; A friction 0, B friction 1 (86.25 and 84.25 before recency). Goals/game IDs are 1 and 2.

History dates are days before the fixed clock. Default histories use days 1, 2, … . The latest 20 completed, nonfuture sessions per game are selected deterministically by finish timestamp then session ID descending. Active rows do not count. Invalid ratings/naive timestamps are rejected by the experimental projection. Future completed rows are ignored, unlike production's defensive recency clamp; normal recorded fixtures contain none. This projection is not a new database schema.

| Case | Candidate variant and complete history construction |
| --- | --- |
| A | Strong pair; no history |
| B | Strong; A one rating 1, day 1 |
| C | Strong; A eight ratings 1, days 1–8 |
| D | Strong; B one rating 5, day 1 |
| E | Strong; B eight ratings 5, days 1–8 |
| F | Close; A ratings 5,1,5,1,5 on days 1–5; B five ratings 3 on same days |
| G | Close; A three ratings 5 on days 1–3 and ten ratings 1 on days 120–129; B none |
| H | Close; A three ratings 1 on days 1–3 and ten ratings 5 on days 120–129; B none |
| I | Close; A 100 ratings 4 on days 1–100 (latest 20 used); B two ratings 5 on days 1–2 |
| J | A interest 5, B interest 3; both priority 2/friction 0; A eight ratings 1, B eight ratings 5 on days 1–8 |
| K | Close; A three ratings 1, B three ratings 5 on days 1–3 |
| L | Close; empty history initially; 30 subsequent daily recommendation/play cycles |
| M | Strong; A twenty ratings 5 on days 0,0.5,…,9.5; B none |
| N | Close; A rating 4 day 1 with duration/budget 20/120; B rating 4 day 1 with 100/60 |
| O | Close; A four ratings 5 and “No measurable progress; relaxed”; B four ratings 1 and “Finished objective; disliked session” |
| P | Close; A three current-context ratings 1 days 1–3 plus ten high-energy/challenge ratings 5 days 4–13; B none |
| Q | A interest 5/priority 3, high energy/challenge, eight ratings 5; B usual close attributes |
| R | A interest 5/priority 3, estimate 120, eight ratings 5; B usual close attributes |
| S | Close; A one rating 1, B one rating 3, both day 1 |
| T | Close; A one rating 3, B one rating 5, both day 1 |

Tests additionally cover active/future/invalid rows, deterministic input permutations, shared game history across goals and capped very large histories.

## 9. Candidate models

Let z = (rating − 3)/2, yielding −1, −0.5, 0, 0.5, 1. Let a be a maximum adjustment magnitude and n the number of selected observations. This assumes equal spacing of ordinal ratings; it is an explicit heuristic.

| Model | Formula and application |
| --- | --- |
| M0 | Frozen scorer, adjustment zero |
| M1 | a × mean(z); latest-20 bounded mean with no age/confidence discount |
| M2 | a × mean(z) × n/(n+3) |
| M2cap | Alternative confidence: a × mean(z) × min(1,n/5) |
| M3exp | a × Σ(wz)/(Σw+3), w = 2^(−age_days/30) |
| M3linear | Same shrinkage, w = max(0,1−age_days/90) |
| M4tie | M3exp, withheld until three selected observations; reorder **only the original accepted 3-point near-tie band** |
| M5context | M3exp after retaining exact energy and desired-experience matches |

M5 is justified by P, where recent challenge enjoyment contradicts low-energy progression enjoyment. It does not match social mode or time and does not assert a complete contextual model. Selection of the latest 20 precedes its context filter.

Non-M4 experimental models reorder all suitable candidates by base + adjustment using the frozen deterministic secondary keys. They are research ordering keys, not an implemented replacement response contract. M4 preserves original scores, acceptance status and choice membership; its key only orders that existing band. Every model leaves unsuitable/excluded candidates unrecommended.

Window 20, prior 3, half-life 30 days, linear horizon 90 days, three-session minimum and amplitudes are **uncalibrated research heuristics**. No synthetic optimum is claimed.

## 10. Scenario results

Winners at a = 3:

| Case | Purpose | M0 | M1 | M2 | M2cap | M3exp | M3linear | M4tie | M5context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | No history: high interest/priority versus moderate | A | A | A | A | A | A | A | A |
| B | One bad session for the strong favorite | A | A | A | A | A | A | A | A |
| C | Eight bad recent sessions for the strong favorite | A | A | A | A | A | A | A | A |
| D | One excellent session for the moderate alternative | A | A | A | A | A | A | A | A |
| E | Eight excellent sessions for the moderate alternative | A | A | A | A | A | A | A | A |
| F | Mixed 5/1/5/1/5 versus consistently neutral | A | A | A | A | A | A | A | A |
| G | Old bad, recent good versus no history | B | B | B | B | A | A | A | A |
| H | Old good, recent bad versus no history | B | A | A | A | B | B | B | B |
| I | 100 mildly positive versus 2 excellent sessions | A | A | A | A | A | A | A | A |
| J | Strong interest conflict at equal goal priority | A | A | A | A | A | A | A | A |
| K | Near tie with three bad versus three excellent sessions | A | B | B | B | B | B | B | B |
| L | Initial state of 30 recommendation/play feedback cycles | A | A | A | A | A | A | A | A |
| M | Frequently played legitimate favorite | A | A | A | A | A | A | A | A |
| N | Duration anomalies: 20/120 versus 100/60; identical enjoyment | A | A | A | A | A | A | A | A |
| O | Enjoyable no-progress versus unenjoyable completed-goal narrative | A | A | A | A | A | A | A | A |
| P | Context confounding: challenge good, current progression bad | B | A | A | A | A | A | A | B |
| Q | Unsuitable favorite stays unsuitable despite perfect outcomes | B | B | B | B | B | B | B | B |
| R | Time-filtered favorite stays excluded despite perfect outcomes | B | B | B | B | B | B | B | B |
| S | One bad near-tie outcome with recency held equal | A | B | A | A | A | A | A | A |
| T | One excellent near-tie outcome with recency held equal | A | B | A | A | A | A | A | A |

Full numeric comparisons at a = 3 follow. Δ is enjoyment adjustment; key is base + Δ. Values are rounded to three decimals for presentation; code uses unrounded floats. Q/A is eligible but unsuitable (10 < 25); its zero adjustment/key cannot cause acceptance. R/A is excluded for insufficient time and therefore has no score. All other listed candidates are eligible and suitable. No social rule was changed; invariant tests cover explicit solo/social filtering and both abstention outcomes.

**M4 keys outside its original band are diagnostic only and cannot reorder a candidate into the band.** In strong pairs and J, only A belongs to the band; B's displayed signal is not applied to the winner decision. In Q only B belongs; in R only B survives.

| Case/game | Base | Suitability | M1 Δ → key | M2 Δ → key | M2cap Δ → key | M3exp Δ → key | M3linear Δ → key | M4tie Δ → key | M5context Δ → key |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A/A | 100.000 | 60 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 |
| A/B | 80.000 | 60 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 |
| B/A | 97.429 | 60 | -3.000 → 94.429 | -0.750 → 96.679 | -0.600 → 96.829 | -0.737 → 96.691 | -0.744 → 96.685 | 0.000 → 97.429 | -0.737 → 96.691 |
| B/B | 80.000 | 60 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 |
| C/A | 97.429 | 60 | -3.000 → 94.429 | -2.182 → 95.247 | -3.000 → 94.429 | -2.119 → 95.309 | -2.151 → 95.278 | -2.119 → 95.309 | -2.119 → 95.309 |
| C/B | 80.000 | 60 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 |
| D/A | 100.000 | 60 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 |
| D/B | 77.429 | 60 | 3.000 → 80.429 | 0.750 → 78.179 | 0.600 → 78.029 | 0.737 → 78.166 | 0.744 → 78.172 | 0.000 → 77.429 | 0.737 → 78.166 |
| E/A | 100.000 | 60 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 | 0.000 → 100.000 |
| E/B | 77.429 | 60 | 3.000 → 80.429 | 2.182 → 79.610 | 3.000 → 80.429 | 2.119 → 79.548 | 2.151 → 79.580 | 2.119 → 79.548 | 2.119 → 79.548 |
| F/A | 83.679 | 60 | 0.600 → 84.279 | 0.375 → 84.054 | 0.600 → 84.279 | 0.366 → 84.044 | 0.370 → 84.049 | 0.366 → 84.044 | 0.366 → 84.044 |
| F/B | 81.679 | 60 | 0.000 → 81.679 | 0.000 → 81.679 | 0.000 → 81.679 | 0.000 → 81.679 | 0.000 → 81.679 | 0.000 → 81.679 | 0.000 → 81.679 |
| G/A | 83.679 | 60 | -1.615 → 82.063 | -1.313 → 82.366 | -1.615 → 82.063 | 1.073 → 84.752 | 1.483 → 85.162 | 1.073 → 84.752 | 1.073 → 84.752 |
| G/B | 84.250 | 60 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 |
| H/A | 83.679 | 60 | 1.615 → 85.294 | 1.313 → 84.991 | 1.615 → 85.294 | -1.073 → 82.605 | -1.483 → 82.195 | -1.073 → 82.605 | -1.073 → 82.605 |
| H/B | 84.250 | 60 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 |
| I/A | 83.679 | 60 | 1.500 → 85.179 | 1.304 → 84.983 | 1.500 → 85.179 | 1.261 → 84.940 | 1.282 → 84.961 | 1.261 → 84.940 | 1.261 → 84.940 |
| I/B | 81.679 | 60 | 3.000 → 84.679 | 1.200 → 82.879 | 1.200 → 82.879 | 1.175 → 82.854 | 1.188 → 82.866 | 0.000 → 81.679 | 1.175 → 82.854 |
| J/A | 89.929 | 60 | -3.000 → 86.929 | -2.182 → 87.747 | -3.000 → 86.929 | -2.119 → 87.809 | -2.151 → 87.778 | -2.119 → 87.809 | -2.119 → 87.809 |
| J/B | 77.429 | 60 | 3.000 → 80.429 | 2.182 → 79.610 | 3.000 → 80.429 | 2.119 → 79.548 | 2.151 → 79.580 | 2.119 → 79.548 | 2.119 → 79.548 |
| K/A | 83.679 | 60 | -3.000 → 80.679 | -1.500 → 82.179 | -1.800 → 81.879 | -1.465 → 82.213 | -1.483 → 82.195 | -1.465 → 82.213 | -1.465 → 82.213 |
| K/B | 81.679 | 60 | 3.000 → 84.679 | 1.500 → 83.179 | 1.800 → 83.479 | 1.465 → 83.144 | 1.483 → 83.162 | 1.465 → 83.144 | 1.465 → 83.144 |
| L/A | 86.250 | 60 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 |
| L/B | 84.250 | 60 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 |
| M/A | 97.000 | 60 | 3.000 → 100.000 | 2.609 → 99.609 | 3.000 → 100.000 | 2.571 → 99.571 | 2.590 → 99.590 | 2.571 → 99.571 | 2.571 → 99.571 |
| M/B | 80.000 | 60 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 | 0.000 → 80.000 |
| N/A | 83.679 | 60 | 1.500 → 85.179 | 0.375 → 84.054 | 0.300 → 83.979 | 0.369 → 84.047 | 0.372 → 84.050 | 0.000 → 83.679 | 0.369 → 84.047 |
| N/B | 81.679 | 60 | 1.500 → 83.179 | 0.375 → 82.054 | 0.300 → 81.979 | 0.369 → 82.047 | 0.372 → 82.050 | 0.000 → 81.679 | 0.369 → 82.047 |
| O/A | 83.679 | 60 | 3.000 → 86.679 | 1.714 → 85.393 | 2.400 → 86.079 | 1.672 → 85.351 | 1.694 → 85.372 | 1.672 → 85.351 | 1.672 → 85.351 |
| O/B | 81.679 | 60 | -3.000 → 78.679 | -1.714 → 79.964 | -2.400 → 79.279 | -1.672 → 80.007 | -1.694 → 79.985 | -1.672 → 80.007 | -1.672 → 80.007 |
| P/A | 83.679 | 60 | 1.615 → 85.294 | 1.313 → 84.991 | 1.615 → 85.294 | 1.143 → 84.821 | 1.225 → 84.904 | 1.143 → 84.821 | -1.465 → 82.213 |
| P/B | 84.250 | 60 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 | 0.000 → 84.250 |
| Q/A | 47.429 | 10 | 0.000 → 47.429 | 0.000 → 47.429 | 0.000 → 47.429 | 0.000 → 47.429 | 0.000 → 47.429 | 0.000 → 47.429 | 0.000 → 47.429 |
| Q/B | 86.250 | 60 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 |
| R/B | 86.250 | 60 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 | 0.000 → 86.250 |
| S/A | 83.679 | 60 | -3.000 → 80.679 | -0.750 → 82.929 | -0.600 → 83.079 | -0.737 → 82.941 | -0.744 → 82.935 | 0.000 → 83.679 | -0.737 → 82.941 |
| S/B | 81.679 | 60 | 0.000 → 81.679 | 0.000 → 81.679 | 0.000 → 81.679 | 0.000 → 81.679 | 0.000 → 81.679 | 0.000 → 81.679 | 0.000 → 81.679 |
| T/A | 83.679 | 60 | 0.000 → 83.679 | 0.000 → 83.679 | 0.000 → 83.679 | 0.000 → 83.679 | 0.000 → 83.679 | 0.000 → 83.679 | 0.000 → 83.679 |
| T/B | 81.679 | 60 | 3.000 → 84.679 | 0.750 → 82.429 | 0.600 → 82.279 | 0.737 → 82.416 | 0.744 → 82.422 | 0.000 → 81.679 | 0.737 → 82.416 |

Observations:
- A–E preserve the strong favorite at ±3; one session does not erase the 20-point preference gap. C also shows that repeated dislike is not necessarily an instruction to override explicitly high interest.
- F retains A despite inconsistent outcomes. Means conceal variability; no tested model has an explicit variance term.
- G: age weighting identifies recent improvement while lifetime-like latest-20 means still penalize A. H reverses this: unaged means reward A despite recent bad sessions.
- I: history count is confidence, not a popularity bonus. Only 20 of 100 A records are used, and the sparse alternative has two records.
- J: large adjustments can override a two-step interest difference; M4 cannot because B is outside the accepted band.
- K: outcomes resolve the close choice for B; this is the strongest favorable near-tie example.
- L: a static cold start looks harmless, but repeated cycles reveal a different behavior (section 15).
- M: a frequently played favorite with strong outcomes continues winning. Frequency alone is not evidence of pathology.
- N: different duration ratios produce the same enjoyment adjustment. O likewise uses rating, not progress text or alleged completion.
- P: pooled-history models, including M4, favor A because enjoyable high-energy challenge sessions mask bad current-context sessions. M5 favors B. This counterexample challenges relevance, not arithmetic correctness.
- Q/R: excellent outcomes never bypass situational suitability or hard time filtering.
- S/T: M1 flips a close choice after one session; confidence models and M4 do not at ±3.

## 11. Scoring-magnitude analysis

We evaluated ±1, ±2, ±3, ±5, ±8 and ±10 for every model and scenario. These are per-candidate bounds; opposite-sign evidence can create a relative swing up to twice the bound (less with shrinkage). ±3 is already the entire accepted near-tie margin and the maximum recency penalty. ±5 can outweigh two friction steps. ±8/±10 can compete with an interest or priority step and alter explicit preference decisions.

Selected discriminating sweep results (A/B = winner):

| Case/model | ±1 | ±2 | ±3 | ±5 | ±8 | ±10 |
| --- | --- | --- | --- | --- | --- | --- |
| G/M1 | B | B | B | B | B | B |
| G/M2 | B | B | B | B | B | B |
| G/M3exp | B | A | A | A | A | A |
| G/M4tie | B | A | A | A | A | A |
| G/M5context | B | A | A | A | A | A |
| H/M1 | B | A | A | A | A | A |
| H/M2 | B | A | A | A | A | A |
| H/M3exp | B | B | B | B | B | B |
| H/M4tie | B | B | B | B | B | B |
| H/M5context | B | B | B | B | B | B |
| J/M1 | A | A | A | A | B | B |
| J/M2 | A | A | A | A | A | B |
| J/M3exp | A | A | A | A | A | B |
| J/M4tie | A | A | A | A | A | A |
| J/M5context | A | A | A | A | A | B |
| K/M1 | A | B | B | B | B | B |
| K/M2 | A | A | B | B | B | B |
| K/M3exp | A | A | B | B | B | B |
| K/M4tie | A | A | B | B | B | B |
| K/M5context | A | A | B | B | B | B |
| P/M1 | B | A | A | A | A | A |
| P/M2 | B | A | A | A | A | A |
| P/M3exp | B | A | A | A | A | A |
| P/M4tie | B | A | A | A | A | A |
| P/M5context | B | B | B | B | B | B |
| S/M1 | A | A | B | B | B | B |
| S/M2 | A | A | A | A | A | B |
| S/M3exp | A | A | A | A | A | B |
| S/M4tie | A | A | A | A | A | A |
| S/M5context | A | A | A | A | A | B |
| T/M1 | A | A | B | B | B | B |
| T/M2 | A | A | A | A | A | B |
| T/M3exp | A | A | A | A | A | B |
| T/M4tie | A | A | A | A | A | A |
| T/M5context | A | A | A | A | A | B |

The complete sweep is reproducible with `python -m experiments.outcome_017` from backend. No tested amplitude eliminates M4's loop problem. Large amplitudes are especially difficult to justify; smaller ones limit influence but do not establish relevance or fairness to unobserved alternatives.

Asymmetric influence uses a unit signal multiplied by +3/−1, +1/−3 or +3/−3:

| Case/model | +3 / −1 | +1 / −3 | +3 / −3 |
| --- | --- | --- | --- |
| G/M3exp | A | B | A |
| G/M4tie | A | B | A |
| H/M3exp | B | B | B |
| H/M4tie | B | B | B |
| K/M3exp | A | A | B |
| K/M4tie | A | A | B |
| P/M3exp | A | B | A |
| P/M4tie | A | B | A |

More negative influence avoids P's positive pooled-history boost but also suppresses G's legitimate recent improvement. Either asymmetry prevents K's flip at these settings because the combined swing is slightly below its two-point gap. There is no empirical basis to prefer symmetric, positive-heavy or negative-heavy influence from these fixtures.

## 12. Sparse-history/confidence analysis

M1 gives a fresh single rating 5 the full +a (or rating 1 −a). M2 gives ±a/4. M2cap gives ±a/5. M3exp gives at most ±a/4 and less as the record ages. M4 gives zero before three sessions. At a = 3 these fresh single-session effects are 3, 0.75, 0.6, at most 0.75 and 0 respectively.

M2 confidence for n = 0,1,2,3,5,20 is 0,0.25,0.40,0.50,0.625,0.870. The cap prevents 500 records from creating greater evidence than the latest 20. Age weighting reduces effective evidence further. These denominators are shrinkage controls, **not calibrated probabilities**.

F has mean 3.4 despite ratings ranging 1–5. A mean alone cannot explain this instability. Age models can respond to order, but still lack an explicit variability or uncertainty account. More schema fields are not necessary to calculate distributions; interpreting them is a separate policy decision.

M4's minimum count protects against single-session noise yet disadvantages the alternative that gets played once and then stops receiving observations. A minimum-data gate can itself reinforce data starvation.

## 13. Cold-start analysis

No history contributes zero, reproducing V0.1. A new game is not directly penalized for having no ratings. However, a familiar game can receive positive evidence while a new game remains neutral; this creates a **relative** cold-start disadvantage. Neutral is not guaranteed equal exposure.

B in G/H/P is a deliberate no-history alternative; S/T isolate one-record sensitivity with recency equal. There is no evidence that an automatic exploration quota suits a personal preference tool. Do not secretly lower favorites to manufacture exposure.

## 14. Existing recency interaction

Production recency uses the **most recent completed session per game**, not rating, count, active start, recommendation frequency or streak. Let d = max(0, UTC elapsed seconds / 86400) since its finish. Contribution is −3 × max(0,1−d/7); never played or at least seven days old contributes zero. A future timestamp defensively clamps to just played. Active sessions do not count.

This is a mild spacing/novelty nudge, not dislike inference. Outcome decay instead asks whether a rating is still relevant, and confidence asks how much evidence exists. They have different meanings but share completed-session timestamps. Recent good evidence can cancel spacing; recent bad evidence can compound it. The effective combined pressure matters even though these are not literally duplicate quality factors.

Our fixtures recompute the frozen recency input from synthetic completed histories; one-day recency is −18/7. This explains why no-history B can beat A before any outcome adjustment in G/H/P. The loops demonstrate how positive evidence overwhelms the intended spacing pressure. Neither ratings nor session counts should replace recency without a separate policy review.

## 15. Feedback-loop analysis

Thirty daily cycles start with the close pair and no history. Recommend the highest experimental key, play that winner, record its completion at that cycle's time, then recompute history and frozen recency. No random exploration or forced alternation. Both games would yield rating 5 whenever played. This is a deliberately controlled hypothetical, not measured owner behavior.

Cells show A/B selection counts (longest consecutive streak):

| Model | ±1 | ±2 | ±3 | ±5 | ±8 | ±10 |
| --- | --- | --- | --- | --- | --- | --- |
| M0 | 25/5 (5) | 25/5 (5) | 25/5 (5) | 25/5 (5) | 25/5 (5) | 25/5 (5) |
| M1 | 30/0 (30) | 30/0 (30) | 30/0 (30) | 30/0 (30) | 30/0 (30) | 30/0 (30) |
| M2 | 25/5 (6) | 29/1 (28) | 30/0 (30) | 30/0 (30) | 30/0 (30) | 30/0 (30) |
| M2cap | 29/1 (28) | 29/1 (28) | 30/0 (30) | 30/0 (30) | 30/0 (30) | 30/0 (30) |
| M3exp | 25/5 (6) | 29/1 (28) | 30/0 (30) | 30/0 (30) | 30/0 (30) | 30/0 (30) |
| M3linear | 25/5 (6) | 29/1 (28) | 30/0 (30) | 30/0 (30) | 30/0 (30) | 30/0 (30) |
| M4tie | 29/1 (28) | 29/1 (28) | 29/1 (28) | 29/1 (28) | 29/1 (28) | 29/1 (28) |
| M5context | 25/5 (6) | 29/1 (28) | 30/0 (30) | 30/0 (30) | 30/0 (30) | 30/0 (30) |

Control yields 25/5 with longest streak 5. At ±3, unbanded confidence/age models lock onto A for all 30 cycles. M1 locks in even at ±1. **M4 yields 29/1 and a 28-session streak at every tested amplitude**: its minimum-data rule suppresses B's one good observation while A accumulates usable evidence.

A second simulation sets hypothetical enjoyment to A = 4 and B = 5, at a = 3:

| Model | A / B | Longest streak |
| --- | --- | --- |
| M0 | 25 / 5 | 5 |
| M1 | 30 / 0 | 30 |
| M2 | 25 / 5 | 6 |
| M2cap | 29 / 1 | 28 |
| M3exp | 25 / 5 | 6 |
| M3linear | 25 / 5 | 6 |
| M4tie | 29 / 1 | 28 |
| M5context | 25 / 5 | 6 |

M4 still gives B only one play despite B's better hypothetical outcomes. These latent inputs expose information starvation; they do not supply validated real-world labels or an accuracy metric. M3exp's 25/5 distribution here is preferable to M4's lock-in, but cannot establish globally superior recommendations.

Contrast M, where explicit interest/priority already favor A and repeated enjoyment remains excellent. Continuing to recommend A is consistent with expressed preference; it should not be penalized merely for popularity. Pathology here is the **algorithm's self-created loss of observations among otherwise close choices**, not every repeated recommendation.

## 16. Explainability analysis

Possible future language, with evidence shown alongside it:
- Three good recent matching sessions: “Your recent sessions with this game have gone well.”
- Several bad recent sessions: “Several recent sessions with this game were rated poorly.”
- One session: “There is little session history, so it has only a small influence.” For M4: “There is not enough history to affect the close decision.”
- K under M4: “These games were otherwise close, and your recent sessions favored Ember Expedition.”
- P: “Most favorable ratings came from challenge sessions; they may not describe tonight's progression session.”

An inspectable future breakdown would show original score, outcome delta, final ordering key, selected/weighted counts, age window, context coverage and whether the signal actually applied. For K, M3exp/M4 adjustments are approximately −1.465/+1.465; original scores 83.679/81.679 become ordering keys 82.214/83.143. M4 must still show original scores and original band membership rather than mislabel keys as production scores.

Avoid “you will enjoy this,” confidence percentages, inferred goal success or claims that a neutral/default rating proves indifference. No UI was implemented.

## 17. Rejected approaches

Reject unrestricted mean influence (single-session overreaction); raw frequency bonuses (exposure feedback); full confidence after five records without aging (old evidence and loops); duration/progress/goal-success proxies (semantic gaps); automatic exploration quotas or favorite penalties (unsupported product policy); and unbounded history influence (overrides explicit intent).

M4 is rejected as a presumed loop solution, not as a mathematically invalid band guard. It succeeds at preserving large preference gaps but fails its important falsification tests. M5 is a useful context counterexample response, not a complete contextual recommender.

## 18. Recommended approach, if any

Do not adopt any ranking adjustment yet. M3exp with small influence (±1 as a research setting, not a production choice) is the strongest general candidate for another investigation: transparent shrinkage, gradual aging, bounded points and fewer loop problems than M4 in these simulations. M5 demonstrates that context relevance must also be assessed before adoption.

The safest next product direction is **descriptive outcome evidence without changing ranking**. That proposal is not a tested scoring model or an implemented feature. It lets the owner inspect whether recorded ratings mean what the policy assumes.

## 19. Known weaknesses of the recommended approach

M3exp still favors the wrong contextual history in P, changes close decisions without preference-specific authorization, has arbitrary window/half-life/prior/magnitude and fails the equal-enjoyment loop at ±2 and above. ±1 still lengthens the control's streak. Ratings are ordinal, potentially defaulted, self-selected and affected by context or the particular goal. Game-level aggregation can conflate goals; goal-level aggregation would be sparser.

M5 matches only two context dimensions, can discard older relevant history because the global cap comes first, and makes cold-start uncertainty worse. Descriptive summaries can still mislead unless counts, context and limitations accompany them.

Human judgment is required on whether history should ever outrank explicit interest, whether default 3 is meaningful evidence, whether negative ratings are stronger instructions than positive ones, what contexts are comparable, and whether close choices should be reordered or simply accompanied by advice. The near-tie margin is a discontinuous boundary: membership changes as base scores/recency cross three points, even if enjoyment history is unchanged.

## 20. Whether production scoring should change

**No.** V0.1 remains the production policy. Synthetic examples establish deterministic behavior and counterexamples, not recommendation benefit. No suitability, near-tie, preference, friction, recency or duration rule was tuned.

## 21. Smallest proposed future implementation milestone, if justified

Subject to separate review, design a read-only per-game outcome summary: completed count, rating distribution, dates and matching-context coverage, with explicit sparse/default-rating caveats. Keep recommendation scores and ordering unchanged. First settle rating semantics and review the summary contract; avoid schema changes unless that review proves necessary. Then evaluate on owner-reviewed examples before considering a separate scoring experiment.

This milestone was **not started**. It would not require an LLM, account system or new infrastructure.

## 22. Test/verification evidence

| Check | Before investigation | After isolated experiment |
| --- | --- | --- |
| Complete backend pytest invocation | 559 passed, 50 skipped | **635 passed, 50 skipped** (27.76s) |
| Focused experimental tests | Not present | **76 passed** (0.49s) |
| Complete frontend suite | 51 passed | **51 passed** (12.16s) |
| Production frontend build | Existing baseline retained | Passed, Vite 8.3.2; 26 modules |
| Frozen scorer SHA-256 | Expected frozen hash | Exact match |
| Reports 001–016 checksums | Captured before investigation | Exact matches |
| Whitespace/diff inspection | Existing unrelated owner/editor changes recorded | git diff --check passed; no production code changes |

The 50 backend skips comprise 48 opt-in PostgreSQL integration/maintenance cases and two existing SQLite/dialect skips. No PostgreSQL service, restore or provider operation was run. This is a complete suite invocation with explicit coverage limits, **not** a claim that those 50 tests passed.

Tests cover control equivalence, deterministic permutations and tie behavior, bounded/neutral signals, eligibility/suitability/abstention invariants, confidence/aging, capped history, active/future/invalid records, shared game evidence, proxy rejection, contextual and loop counterexamples, asymmetric bounds, scorer integrity and absence of production imports of the experiment. Existing tests were not weakened.

Reproduction from backend: `python -m experiments.outcome_017` (fictional fixed-clock JSON); `python -m pytest tests/test_outcome_017.py`; `python -m pytest`. Frontend: `npm test -- --run`, `npm run build`. Test execution used isolated local SQLite configuration and did not read provider data.

## 23. Files changed

- `backend/experiments/outcome_017.py`: resumed existing interrupted scaffold; narrow correctness repairs, confidence alternatives, contextual counterexample and simulations.
- `backend/tests/test_outcome_017.py`: 76 independent experimental/invariant tests.
- `reports/017_session_outcome_signal_investigation.md`: this historical investigation.
- `reports/README.md`: new index entry.

The owner had committed the initial experiment scaffold before continuation. Existing .gitignore and Visual Studio working-tree changes were preserved. No production application, API, schema, frontend or deployment file was modified. No cloud access, secrets, personal data, backup/restore, deployment or follow-up implementation occurred.

## 24. Explicit frozen-policy confirmation

`backend/app/scoring.py` was not modified. Production remains `v0.1-final-004`. Reports 001–016 remain unchanged; this report does not rewrite deployment acceptance history.

## 25. Frozen scorer hash verification

Verified SHA-256:

```text
b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a
```

This matches the required frozen hash and the investigation's before/after checksum comparison.

