# 002: Recommendation scoring policy comparison

Date: 2026-10-03 (America/Los_Angeles). Milestone: 1 policy investigation. Status: complete; proposal not adopted.

Baseline reference: [Experiment 001](001_milestone_1_engine_evaluation.md). That report, its 13 fixtures, and the v0.1 engine are unchanged. No database, API, or frontend work was performed.

## 1. Questions and hypotheses

- Would stronger energy influence stop unrelated preferences casually overwhelming low energy without making demanding games categorically impossible?
- Would plateau time scoring reduce estimate noise while modestly preferring room for overruns?
- Would a weaker recency nudge preserve a recently played favorite without inventing continuation intent?
- Would removing constant social points simplify ranking without losing ranking information?
- Would a near-tie set communicate equivalent choices without random ordering?
- Would explicit suitability/total gates distinguish bad fits from infeasible choices?
- Are these changes consistent across conflicts, rather than merely different from baseline?

## 2. Baseline policy summary

Baseline v0.1 uses hard time/social/lifecycle filters, then additive interest 25, priority 15, linear time 15, energy 15, constant social 10, binary experience 20, friction penalty up to 10, and seven-day recency penalty up to 10. It always selects the highest-scoring eligible candidate, even if negative. Ordering is raw score descending, priority descending, goal ID ascending, then game ID ascending. Exact filters and full formulas are preserved in report 001.

## 3. Proposed policy and conceptual model

Experimental code lives only in `backend/experiments/policy_002.py`; no import from the baseline engine selects it. It reuses validated baseline domain objects and calls baseline recommend solely to preserve hard eligibility/validation, then computes independent experimental factors. This incurs redundant baseline scoring in the research harness, a deliberate small-code compromise rather than new production architecture.

Eligibility remains unchanged: can I do it? Every eligible candidate is then scored, including candidates that will fail suitability. Situational suitability is explicitly the sum of energy, experience, and time points. Preference is interest plus goal priority. Friction and recency are additive costs. A recommendation must pass both suitability and total thresholds; among passing candidates, total score decides order. These are a few fields/conditions, not separate services or layers.

This is not a strict lexicographic suitability-before-preference ranking: suitability is a minimum gate, and preference can still overcome fit differences above the gate. The total gate also means preference and costs influence acceptance. Explicit suitability reasons make this tradeoff inspectable, but calling it suitable does not imply clinical or empirically calibrated fitness.

## 4. Proposed weights, formulas, and thresholds

| Term | Maximum / setting | Formula or rule | Rationale |
| --- | --- | --- | --- |
| interest | +25 | 25 * (interest - 1) / 4 | Preserve actual preference information |
| goal_priority | +15 | 15 * (priority - 1) / 2 | Preserve goal importance |
| energy_fit | +30 | sufficient: 30; one level short: 15; two short: 0 | Double energy influence; demanding favorites can still pass when experience fits |
| time_fit | +10 | estimated <= 90% available: 10; otherwise eligible: 8 | Plateau reduces precision sensitivity; 2-point soft buffer deduction |
| experience_fit | +20 | matching tag: 20; otherwise 0 | Retain direct requested experience influence |
| social_fit | removed | Social remains eligibility only | Constant points convey no ranking information |
| friction | up to -10 | -10 * friction / 5 | Preserve known tradeoff for controlled comparison |
| recent_play | up to -3 | -3 * max(0, 1 - elapsed_days / 7); never: 0 | Smaller variety nudge; do not infer continuation from recency |
| minimum_suitability | 25 inclusive | time + energy + experience >= 25 | Prevent preference rescuing extremely poor situational fit |
| minimum_total | 50 inclusive | sum of every factor >= 50 | Permit explicit no-good-fit result despite eligibility |
| near_tie_margin | 3 inclusive | qualifying score within 3 of the best qualifying score | Present similar choices without implying tiny differences are meaningful |

Positive maxima remain 100, but components and scale changed: cross-policy absolute scores are not quality comparisons. Raw values are not rounded or clamped. Buffer is 10% of time (3 minutes in a 30-minute window, 12 in a two-hour window), not inferred setup minutes or guaranteed slack. Friction does not consume time. Constants are centralized in the frozen experimental Policy object; no override interface or persistence was added.

Elapsed days and time validation follow the baseline semantics. Neither enjoyment nor continuation intention exists in the input. We do not add a continuation bonus or assume that recent play means wanting to continue.

Outcomes:

- `no_eligible`: no candidate passes hard filters.
- `no_good_fit`: eligible scored candidates exist, but none pass both gates.
- `clear_recommendation`: exactly one qualifying candidate is within 3 points of the best qualifying score.
- `multiple_equivalent`: two or more qualify and are within 3 points of that best score.

Raw score/priority/ID ordering is retained within the group. First display choice is not a sole winner when status is multiple_equivalent. Near-tie membership is anchored to the best, not chained pairwise; a sequence of small gaps cannot bring a distant candidate into the group. Nonqualifying candidates are never included in the group, even if numerically close.

## 5. Method, reproducibility, and tests

Exactly the same immutable 13 fixtures and evaluation clock from report 001 are imported, not copied or edited. Six additional discriminating fixtures are in `backend/experiments/comparison_002.py`. Reference time: 2026-10-03T19:00:00+00:00. Candidate IDs are local to each scenario. All games are active and all goals active.

For all 19 scenarios, both policies receive the same candidate objects, context, and clock; exclusions match exactly. Proposed output equals a repeat run and a reversed-input run. Breakdown sums equal totals. These assertions are also exercised by experimental pytest coverage. Cases were designed to expose tradeoffs; this is synthetic policy inspection, not a blind benchmark or a measurement of enjoyment.

Python 3.12.6; pytest 8.4.2. Commands run from backend:

` .venv/Scripts/python.exe -m pytest tests/test_scoring.py -q `

```text
..................................................................       [100%]
66 passed in 0.07s
```

` .venv/Scripts/python.exe -m pytest tests/test_policy_002.py -q `

```text
.........................                                                [100%]
25 passed in 0.05s
```

Total: **91 passed (66 unchanged baseline + 25 experimental)**. Experimental tests cover energy reversal/escape, plateau/buffer boundaries, recency decay, all four outcomes, gate boundaries, near-tie inclusivity anchored to the best, exclusion parity, arithmetic, and order independence.

Replay without writing a report: `.venv/Scripts/python.exe -m experiments.comparison_002` (JSON with inputs, factors, and both results). Replaying after code changes is a new investigation; preserve this report and create the next number.

Provenance SHA-256:

- `backend/app/scoring.py`: `e0bee04c7f81a53b1881a8777d689bd08bb337155fdf4675702af4fc4d7e87fe` (verified unchanged before and after evaluation).
- `reports/001_milestone_1_engine_evaluation.md`: `321498eabc0741db9eac22988981bbc3e7ec948035369c732f0c1777b7b299bb` (verified unchanged before and after evaluation).
- `backend/examples/evaluation_001.py`: `b6a3b4635a643a0fc7428901dd0084e3ffc072edf82a007530d8e25ae5015ab7` (verified unchanged before and after evaluation).
- `backend/experiments/policy_002.py`: `9e50f8e33c69cddc852e06229cc22291ca0c7329c40c1ecc586676ccfe3c28a4`.
- `backend/experiments/comparison_002.py`: `01a3bd05472851578c6290614d8a2ef9f3299b65b97b6f81949a810fa87d5b3e`.
- `backend/tests/test_policy_002.py`: `dc1d9e94f25eda7f2ed085944cca0cb1ed02c43c0152c378b0798ba5c15db227`.

## 6. Compact comparison

Changed includes a different sole result, near-tie classification, or abstention; it does not mean improved quality. Baseline always offers a single winner when eligible.

| Scenario | Baseline | Proposed | Changed |
| --- | --- | --- | --- |
| 1. Low energy + short session + progression | Iron Summit | Moonlit Orchard (clear_recommendation) | Yes |
| 2. High energy + long session + challenge | Iron Summit | Iron Summit; Clockwork Duel (multiple_equivalent) | Yes |
| 3. Strong interest in a poor situational fit | Quiet Cartographer | Quiet Cartographer (clear_recommendation) | No |
| 4. Lower interest with a perfect situational fit | Moonlit Orchard | Moonlit Orchard (clear_recommendation) | No |
| 5. Two nearly identical candidates | Forest Foundry | Harbor Builder; Forest Foundry (multiple_equivalent) | Yes |
| 6. Recently played favorite versus less-recent alternative | Quiet Cartographer | Moonlit Orchard (clear_recommendation) | Yes |
| 7. High-friction favorite versus low-friction alternative | Harbor Builder | Harbor Builder (clear_recommendation) | No |
| 8. Candidate excluded by available time | Clockwork Duel | Clockwork Duel (clear_recommendation) | No |
| 9. Candidate excluded by solo/social requirements | Starship Crew | Starship Crew; Trail Partners (multiple_equivalent) | Yes |
| 10. Multiple conflicting factors | Quiet Cartographer | Quiet Cartographer (clear_recommendation) | No |
| 11. Supplement: exact tie and stable order | Moonlit Orchard | Moonlit Orchard; Quiet Cartographer (multiple_equivalent) | Yes |
| 12. Supplement: negative-score eligible candidate | Iron Summit | no_good_fit | Yes |
| 13. Supplement: no eligible candidate | No eligible candidate | no_eligible | No |
| 14. Energy mismatch favorite still possible | Iron Summit | Iron Summit (clear_recommendation) | No |
| 15. Time buffer band boundary | Forest Foundry | Harbor Builder; Forest Foundry (multiple_equivalent) | Yes |
| 16. Very short goal in a long window | Quiet Cartographer | Moonlit Orchard; Quiet Cartographer (multiple_equivalent) | Yes |
| 17. Recent-play ordering with equal interest | Quiet Cartographer | Quiet Cartographer; Moonlit Orchard (multiple_equivalent) | Yes |
| 18. Total threshold across priority step | Quiet Cartographer | Quiet Cartographer (clear_recommendation) | No |
| 19. Suitability gate rejects a high-total mismatch | Iron Summit | no_good_fit | Yes |

## 7. Full side-by-side results for the 13 baseline scenarios

All factor tables retain raw floating-point output. Proposed social column is a dash because the factor was removed, not a hidden deduction. Suitability is a subtotal, not an additional contribution. Every other listed factor sums to Total. Inputs list elapsed days since last completed play (never means null). Game ID = goal ID; lifecycle defaults are active. Excluded candidates receive no score in either policy.

### 1. Low energy + short session + progression

Situation: available_minutes=20; energy=low; social_preference=solo; desired_experience=progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Upgrade the watering can | 15 | low | solo | chill, progression | 4 | 2 | 1 | 7.0 |
| 2 | Iron Summit / Clear the training arena | 20 | high | solo | challenge, progression | 5 | 3 | 1 | 7.0 |

Eligibility: ID 2 eligible. ID 1 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 2 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 20 | -2.0 | 0 | 83.0 | - | No gate |
| Baseline | 1 | 18.75 | 7.5 | 11.25 | 15.0 | 10 | 20 | -2.0 | 0 | 80.5 | - | No gate |
| Proposed | 1 | 18.75 | 7.5 | 10 | 30 | - | 20 | -2.0 | 0 | 84.25 | 60 | Yes |
| Proposed | 2 | 25.0 | 15.0 | 8.0 | 0 | - | 20 | -2.0 | 0 | 66.0 | 28.0 | Yes |

Baseline winner: Iron Summit.
Proposed result: **clear_recommendation**; choices in display order: Moonlit Orchard.

Changed: Yes. The suitable orchard replaces the demanding favorite as sole choice.

Why: Energy doubles its maximum difference from 15 to 30 points and the time rule stops rewarding a full-window estimate over a comfortable one. Orchard 84.25 versus Summit 66 gives an 18.25-point lead.

Intentional behavior / concern: Intentional stronger situational influence. The favorite remains suitable; this is a ranking reversal, not an energy exclusion.

### 2. High energy + long session + challenge

Situation: available_minutes=120; energy=high; social_preference=solo; desired_experience=challenge.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Conquer the summit boss | 120 | high | solo | challenge | 5 | 3 | 2 | 7.0 |
| 2 | Clockwork Duel / Complete a ranked ladder run | 60 | medium | solo | challenge | 4 | 3 | 0 | 7.0 |
| 3 | Moonlit Orchard / Expand the orchard | 90 | low | solo | chill, progression | 5 | 3 | 0 | 7.0 |

Eligibility: ID 1 eligible. ID 2 eligible. ID 3 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 1 | 25.0 | 15.0 | 15.0 | 15.0 | 10 | 20 | -4.0 | 0 | 96.0 | - | No gate |
| Baseline | 2 | 18.75 | 15.0 | 7.5 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | No gate |
| Baseline | 3 | 25.0 | 15.0 | 11.25 | 15.0 | 10 | 0 | 0.0 | 0 | 76.25 | - | No gate |
| Proposed | 1 | 25.0 | 15.0 | 8.0 | 30 | - | 20 | -4.0 | 0 | 94.0 | 58.0 | Yes |
| Proposed | 2 | 18.75 | 15.0 | 10 | 30 | - | 20 | 0.0 | 0 | 93.75 | 60 | Yes |
| Proposed | 3 | 25.0 | 15.0 | 10 | 30 | - | 0 | 0.0 | 0 | 80.0 | 40 | Yes |

Baseline winner: Iron Summit.
Proposed result: **multiple_equivalent**; choices in display order: Iron Summit, Clockwork Duel.

Changed: Yes in classification; first display choice unchanged.

Why: Summit 94 and Duel 93.75 are within 3 points. Duel gains full plateau time credit while Summit gets 8 time points; the favorite remains first by 0.25.

Intentional behavior / concern: Intentional near equivalence; potentially surprising if the user specifically wanted a long boss encounter. Neither policy knows desired engagement length beyond available time.

### 3. Strong interest in a poor situational fit

Situation: available_minutes=30; energy=low; social_preference=solo; desired_experience=chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Practice a boss phase | 30 | high | solo | challenge | 5 | 3 | 0 | 7.0 |
| 2 | Quiet Cartographer / Sketch the lakeside trail | 20 | low | solo | chill | 2 | 2 | 0 | 7.0 |

Eligibility: ID 2 eligible. ID 1 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 2 | 6.25 | 7.5 | 10.0 | 15.0 | 10 | 20 | 0.0 | 0 | 68.75 | - | No gate |
| Baseline | 1 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 0 | 0.0 | 0 | 65.0 | - | No gate |
| Proposed | 2 | 6.25 | 7.5 | 10 | 30 | - | 20 | 0.0 | 0 | 73.75 | 60 | Yes |
| Proposed | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | No |

Proposed ID 1 remains eligible but does not qualify: Situational suitability 8.0 is below 25. Total score 48.0 is below 50.

Baseline winner: Quiet Cartographer.
Proposed result: **clear_recommendation**; choices in display order: Quiet Cartographer.

Changed: No winner change; unsuitable alternative now explicitly marked.

Why: Cartographer 73.75 wins. Summit has suitability 8 and total 48, failing both gates even though it remains eligible.

Intentional behavior / concern: Intentional strong energy/experience conflict detection; a suitability failure is a decision filter in practice, even though eligibility is unchanged.

### 4. Lower interest with a perfect situational fit

Situation: available_minutes=30; energy=low; social_preference=solo; desired_experience=chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Finish the evening harvest | 30 | low | solo | chill | 2 | 3 | 0 | 7.0 |
| 2 | Iron Summit / Practice a boss phase | 30 | high | solo | challenge | 5 | 3 | 0 | 7.0 |

Eligibility: ID 1 eligible. ID 2 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 1 | 6.25 | 15.0 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 81.25 | - | No gate |
| Baseline | 2 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 0 | 0.0 | 0 | 65.0 | - | No gate |
| Proposed | 1 | 6.25 | 15.0 | 8.0 | 30 | - | 20 | 0.0 | 0 | 79.25 | 58.0 | Yes |
| Proposed | 2 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | No |

Proposed ID 2 remains eligible but does not qualify: Situational suitability 8.0 is below 25. Total score 48.0 is below 50.

Baseline winner: Moonlit Orchard.
Proposed result: **clear_recommendation**; choices in display order: Moonlit Orchard.

Changed: No winner change; unsuitable alternative now explicitly marked.

Why: Orchard 79.25 wins with suitability 58; Summit again fails suitability and total thresholds.

Intentional behavior / concern: Intentional. Lower interest does not prevent a well-fitting candidate from meeting the combined threshold.

### 5. Two nearly identical candidates

Situation: available_minutes=30; energy=medium; social_preference=solo; desired_experience=progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Harbor Builder / Construct the west pier | 29 | medium | solo | progression | 4 | 2 | 0 | 7.0 |
| 2 | Forest Foundry / Construct the sawmill | 30 | medium | solo | progression | 4 | 2 | 0 | 7.0 |

Eligibility: ID 2 eligible. ID 1 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | No gate |
| Baseline | 1 | 18.75 | 7.5 | 14.5 | 15.0 | 10 | 20 | 0.0 | 0 | 85.75 | - | No gate |
| Proposed | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | Yes |
| Proposed | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | Yes |

Baseline winner: Forest Foundry.
Proposed result: **multiple_equivalent**; choices in display order: Harbor Builder, Forest Foundry.

Changed: Yes. Sole Forest Foundry becomes equivalent choices, with Harbor Builder displayed first.

Why: Both 29 and 30 minutes fall in the tight band and score 84.25. Priority ties; goal ID 1 sorts before 2.

Intentional behavior / concern: Intentional removal of one-minute precision sensitivity. ID preference remains a display convention, not evidence Harbor Builder is better.

### 6. Recently played favorite versus less-recent alternative

Situation: available_minutes=30; energy=low; social_preference=solo; desired_experience=chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Harvest the greenhouse | 30 | low | solo | chill | 5 | 2 | 0 | 0.0 |
| 2 | Quiet Cartographer / Map the old village | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |

Eligibility: ID 2 eligible. ID 1 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | No gate |
| Baseline | 1 | 25.0 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | -10.0 | 82.5 | - | No gate |
| Proposed | 1 | 25.0 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | -3.0 | 87.5 | 58.0 | Yes |
| Proposed | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | Yes |

Baseline winner: Quiet Cartographer.
Proposed result: **clear_recommendation**; choices in display order: Moonlit Orchard.

Changed: Yes. The recently played favorite becomes the sole choice.

Why: Orchard 87.5 versus Cartographer 84.25: interest advantage 6.25 now exceeds recency penalty 3 by 3.25, just outside the near-tie band.

Intentional behavior / concern: Intentional weaker variety nudge. No continuation intent was invented. Classification itself is fragile: only 0.25 outside the band.

### 7. High-friction favorite versus low-friction alternative

Situation: available_minutes=30; energy=medium; social_preference=solo; desired_experience=progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Starship Workshop / Install the engine upgrade | 30 | medium | solo | progression | 5 | 2 | 5 | 7.0 |
| 2 | Harbor Builder / Upgrade the fishing dock | 30 | medium | solo | progression | 4 | 2 | 0 | 7.0 |

Eligibility: ID 2 eligible. ID 1 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | No gate |
| Baseline | 1 | 25.0 | 7.5 | 15.0 | 15.0 | 10 | 20 | -10.0 | 0 | 82.5 | - | No gate |
| Proposed | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | Yes |
| Proposed | 1 | 25.0 | 7.5 | 8.0 | 30 | - | 20 | -10.0 | 0 | 80.5 | 58.0 | Yes |

Baseline winner: Harbor Builder.
Proposed result: **clear_recommendation**; choices in display order: Harbor Builder.

Changed: No. Harbor Builder stays the sole choice.

Why: Both lose the same constant social term and receive the same time/energy changes. Interest gap 6.25 still cannot offset friction gap 10; lead remains 3.75.

Intentional behavior / concern: Intentional retention of friction behavior. This policy does not claim to solve setup-time estimation.

### 8. Candidate excluded by available time

Situation: available_minutes=30; energy=high; social_preference=solo; desired_experience=challenge.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Finish the full boss encounter | 31 | high | solo | challenge | 5 | 3 | 0 | 7.0 |
| 2 | Clockwork Duel / Play one ranked match | 30 | high | solo | challenge | 3 | 2 | 0 | 7.0 |

Eligibility: ID 2 eligible.
- Both policies exclude ID 1: Needs 31 minutes; only 30 available.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 2 | 12.5 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 80.0 | - | No gate |
| Proposed | 2 | 12.5 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 78.0 | 58.0 | Yes |

Baseline winner: Clockwork Duel.
Proposed result: **clear_recommendation**; choices in display order: Clockwork Duel.

Changed: No. Clockwork Duel remains the sole eligible choice.

Why: The 31-minute candidate is still excluded. Duel scores 78 and passes suitability 58 and total 50 gates.

Intentional behavior / concern: Intentional preservation of the hard cutoff. Buffer is a soft 2-point deduction, not an additional exclusion.

### 9. Candidate excluded by solo/social requirements

Situation: available_minutes=45; energy=medium; social_preference=social; desired_experience=progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Harbor Builder / Upgrade the solo town | 45 | medium | solo | progression | 5 | 3 | 0 | 7.0 |
| 2 | Starship Crew / Complete a co-op expedition | 45 | medium | social | progression | 4 | 2 | 1 | 7.0 |
| 3 | Trail Partners / Restore the shared campsite | 30 | low | both | progression | 3 | 2 | 0 | 7.0 |

Eligibility: ID 2 eligible. ID 3 eligible.
- Both policies exclude ID 1: Activity is solo-only; preference is social.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | -2.0 | 0 | 84.25 | - | No gate |
| Baseline | 3 | 12.5 | 7.5 | 10.0 | 15.0 | 10 | 20 | 0.0 | 0 | 75.0 | - | No gate |
| Proposed | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | -2.0 | 0 | 82.25 | 58.0 | Yes |
| Proposed | 3 | 12.5 | 7.5 | 10 | 30 | - | 20 | 0.0 | 0 | 80.0 | 60 | Yes |

Baseline winner: Starship Crew.
Proposed result: **multiple_equivalent**; choices in display order: Starship Crew, Trail Partners.

Changed: Yes in classification; Starship Crew remains first.

Why: Solo candidate stays excluded. Crew 82.25 and Trail Partners 80 are near equivalent; the shorter goal gets full plateau credit.

Intentional behavior / concern: Intentional near-tie output, but social readiness remains unknown. Removing social points itself changes no order.

### 10. Multiple conflicting factors

Situation: available_minutes=60; energy=medium; social_preference=either; desired_experience=novelty.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Starship Crew / Explore the new nebula | 60 | high | social | challenge, novelty | 5 | 3 | 4 | 0.0 |
| 2 | Quiet Cartographer / Explore the desert atlas | 40 | low | solo | chill, novelty | 3 | 2 | 0 | 7.0 |
| 3 | Harbor Builder / Complete the harbor expansion | 60 | medium | solo | progression | 4 | 3 | 1 | 3.5 |

Eligibility: ID 2 eligible. ID 1 eligible. ID 3 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 2 | 12.5 | 7.5 | 10.0 | 15.0 | 10 | 20 | 0.0 | 0 | 75.0 | - | No gate |
| Baseline | 1 | 25.0 | 15.0 | 15.0 | 7.5 | 10 | 20 | -8.0 | -10.0 | 74.5 | - | No gate |
| Baseline | 3 | 18.75 | 15.0 | 15.0 | 15.0 | 10 | 0 | -2.0 | -5.0 | 66.75 | - | No gate |
| Proposed | 2 | 12.5 | 7.5 | 10 | 30 | - | 20 | 0.0 | 0 | 80.0 | 60 | Yes |
| Proposed | 1 | 25.0 | 15.0 | 8.0 | 15.0 | - | 20 | -8.0 | -3.0 | 72.0 | 43.0 | Yes |
| Proposed | 3 | 18.75 | 15.0 | 8.0 | 30 | - | 0 | -2.0 | -1.5 | 68.25 | 38.0 | Yes |

Baseline winner: Quiet Cartographer.
Proposed result: **clear_recommendation**; choices in display order: Quiet Cartographer.

Changed: No winner change; the lead becomes clearer.

Why: Cartographer 80 beats Crew 72 by 8 rather than 0.5. More energy weight and plateau time credit offset the reduced recency advantage.

Intentional behavior / concern: Intentional shift toward situational fit; cannot establish greater enjoyment from synthetic inputs.

### 11. Supplement: exact tie and stable order

Situation: available_minutes=30; energy=low; social_preference=solo; desired_experience=chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 2 | Quiet Cartographer / Sketch the river bend | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |
| 1 | Moonlit Orchard / Harvest the river plot | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |

Eligibility: ID 1 eligible. ID 2 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 1 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | No gate |
| Baseline | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | No gate |
| Proposed | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | Yes |
| Proposed | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | Yes |

Baseline winner: Moonlit Orchard.
Proposed result: **multiple_equivalent**; choices in display order: Moonlit Orchard, Quiet Cartographer.

Changed: Yes in classification; first display choice unchanged.

Why: Both score 84.25. Both are returned as equivalent; goal ID keeps Moonlit Orchard first.

Intentional behavior / concern: Intentional recognition of exact equivalence without randomness.

### 12. Supplement: negative-score eligible candidate

Situation: available_minutes=60; energy=low; social_preference=solo; desired_experience=chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Do a one-minute combat drill | 1 | high | solo | challenge | 1 | 1 | 5 | 0.0 |

Eligibility: ID 1 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 1 | 0.0 | 0.0 | 0.25 | 0.0 | 10 | 0 | -10.0 | -10.0 | -9.75 | - | No gate |
| Proposed | 1 | 0.0 | 0.0 | 10 | 0 | - | 0 | -10.0 | -3.0 | -3.0 | 10 | No |

Proposed ID 1 remains eligible but does not qualify: Situational suitability 10 is below 25. Total score -3.0 is below 50.

Baseline winner: Iron Summit.
Proposed result: **no_good_fit**; choices in display order: none.

Changed: Yes. A negative-score winner becomes no_good_fit.

Why: Summit scores -3 with suitability 10 and fails both thresholds. It is scored and retained as eligible, but there is no recommendation.

Intentional behavior / concern: Intentional explicit abstention; thresholds, not score sign alone, define the outcome.

### 13. Supplement: no eligible candidate

Situation: available_minutes=15; energy=low; social_preference=solo; desired_experience=chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Starship Crew / Complete a co-op expedition | 30 | medium | social | progression | 5 | 3 | 0 | 7.0 |

Eligibility: No eligible candidates.
- Both policies exclude ID 1: Needs 30 minutes; only 15 available. Activity is social-only; preference is solo.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |

Baseline winner: none.
Proposed result: **no_eligible**; choices in display order: none.

Changed: No. No eligible candidate under either policy.

Why: Time and social exclusions remain identical. Proposed status is no_eligible, distinct from scenario 12.

Intentional behavior / concern: Intentional distinction between feasibility and suitability.

## 8. Additional discriminating scenarios

### 14. Energy mismatch favorite still possible

Situation: available_minutes=30; energy=low; social_preference=solo; desired_experience=progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Train the new combat skill | 30 | high | solo | progression | 5 | 3 | 0 | 7.0 |
| 2 | Moonlit Orchard / Grow a basic crop | 30 | low | solo | progression | 1 | 1 | 0 | 7.0 |

Eligibility: ID 1 eligible. ID 2 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 1 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 20 | 0.0 | 0 | 85.0 | - | No gate |
| Baseline | 2 | 0.0 | 0.0 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 60.0 | - | No gate |
| Proposed | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 20 | 0.0 | 0 | 68.0 | 28.0 | Yes |
| Proposed | 2 | 0.0 | 0.0 | 8.0 | 30 | - | 20 | 0.0 | 0 | 58.0 | 58.0 | Yes |

Baseline winner: Iron Summit.
Proposed result: **clear_recommendation**; choices in display order: Iron Summit.

Changed: No. The high-energy favorite still wins.

Why: Summit 68 versus Orchard 58. Experience match supplies suitability 28, so the severe mismatch is not categorically blocked; maximum preference exceeds the 30-point energy disadvantage by 10.

Intentional behavior / concern: Intentionally demonstrates the requested escape for a favorite demanding game. Human judgment is needed on whether this escape is too generous.

### 15. Time buffer band boundary

Situation: available_minutes=30; energy=medium; social_preference=solo; desired_experience=progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Forest Foundry / Build the workshop | 28 | medium | solo | progression | 4 | 2 | 0 | 7.0 |
| 2 | Harbor Builder / Build the dock | 27 | medium | solo | progression | 4 | 2 | 0 | 7.0 |

Eligibility: ID 1 eligible. ID 2 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 1 | 18.75 | 7.5 | 14.0 | 15.0 | 10 | 20 | 0.0 | 0 | 85.25 | - | No gate |
| Baseline | 2 | 18.75 | 7.5 | 13.5 | 15.0 | 10 | 20 | 0.0 | 0 | 84.75 | - | No gate |
| Proposed | 2 | 18.75 | 7.5 | 10 | 30 | - | 20 | 0.0 | 0 | 86.25 | 60 | Yes |
| Proposed | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | Yes |

Baseline winner: Forest Foundry.
Proposed result: **multiple_equivalent**; choices in display order: Harbor Builder, Forest Foundry.

Changed: Yes. The first display choice reverses and both are equivalent.

Why: 27 minutes earns 10 time points; 28 earns 8. Harbor 86.25 precedes Forest 84.25, whereas linear baseline favors 28 minutes.

Intentional behavior / concern: A band boundary still introduces a 2-point cliff for one minute. Near equivalence mitigates interpretation but not the ordering reversal.

### 16. Very short goal in a long window

Situation: available_minutes=120; energy=low; social_preference=solo; desired_experience=chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Water one plant | 1 | low | solo | chill | 4 | 2 | 0 | 7.0 |
| 2 | Quiet Cartographer / Map the whole forest | 90 | low | solo | chill | 4 | 2 | 0 | 7.0 |

Eligibility: ID 2 eligible. ID 1 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 2 | 18.75 | 7.5 | 11.25 | 15.0 | 10 | 20 | 0.0 | 0 | 82.5 | - | No gate |
| Baseline | 1 | 18.75 | 7.5 | 0.125 | 15.0 | 10 | 20 | 0.0 | 0 | 71.375 | - | No gate |
| Proposed | 1 | 18.75 | 7.5 | 10 | 30 | - | 20 | 0.0 | 0 | 86.25 | 60 | Yes |
| Proposed | 2 | 18.75 | 7.5 | 10 | 30 | - | 20 | 0.0 | 0 | 86.25 | 60 | Yes |

Baseline winner: Quiet Cartographer.
Proposed result: **multiple_equivalent**; choices in display order: Moonlit Orchard, Quiet Cartographer.

Changed: Yes. The long goal becomes tied with a one-minute task; the one-minute task is first.

Why: Both are below 90% and earn 10 time points; equal preference yields 86.25 each. Baseline time points 0.125 versus 11.25 favor the long goal.

Intentional behavior / concern: Potential regression: a plateau with no lower occupancy bound ignores the difference between a tiny chore and a substantial session.

### 17. Recent-play ordering with equal interest

Situation: available_minutes=30; energy=low; social_preference=solo; desired_experience=chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Harvest the orchard | 30 | low | solo | chill | 4 | 2 | 0 | 0.0 |
| 2 | Quiet Cartographer / Map the orchard trail | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |

Eligibility: ID 2 eligible. ID 1 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | No gate |
| Baseline | 1 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | -10.0 | 76.25 | - | No gate |
| Proposed | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | Yes |
| Proposed | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | -3.0 | 81.25 | 58.0 | Yes |

Baseline winner: Quiet Cartographer.
Proposed result: **multiple_equivalent**; choices in display order: Quiet Cartographer, Moonlit Orchard.

Changed: Yes in classification; the less-recent alternative stays first.

Why: Equal interest leaves the full 3-point recency difference. The inclusive near-tie rule returns both candidates.

Intentional behavior / concern: Intentional: recency still nudges variety without claiming the recent option is decisively worse.

### 18. Total threshold across priority step

Situation: available_minutes=30; energy=low; social_preference=solo; desired_experience=challenge.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Complete a peaceful chore | 30 | low | solo | chill | 1 | 2 | 0 | 7.0 |
| 2 | Quiet Cartographer / Finish the peaceful atlas | 30 | low | solo | chill | 1 | 3 | 0 | 7.0 |

Eligibility: ID 2 eligible. ID 1 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 2 | 0.0 | 15.0 | 15.0 | 15.0 | 10 | 0 | 0.0 | 0 | 55.0 | - | No gate |
| Baseline | 1 | 0.0 | 7.5 | 15.0 | 15.0 | 10 | 0 | 0.0 | 0 | 47.5 | - | No gate |
| Proposed | 2 | 0.0 | 15.0 | 8.0 | 30 | - | 0 | 0.0 | 0 | 53.0 | 38.0 | Yes |
| Proposed | 1 | 0.0 | 7.5 | 8.0 | 30 | - | 0 | 0.0 | 0 | 45.5 | 38.0 | No |

Proposed ID 1 remains eligible but does not qualify: Total score 45.5 is below 50.

Baseline winner: Quiet Cartographer.
Proposed result: **clear_recommendation**; choices in display order: Quiet Cartographer.

Changed: No first-choice change; one eligible candidate now fails the gate.

Why: Both have suitability 38 and miss the requested challenge tag. Priority 2 yields 45.5 (below 50), priority 3 yields 53 (above 50).

Intentional behavior / concern: Unexpected tradeoff: priority can push an otherwise identical experiential mismatch into suitability acceptance through the total-score gate. Labels should not imply fit depends only on context.

### 19. Suitability gate rejects a high-total mismatch

Situation: available_minutes=30; energy=low; social_preference=solo; desired_experience=chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Fight the boss again | 30 | high | solo | challenge | 5 | 3 | 0 | 7.0 |

Eligibility: ID 1 eligible.

| Policy | ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total | Suitability | Qualifies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 1 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 0 | 0.0 | 0 | 65.0 | - | No gate |
| Proposed | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | No |

Proposed ID 1 remains eligible but does not qualify: Situational suitability 8.0 is below 25. Total score 48.0 is below 50.

Baseline winner: Iron Summit.
Proposed result: **no_good_fit**; choices in display order: none.

Changed: Yes. Baseline favorite becomes no_good_fit.

Why: Severe energy mismatch plus missing chill tag yields suitability 8 and total 48. A comfortable 20-minute estimate (tested separately) would raise total to 50 but suitability remains 10, so the explicit suitability gate still blocks it.

Intentional behavior / concern: Intentional independent suitability gate. Its cutoff needs real-user calibration; no statistical evidence supports 25 or 50 yet.

## 9. Unexpected results

- Scenario 2 changes a previously clear high-energy/long-session winner into a 0.25-point near tie. Removing occupancy preference makes a shorter ladder run competitive with the boss encounter.
- Scenario 16 ties a one-minute chore with a 90-minute goal, then puts the chore first by ID. The comfortable-fit plateau is too broad if users expect a meaningful session-sized accomplishment.
- Scenario 15 reverses duration ordering at the 90% boundary. The band avoids continuous precision sensitivity but creates a discontinuity.
- Scenario 18 shows priority alone deciding whether an experiential mismatch meets the total threshold. Explicit suitability gates do not completely separate preference from acceptance.
- Scenario 6 is clear by only 0.25 beyond the near-tie cutoff. The new classification has its own precision boundary.

## 10. Improvements relative to baseline

- Scenario 1 responds more strongly to low energy while scenario 14 preserves a demanding-favorite escape. This matches the proposed intent in those examples, not a universal guarantee.
- 29/30-minute differences no longer create a falsely precise sole winner in scenario 5.
- Recent favorite survives a one-step interest difference (scenario 6), and equal-interest recency differences are treated as equivalent choices (17).
- Social eligibility is unchanged; removing its constant score makes every ranked factor convey distinguishing information somewhere in the input space.
- Explicit no_good_fit and no_eligible distinguish unsuitable choices from infeasible ones (12, 13, 19).
- All outputs retain determinism and additive explanations; choices remain inspectable, including unsuitable eligible options.

## 11. Regressions and tradeoffs

- Loss of meaningful duration discrimination is demonstrated by scenario 16; this is a substantive reason not to adopt yet.
- Arbitrary thresholds and time bands introduce cliffs. No user evidence establishes 25, 50, 90%, or 3 points as the right cutoffs.
- Weaker recency may under-encourage variety for someone who wanted a change. Continuation intent and enjoyment are still unknown.
- Stronger energy can restrict challenge preferences; missing an experience tag makes a severe energy mismatch fail suitability regardless of high preference.
- A near-tie group can dilute a user request for one answer, and the first item still benefits from ID order when totals tie.
- Removing constant social points changes score scale without itself improving order; threshold calibration must use the new scale.
- The combined changes confound causal interpretation. Factor breakdowns explain arithmetic, but this experiment is not an ablation study showing which individual change is best.

## 12. Remaining weaknesses

Binary game-level experience tags, subjective interest/friction scales, unknown social availability, no inferred setup minutes, and lack of actual enjoyment data remain. High-energy contexts still give lower-energy games full energy points. A 10% buffer deduction reserves no actual time. Very short goals receive maximum time credit. There is no continuation signal and no calibrated recommendation confidence. Future suitability snapshots would need policy version, thresholds, weights, and the explicit result status, but no persistence changes were made.

## 13. Decisions requiring human judgment

1. Accept stronger soft energy weighting and a suitability gate, including the demanding-favorite escape in scenario 14, or require a different relationship between energy and preference?
2. Should time fit distinguish tiny tasks from substantial session goals? Should a comfort band include a minimum occupancy, and should estimates include setup? Is a soft proportional buffer appropriate?
3. Is weaker recency alone enough, or should a later input explicitly distinguish continuation versus variety? Do not infer it from history.
4. Is three points a useful near-equivalence band, and should the UI show multiple choices or one primary plus alternatives?
5. Should acceptance depend partly on interest/priority through the total gate, or solely on situational suitability? What examples should define acceptable abstention?
6. Are these gates/weights worth another controlled comparison before production adoption?

## 14. Recommendation

**Run another experiment; retain v0.1 as the unchanged production baseline.** The proposed policy addresses several observed issues, but the tiny-task duration tie and uncalibrated acceptance cliffs are material tradeoffs. A follow-up should compare a minimum-occupancy comfort band or another bounded duration policy against these same inputs, include threshold-adjacent examples, and ideally test a few real personal-library choices. Hold unrelated factors fixed to isolate effects. Do not adopt experiment-002 or start Milestone 2 without user direction.

## 15. Files and historical preservation

Created `backend/experiments/__init__.py`, `policy_002.py`, `comparison_002.py`, `backend/tests/test_policy_002.py`, and this report. Updated only the mutable `reports/README.md` index among existing planning/report files. Production engine, report 001, original fixtures/tests, weights, database, API, and frontend were not changed. Reports are historical records; repeat investigations or corrections belong in report 003 or the next available number, referencing this report.
