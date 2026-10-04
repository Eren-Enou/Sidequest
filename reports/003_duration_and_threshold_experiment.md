# 003: Duration-fit and suitability-boundary refinement

Date: 2026-10-03 (America/Los_Angeles). Milestone: 1 policy investigation. Status: complete; candidate not adopted.

Historical references: [001](001_milestone_1_engine_evaluation.md), [002](002_scoring_policy_experiment.md). Neither report nor the baseline/002 engines, fixtures, or tests was modified. Milestone 2 remains unstarted.

## 1. Experiment question

Can a continuous duration rule fix the one-minute/90-minute tie while preserving Experiment 002 improvements? Do unchanged suitability, total, and equivalence boundaries remain concerning? This is synthetic behavioral evaluation, not empirical calibration or evidence of improved enjoyment.

## 2. Behaviors intentionally held constant

All non-time factor objects are reused verbatim from Experiment 002: interest 25, priority 15, energy 30 (sufficient/one-step/two-step multipliers 1/0.5/0), experience 20, friction penalty up to 10, seven-day recency penalty up to 3. Social remains eligibility only. Lifecycle/time/social filters and validation are unchanged. Energy remains soft, with the demanding-favorite escape retained.

Ordering remains total descending, priority descending, goal ID ascending, then game ID ascending. Suitability minimum 25, total minimum 50, and near-tie margin 3 retain inclusive comparisons. No thresholds or unrelated weights were optimized. All four outcome statuses remain.

Implementation: `backend/experiments/policy_003.py` calls the frozen 002 function, replaces only the time factor, then recalculates totals, acceptance reasons, ordering, and near-tie membership using identical rules. Version: experiment-003. Research dependency chaining redundantly computes older scores; this is a small experiment implementation, not a recommended production architecture. No application integration was added.

## 3. Time-fit alternatives considered

Let r = estimated_minutes / available_minutes on eligible positive durations. All alternatives have maximum 10 points. Goals beyond available time are excluded before scoring.

| Approach | Formula | Very short | Preferred region | Near limit | Explanation / complexity |
| --- | --- | --- | --- | --- | --- |
| A: linear ramp + plateau (selected) | 20r below 0.5; 10 through 0.9; 10 - 20(r - 0.9) thereafter | Linear small contribution | Equal full credit from 50% to 90% | Continuous decline to 8 | Simple three-piece rule; continuous values, corners in slope |
| B: smoothstep plateau | 10h(2r) below 0.5; 10 through 0.9; 10 - 2h((r - 0.9)/0.1) thereafter; h(t)=3t^2-2t^3 | Suppresses tiny tasks more strongly | Smooth entry/exit to plateau | Smooth decline to 8 | Cubic easing is harder to explain for little product gain |
| C: bounded parabola | 10 * [1 - ((r - 0.7)/0.7)^2] | Approaches zero | Peak at 70%; broad but no plateau | 8.163265... at 100% | One equation but arbitrary ideal peak; small differences still affect ranking |

All three were evaluated at every requested duration matrix point. Maximum adjacent-minute contribution change across each complete eligible window:

| Available minutes | A maximum change | B maximum change | C maximum change |
| ---: | ---: | ---: | ---: |
| 30 | 0.666667 | 0.998519 | 0.884354 |
| 60 | 0.333333 | 0.499259 | 0.459184 |
| 120 | 0.166667 | 0.249907 | 0.233844 |

A has the smallest worst-case adjacent-minute change in these windows and exact equality across the preferred region. B is smoother in derivative but steeper elsewhere, and more harshly discounts small useful chunks. C is bounded and continuous but continues favoring a particular precise duration. None represents uncertainty in estimates. A was selected for the simplest explanation and wide preferred region, rather than claiming one ideal duration. This compares time behavior, not all possible recalibrated full scoring policies.

## 4. Selected formula and rationale

```text
r = estimated_minutes / available_minutes
if estimated_minutes > available_minutes: ineligible
elif r < 0.5: time_fit = 20 * r
elif r <= 0.9: time_fit = 10
else: time_fit = 10 - 20 * (r - 0.9)
```

The ramp distinguishes trivial, reasonable, and substantial goals. Half a window earns full credit. The 50-90% plateau tolerates estimate noise while encouraging room for overruns. Full-window estimates retain 8 points and remain viable. The decline is a soft buffer preference, not guaranteed slack or invented setup minutes.

Values are continuous at 50% and 90%, with no new jumps. Maximum adjacent change is 20/window: 59 versus 60 minutes changes by 1/6 point in a 120-minute window and by 1/3 in a 60-minute window, well inside the three-point equivalence band when all else is equal.

The duration function uses rational arithmetic before returning floats, avoiding incidental binary rounding in breakpoint calculations. Inherited float summation can still represent 49.98 as 49.980000000000004. Tests compare expected decimals approximately while checking exact breakdown-to-total sums. No decision epsilon or rounding was introduced.

## 5. Full duration test matrix

Time contributions are rounded to six decimals for display only; replay JSON retains raw values. Each matrix candidate has interest 4, priority 2, low energy, chill tag, friction 0, and last completed play seven days ago. Context is low/solo/chill. Every eligible matrix candidate still qualifies under 003, including near-full-window goals; window+1 is excluded by all policies.

| Available | Estimate | Eligibility | 002 time | A / 003 time | B time | C time | 003 outcome |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| 30 | 1 | eligible | 10 | 0.666667 | 0.127407 | 0.929705 | clear_recommendation |
| 30 | 5 | eligible | 10 | 3.333333 | 2.592593 | 4.195011 | clear_recommendation |
| 30 | 10 | eligible | 10 | 6.666667 | 7.407407 | 7.256236 | clear_recommendation |
| 30 | 15 | eligible | 10 | 10.000000 | 10.000000 | 9.183673 | clear_recommendation |
| 30 | 20 | eligible | 10 | 10.000000 | 10.000000 | 9.977324 | clear_recommendation |
| 30 | 25 | eligible | 10 | 10.000000 | 10.000000 | 9.637188 | clear_recommendation |
| 30 | 27 | eligible | 10 | 10.000000 | 10.000000 | 9.183673 | clear_recommendation |
| 30 | 28 | eligible | 8 | 9.333333 | 9.481481 | 8.888889 | clear_recommendation |
| 30 | 29 | eligible | 8 | 8.666667 | 8.518519 | 8.548753 | clear_recommendation |
| 30 | 30 | eligible | 8 | 8.000000 | 8.000000 | 8.163265 | clear_recommendation |
| 30 | 31 | excluded | - | - | - | - | no_eligible |
| 60 | 1 | eligible | 10 | 0.333333 | 0.032593 | 0.470522 | clear_recommendation |
| 60 | 5 | eligible | 10 | 1.666667 | 0.740741 | 2.239229 | clear_recommendation |
| 60 | 15 | eligible | 10 | 5.000000 | 5.000000 | 5.867347 | clear_recommendation |
| 60 | 30 | eligible | 10 | 10.000000 | 10.000000 | 9.183673 | clear_recommendation |
| 60 | 40 | eligible | 10 | 10.000000 | 10.000000 | 9.977324 | clear_recommendation |
| 60 | 45 | eligible | 10 | 10.000000 | 10.000000 | 9.948980 | clear_recommendation |
| 60 | 50 | eligible | 10 | 10.000000 | 10.000000 | 9.637188 | clear_recommendation |
| 60 | 55 | eligible | 8 | 9.666667 | 9.851852 | 9.041950 | clear_recommendation |
| 60 | 59 | eligible | 8 | 8.333333 | 8.148148 | 8.361678 | clear_recommendation |
| 60 | 60 | eligible | 8 | 8.000000 | 8.000000 | 8.163265 | clear_recommendation |
| 60 | 61 | excluded | - | - | - | - | no_eligible |
| 120 | 1 | eligible | 10 | 0.166667 | 0.008241 | 0.236678 | clear_recommendation |
| 120 | 15 | eligible | 10 | 2.500000 | 1.562500 | 3.252551 | clear_recommendation |
| 120 | 30 | eligible | 10 | 5.000000 | 5.000000 | 5.867347 | clear_recommendation |
| 120 | 45 | eligible | 10 | 7.500000 | 8.437500 | 7.844388 | clear_recommendation |
| 120 | 60 | eligible | 10 | 10.000000 | 10.000000 | 9.183673 | clear_recommendation |
| 120 | 90 | eligible | 10 | 10.000000 | 10.000000 | 9.948980 | clear_recommendation |
| 120 | 100 | eligible | 10 | 10.000000 | 10.000000 | 9.637188 | clear_recommendation |
| 120 | 108 | eligible | 10 | 10.000000 | 10.000000 | 9.183673 | clear_recommendation |
| 120 | 115 | eligible | 8 | 8.833333 | 8.752315 | 8.638039 | clear_recommendation |
| 120 | 119 | eligible | 8 | 8.166667 | 8.039352 | 8.263889 | clear_recommendation |
| 120 | 120 | eligible | 8 | 8.000000 | 8.000000 | 8.163265 | clear_recommendation |
| 120 | 121 | excluded | - | - | - | - | no_eligible |

For a 120-minute window: 1 minute earns 0.166667; 15 earns 2.5; 45 earns 7.5; 60, 90, and 108 earn 10; 119 earns 8.166667; 120 earns 8; 121 is excluded. A short goal remains feasible without equaling a substantial goal on time alone. A goal need not consume 100% to score well.

## 6. Threshold sensitivity analysis

Boundary probes use a manufactured 1,000-minute window, where a one-minute estimate change produces 0.02 points on the rising slope. This long window isolates immediate boundaries; it does not represent a usual session. All original thresholds remain unchanged. Full inputs and breakdowns follow below.

| Boundary | Immediately below | At | Immediately above | 003 outcome |
| --- | --- | --- | --- | --- |
| Suitability 25 | 24.98 (249 min) | 25 (250 min) | 25.02 (251 min) | no_good_fit -> clear -> clear, despite totals 64.98/65/65.02 |
| Total 50 | 49.98 (249 min) | 50 (250 min) | 50.02 (251 min) | no_good_fit -> clear -> clear; suitability passes throughout |
| Near-tie gap 3 | 2.98 (351 min) | 3 (350 min) | 3.02 (349 min) | multiple -> multiple -> clear; first choice never changes |

These are actual categorical cliffs despite continuous time scoring, not arithmetic bugs. A 0.02-point change can flip acceptance or classification under inclusive rules. Labels must not imply calibrated confidence. In ordinary windows the 27/28-minute boundary difference shrinks from 002's two points to 2/3; 29/30-minute goals remain near-equivalent.

Eligibility means feasible. Numeric situational suitability is time + energy + experience. Preference is interest + priority. However, inherited Assessment.suitable means passes BOTH suitability and total gates; it is recommendation acceptance, not pure situational fitness.

The existing priority-step scenario remains a counterexample: both candidates have identical suitability 38 and lack the requested challenge tag, but priority 2 produces total 45.5 (rejected), while priority 3 produces 53 (accepted). Thus minimum_total improperly affects the label if suitable means fits the situation alone. It is defensible as a separate desirability threshold, but should not be called situational suitability.

Simpler counterfactual (analysis only, not implemented): remove minimum_total and retain the suitability gate. Both priority-step candidates would qualify and priority would only order them. The below-total probe, suitability 34.98, would also be recommended despite low interest. Removing both gates reintroduces the bad-fit-only problem; a fuzzy boundary still needs an abstention cutoff. This demonstrates a policy question without redesigning unrelated rules during the time experiment.

Assessment: three points is acceptable provisionally as a presentation convention if clear does not imply certainty. Acceptance gates 25/50 remain concerning; human judgment must establish whether low preference should cause abstention. They are not empirically calibrated measures of situational fitness.

## 7. Compact three-way comparison for all 19 historical scenarios

| Scenario | v0.1 | Experiment 002 | Experiment 003 | 002 behavior preserved? |
| --- | --- | --- | --- | --- |
| 1. Low energy + short session + progression | Iron Summit | clear_recommendation: Moonlit Orchard | clear_recommendation: Moonlit Orchard | Yes |
| 2. High energy + long session + challenge | Iron Summit | multiple_equivalent: Iron Summit, Clockwork Duel | multiple_equivalent: Iron Summit, Clockwork Duel | Yes |
| 3. Strong interest in a poor situational fit | Quiet Cartographer | clear_recommendation: Quiet Cartographer | clear_recommendation: Quiet Cartographer | Yes |
| 4. Lower interest with a perfect situational fit | Moonlit Orchard | clear_recommendation: Moonlit Orchard | clear_recommendation: Moonlit Orchard | Yes |
| 5. Two nearly identical candidates | Forest Foundry | multiple_equivalent: Harbor Builder, Forest Foundry | multiple_equivalent: Harbor Builder, Forest Foundry | Yes |
| 6. Recently played favorite versus less-recent alternative | Quiet Cartographer | clear_recommendation: Moonlit Orchard | clear_recommendation: Moonlit Orchard | Yes |
| 7. High-friction favorite versus low-friction alternative | Harbor Builder | clear_recommendation: Harbor Builder | clear_recommendation: Harbor Builder | Yes |
| 8. Candidate excluded by available time | Clockwork Duel | clear_recommendation: Clockwork Duel | clear_recommendation: Clockwork Duel | Yes |
| 9. Candidate excluded by solo/social requirements | Starship Crew | multiple_equivalent: Starship Crew, Trail Partners | multiple_equivalent: Starship Crew, Trail Partners | Yes |
| 10. Multiple conflicting factors | Quiet Cartographer | clear_recommendation: Quiet Cartographer | clear_recommendation: Quiet Cartographer | Yes |
| 11. Supplement: exact tie and stable order | Moonlit Orchard | multiple_equivalent: Moonlit Orchard, Quiet Cartographer | multiple_equivalent: Moonlit Orchard, Quiet Cartographer | Yes |
| 12. Supplement: negative-score eligible candidate | Iron Summit | no_good_fit | no_good_fit | Yes |
| 13. Supplement: no eligible candidate | no_eligible | no_eligible | no_eligible | Yes |
| 14. Energy mismatch favorite still possible | Iron Summit | clear_recommendation: Iron Summit | clear_recommendation: Iron Summit | Yes |
| 15. Time buffer band boundary | Forest Foundry | multiple_equivalent: Harbor Builder, Forest Foundry | multiple_equivalent: Harbor Builder, Forest Foundry | Yes |
| 16. Very short goal in a long window | Quiet Cartographer | multiple_equivalent: Moonlit Orchard, Quiet Cartographer | clear_recommendation: Quiet Cartographer | No; intended tiny-task fix |
| 17. Recent-play ordering with equal interest | Quiet Cartographer | multiple_equivalent: Quiet Cartographer, Moonlit Orchard | multiple_equivalent: Quiet Cartographer, Moonlit Orchard | Yes |
| 18. Total threshold across priority step | Quiet Cartographer | clear_recommendation: Quiet Cartographer | clear_recommendation: Quiet Cartographer | Yes |
| 19. Suitability gate rejects a high-total mismatch | Iron Summit | no_good_fit | no_good_fit | Yes |

18/19 recommendation sets, statuses, and display orders match Experiment 002. The sole change is scenario 16: Quiet Cartographer becomes clear over the one-minute orchard chore, 86.25 versus 76.41666666666667 (approximately 9.833333 points apart). All observed 002 improvements are preserved, including low-energy choice, recent favorite, friction outcome, demanding-favorite escape, near ties, no_good_fit, and no_eligible.

Some scores change without semantic changes. Scenario 5 assigns 29 minutes 8.666667 time points versus 8 for 30; both remain equivalent. Scenario 15 assigns 27 minutes 10 versus 9.333333 for 28, removing the two-point jump. The negative candidate becomes more negative as its trivial time credit declines, but remains no_good_fit.

## 8. Full inputs and scoring results

Raw floats below preserve every factor under all three policies. Suitability is a subtotal, not another factor. A dash means the social factor was removed; omit it when summing. Game ID equals goal ID, IDs are local to scenarios, all lifecycle fields are active. Last play is exact elapsed days before the inherited fixed clock 2026-10-03T19:00:00+00:00. Cases 1-19 are historical inputs; cases 20-28 are new threshold probes.

### Case 1: Low energy + short session + progression

Context: 20 minutes; energy low; social solo; experience progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Upgrade the watering can | 15 | low | solo | chill, progression | 4 | 2 | 1 | 7.0 |
| 2 | Iron Summit / Clear the training arena | 20 | high | solo | challenge, progression | 5 | 3 | 1 | 7.0 |

All policies: ID 2 eligible. ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 2 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 20 | -2.0 | 0 | 83.0 | - | no gate |
| v0.1 | 1 | 18.75 | 7.5 | 11.25 | 15.0 | 10 | 20 | -2.0 | 0 | 80.5 | - | no gate |
| 002 | 1 | 18.75 | 7.5 | 10 | 30 | - | 20 | -2.0 | 0 | 84.25 | 60 | yes |
| 002 | 2 | 25.0 | 15.0 | 8.0 | 0 | - | 20 | -2.0 | 0 | 66.0 | 28.0 | yes |
| 003 | 1 | 18.75 | 7.5 | 10.0 | 30 | - | 20 | -2.0 | 0 | 84.25 | 60.0 | yes |
| 003 | 2 | 25.0 | 15.0 | 8.0 | 0 | - | 20 | -2.0 | 0 | 66.0 | 28.0 | yes |

Results: v0.1 = Iron Summit; 002 = clear_recommendation: Moonlit Orchard; 003 = clear_recommendation: Moonlit Orchard.

### Case 2: High energy + long session + challenge

Context: 120 minutes; energy high; social solo; experience challenge.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Conquer the summit boss | 120 | high | solo | challenge | 5 | 3 | 2 | 7.0 |
| 2 | Clockwork Duel / Complete a ranked ladder run | 60 | medium | solo | challenge | 4 | 3 | 0 | 7.0 |
| 3 | Moonlit Orchard / Expand the orchard | 90 | low | solo | chill, progression | 5 | 3 | 0 | 7.0 |

All policies: ID 1 eligible. ID 2 eligible. ID 3 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 25.0 | 15.0 | 15.0 | 15.0 | 10 | 20 | -4.0 | 0 | 96.0 | - | no gate |
| v0.1 | 2 | 18.75 | 15.0 | 7.5 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| v0.1 | 3 | 25.0 | 15.0 | 11.25 | 15.0 | 10 | 0 | 0.0 | 0 | 76.25 | - | no gate |
| 002 | 1 | 25.0 | 15.0 | 8.0 | 30 | - | 20 | -4.0 | 0 | 94.0 | 58.0 | yes |
| 002 | 2 | 18.75 | 15.0 | 10 | 30 | - | 20 | 0.0 | 0 | 93.75 | 60 | yes |
| 002 | 3 | 25.0 | 15.0 | 10 | 30 | - | 0 | 0.0 | 0 | 80.0 | 40 | yes |
| 003 | 1 | 25.0 | 15.0 | 8.0 | 30 | - | 20 | -4.0 | 0 | 94.0 | 58.0 | yes |
| 003 | 2 | 18.75 | 15.0 | 10.0 | 30 | - | 20 | 0.0 | 0 | 93.75 | 60.0 | yes |
| 003 | 3 | 25.0 | 15.0 | 10.0 | 30 | - | 0 | 0.0 | 0 | 80.0 | 40.0 | yes |

Results: v0.1 = Iron Summit; 002 = multiple_equivalent: Iron Summit, Clockwork Duel; 003 = multiple_equivalent: Iron Summit, Clockwork Duel.

### Case 3: Strong interest in a poor situational fit

Context: 30 minutes; energy low; social solo; experience chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Practice a boss phase | 30 | high | solo | challenge | 5 | 3 | 0 | 7.0 |
| 2 | Quiet Cartographer / Sketch the lakeside trail | 20 | low | solo | chill | 2 | 2 | 0 | 7.0 |

All policies: ID 2 eligible. ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 2 | 6.25 | 7.5 | 10.0 | 15.0 | 10 | 20 | 0.0 | 0 | 68.75 | - | no gate |
| v0.1 | 1 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 0 | 0.0 | 0 | 65.0 | - | no gate |
| 002 | 2 | 6.25 | 7.5 | 10 | 30 | - | 20 | 0.0 | 0 | 73.75 | 60 | yes |
| 002 | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | no |

002 ID 1 remains eligible but fails acceptance: Situational suitability 8.0 is below 25. Total score 48.0 is below 50.
| 003 | 2 | 6.25 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 73.75 | 60.0 | yes |
| 003 | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | no |

003 ID 1 remains eligible but fails acceptance: Situational suitability 8.0 is below 25. Total score 48.0 is below 50.

Results: v0.1 = Quiet Cartographer; 002 = clear_recommendation: Quiet Cartographer; 003 = clear_recommendation: Quiet Cartographer.

### Case 4: Lower interest with a perfect situational fit

Context: 30 minutes; energy low; social solo; experience chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Finish the evening harvest | 30 | low | solo | chill | 2 | 3 | 0 | 7.0 |
| 2 | Iron Summit / Practice a boss phase | 30 | high | solo | challenge | 5 | 3 | 0 | 7.0 |

All policies: ID 1 eligible. ID 2 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 6.25 | 15.0 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 81.25 | - | no gate |
| v0.1 | 2 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 0 | 0.0 | 0 | 65.0 | - | no gate |
| 002 | 1 | 6.25 | 15.0 | 8.0 | 30 | - | 20 | 0.0 | 0 | 79.25 | 58.0 | yes |
| 002 | 2 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | no |

002 ID 2 remains eligible but fails acceptance: Situational suitability 8.0 is below 25. Total score 48.0 is below 50.
| 003 | 1 | 6.25 | 15.0 | 8.0 | 30 | - | 20 | 0.0 | 0 | 79.25 | 58.0 | yes |
| 003 | 2 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | no |

003 ID 2 remains eligible but fails acceptance: Situational suitability 8.0 is below 25. Total score 48.0 is below 50.

Results: v0.1 = Moonlit Orchard; 002 = clear_recommendation: Moonlit Orchard; 003 = clear_recommendation: Moonlit Orchard.

### Case 5: Two nearly identical candidates

Context: 30 minutes; energy medium; social solo; experience progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Harbor Builder / Construct the west pier | 29 | medium | solo | progression | 4 | 2 | 0 | 7.0 |
| 2 | Forest Foundry / Construct the sawmill | 30 | medium | solo | progression | 4 | 2 | 0 | 7.0 |

All policies: ID 2 eligible. ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| v0.1 | 1 | 18.75 | 7.5 | 14.5 | 15.0 | 10 | 20 | 0.0 | 0 | 85.75 | - | no gate |
| 002 | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 002 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 003 | 1 | 18.75 | 7.5 | 8.666666666666666 | 30 | - | 20 | 0.0 | 0 | 84.91666666666666 | 58.666666666666664 | yes |
| 003 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |

Results: v0.1 = Forest Foundry; 002 = multiple_equivalent: Harbor Builder, Forest Foundry; 003 = multiple_equivalent: Harbor Builder, Forest Foundry.

### Case 6: Recently played favorite versus less-recent alternative

Context: 30 minutes; energy low; social solo; experience chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Harvest the greenhouse | 30 | low | solo | chill | 5 | 2 | 0 | 0.0 |
| 2 | Quiet Cartographer / Map the old village | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |

All policies: ID 2 eligible. ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| v0.1 | 1 | 25.0 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | -10.0 | 82.5 | - | no gate |
| 002 | 1 | 25.0 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | -3.0 | 87.5 | 58.0 | yes |
| 002 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 003 | 1 | 25.0 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | -3.0 | 87.5 | 58.0 | yes |
| 003 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |

Results: v0.1 = Quiet Cartographer; 002 = clear_recommendation: Moonlit Orchard; 003 = clear_recommendation: Moonlit Orchard.

### Case 7: High-friction favorite versus low-friction alternative

Context: 30 minutes; energy medium; social solo; experience progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Starship Workshop / Install the engine upgrade | 30 | medium | solo | progression | 5 | 2 | 5 | 7.0 |
| 2 | Harbor Builder / Upgrade the fishing dock | 30 | medium | solo | progression | 4 | 2 | 0 | 7.0 |

All policies: ID 2 eligible. ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| v0.1 | 1 | 25.0 | 7.5 | 15.0 | 15.0 | 10 | 20 | -10.0 | 0 | 82.5 | - | no gate |
| 002 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 002 | 1 | 25.0 | 7.5 | 8.0 | 30 | - | 20 | -10.0 | 0 | 80.5 | 58.0 | yes |
| 003 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 003 | 1 | 25.0 | 7.5 | 8.0 | 30 | - | 20 | -10.0 | 0 | 80.5 | 58.0 | yes |

Results: v0.1 = Harbor Builder; 002 = clear_recommendation: Harbor Builder; 003 = clear_recommendation: Harbor Builder.

### Case 8: Candidate excluded by available time

Context: 30 minutes; energy high; social solo; experience challenge.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Finish the full boss encounter | 31 | high | solo | challenge | 5 | 3 | 0 | 7.0 |
| 2 | Clockwork Duel / Play one ranked match | 30 | high | solo | challenge | 3 | 2 | 0 | 7.0 |

All policies: ID 2 eligible.

ID 1 excluded by all policies: Needs 31 minutes; only 30 available.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 2 | 12.5 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 80.0 | - | no gate |
| 002 | 2 | 12.5 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 78.0 | 58.0 | yes |
| 003 | 2 | 12.5 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 78.0 | 58.0 | yes |

Results: v0.1 = Clockwork Duel; 002 = clear_recommendation: Clockwork Duel; 003 = clear_recommendation: Clockwork Duel.

### Case 9: Candidate excluded by solo/social requirements

Context: 45 minutes; energy medium; social social; experience progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Harbor Builder / Upgrade the solo town | 45 | medium | solo | progression | 5 | 3 | 0 | 7.0 |
| 2 | Starship Crew / Complete a co-op expedition | 45 | medium | social | progression | 4 | 2 | 1 | 7.0 |
| 3 | Trail Partners / Restore the shared campsite | 30 | low | both | progression | 3 | 2 | 0 | 7.0 |

All policies: ID 2 eligible. ID 3 eligible.

ID 1 excluded by all policies: Activity is solo-only; preference is social.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | -2.0 | 0 | 84.25 | - | no gate |
| v0.1 | 3 | 12.5 | 7.5 | 10.0 | 15.0 | 10 | 20 | 0.0 | 0 | 75.0 | - | no gate |
| 002 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | -2.0 | 0 | 82.25 | 58.0 | yes |
| 002 | 3 | 12.5 | 7.5 | 10 | 30 | - | 20 | 0.0 | 0 | 80.0 | 60 | yes |
| 003 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | -2.0 | 0 | 82.25 | 58.0 | yes |
| 003 | 3 | 12.5 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 80.0 | 60.0 | yes |

Results: v0.1 = Starship Crew; 002 = multiple_equivalent: Starship Crew, Trail Partners; 003 = multiple_equivalent: Starship Crew, Trail Partners.

### Case 10: Multiple conflicting factors

Context: 60 minutes; energy medium; social either; experience novelty.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Starship Crew / Explore the new nebula | 60 | high | social | challenge, novelty | 5 | 3 | 4 | 0.0 |
| 2 | Quiet Cartographer / Explore the desert atlas | 40 | low | solo | chill, novelty | 3 | 2 | 0 | 7.0 |
| 3 | Harbor Builder / Complete the harbor expansion | 60 | medium | solo | progression | 4 | 3 | 1 | 3.5 |

All policies: ID 2 eligible. ID 1 eligible. ID 3 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 2 | 12.5 | 7.5 | 10.0 | 15.0 | 10 | 20 | 0.0 | 0 | 75.0 | - | no gate |
| v0.1 | 1 | 25.0 | 15.0 | 15.0 | 7.5 | 10 | 20 | -8.0 | -10.0 | 74.5 | - | no gate |
| v0.1 | 3 | 18.75 | 15.0 | 15.0 | 15.0 | 10 | 0 | -2.0 | -5.0 | 66.75 | - | no gate |
| 002 | 2 | 12.5 | 7.5 | 10 | 30 | - | 20 | 0.0 | 0 | 80.0 | 60 | yes |
| 002 | 1 | 25.0 | 15.0 | 8.0 | 15.0 | - | 20 | -8.0 | -3.0 | 72.0 | 43.0 | yes |
| 002 | 3 | 18.75 | 15.0 | 8.0 | 30 | - | 0 | -2.0 | -1.5 | 68.25 | 38.0 | yes |
| 003 | 2 | 12.5 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 80.0 | 60.0 | yes |
| 003 | 1 | 25.0 | 15.0 | 8.0 | 15.0 | - | 20 | -8.0 | -3.0 | 72.0 | 43.0 | yes |
| 003 | 3 | 18.75 | 15.0 | 8.0 | 30 | - | 0 | -2.0 | -1.5 | 68.25 | 38.0 | yes |

Results: v0.1 = Quiet Cartographer; 002 = clear_recommendation: Quiet Cartographer; 003 = clear_recommendation: Quiet Cartographer.

### Case 11: Supplement: exact tie and stable order

Context: 30 minutes; energy low; social solo; experience chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 2 | Quiet Cartographer / Sketch the river bend | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |
| 1 | Moonlit Orchard / Harvest the river plot | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |

All policies: ID 1 eligible. ID 2 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| v0.1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| 002 | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 002 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 003 | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 003 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |

Results: v0.1 = Moonlit Orchard; 002 = multiple_equivalent: Moonlit Orchard, Quiet Cartographer; 003 = multiple_equivalent: Moonlit Orchard, Quiet Cartographer.

### Case 12: Supplement: negative-score eligible candidate

Context: 60 minutes; energy low; social solo; experience chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Do a one-minute combat drill | 1 | high | solo | challenge | 1 | 1 | 5 | 0.0 |

All policies: ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 0.0 | 0.0 | 0.25 | 0.0 | 10 | 0 | -10.0 | -10.0 | -9.75 | - | no gate |
| 002 | 1 | 0.0 | 0.0 | 10 | 0 | - | 0 | -10.0 | -3.0 | -3.0 | 10 | no |

002 ID 1 remains eligible but fails acceptance: Situational suitability 10 is below 25. Total score -3.0 is below 50.
| 003 | 1 | 0.0 | 0.0 | 0.3333333333333333 | 0 | - | 0 | -10.0 | -3.0 | -12.666666666666666 | 0.3333333333333333 | no |

003 ID 1 remains eligible but fails acceptance: Situational suitability 0.3333333333333333 is below 25. Total score -12.666666666666666 is below 50.

Results: v0.1 = Iron Summit; 002 = no_good_fit; 003 = no_good_fit.

### Case 13: Supplement: no eligible candidate

Context: 15 minutes; energy low; social solo; experience chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Starship Crew / Complete a co-op expedition | 30 | medium | social | progression | 5 | 3 | 0 | 7.0 |

All policies: no eligible candidates.

ID 1 excluded by all policies: Needs 30 minutes; only 15 available. Activity is social-only; preference is solo.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |

Results: v0.1 = no_eligible; 002 = no_eligible; 003 = no_eligible.

### Case 14: Energy mismatch favorite still possible

Context: 30 minutes; energy low; social solo; experience progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Train the new combat skill | 30 | high | solo | progression | 5 | 3 | 0 | 7.0 |
| 2 | Moonlit Orchard / Grow a basic crop | 30 | low | solo | progression | 1 | 1 | 0 | 7.0 |

All policies: ID 1 eligible. ID 2 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 20 | 0.0 | 0 | 85.0 | - | no gate |
| v0.1 | 2 | 0.0 | 0.0 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 60.0 | - | no gate |
| 002 | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 20 | 0.0 | 0 | 68.0 | 28.0 | yes |
| 002 | 2 | 0.0 | 0.0 | 8.0 | 30 | - | 20 | 0.0 | 0 | 58.0 | 58.0 | yes |
| 003 | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 20 | 0.0 | 0 | 68.0 | 28.0 | yes |
| 003 | 2 | 0.0 | 0.0 | 8.0 | 30 | - | 20 | 0.0 | 0 | 58.0 | 58.0 | yes |

Results: v0.1 = Iron Summit; 002 = clear_recommendation: Iron Summit; 003 = clear_recommendation: Iron Summit.

### Case 15: Time buffer band boundary

Context: 30 minutes; energy medium; social solo; experience progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Forest Foundry / Build the workshop | 28 | medium | solo | progression | 4 | 2 | 0 | 7.0 |
| 2 | Harbor Builder / Build the dock | 27 | medium | solo | progression | 4 | 2 | 0 | 7.0 |

All policies: ID 1 eligible. ID 2 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 18.75 | 7.5 | 14.0 | 15.0 | 10 | 20 | 0.0 | 0 | 85.25 | - | no gate |
| v0.1 | 2 | 18.75 | 7.5 | 13.5 | 15.0 | 10 | 20 | 0.0 | 0 | 84.75 | - | no gate |
| 002 | 2 | 18.75 | 7.5 | 10 | 30 | - | 20 | 0.0 | 0 | 86.25 | 60 | yes |
| 002 | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 003 | 2 | 18.75 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 86.25 | 60.0 | yes |
| 003 | 1 | 18.75 | 7.5 | 9.333333333333334 | 30 | - | 20 | 0.0 | 0 | 85.58333333333334 | 59.333333333333336 | yes |

Results: v0.1 = Forest Foundry; 002 = multiple_equivalent: Harbor Builder, Forest Foundry; 003 = multiple_equivalent: Harbor Builder, Forest Foundry.

### Case 16: Very short goal in a long window

Context: 120 minutes; energy low; social solo; experience chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Water one plant | 1 | low | solo | chill | 4 | 2 | 0 | 7.0 |
| 2 | Quiet Cartographer / Map the whole forest | 90 | low | solo | chill | 4 | 2 | 0 | 7.0 |

All policies: ID 2 eligible. ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 2 | 18.75 | 7.5 | 11.25 | 15.0 | 10 | 20 | 0.0 | 0 | 82.5 | - | no gate |
| v0.1 | 1 | 18.75 | 7.5 | 0.125 | 15.0 | 10 | 20 | 0.0 | 0 | 71.375 | - | no gate |
| 002 | 1 | 18.75 | 7.5 | 10 | 30 | - | 20 | 0.0 | 0 | 86.25 | 60 | yes |
| 002 | 2 | 18.75 | 7.5 | 10 | 30 | - | 20 | 0.0 | 0 | 86.25 | 60 | yes |
| 003 | 2 | 18.75 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 86.25 | 60.0 | yes |
| 003 | 1 | 18.75 | 7.5 | 0.16666666666666666 | 30 | - | 20 | 0.0 | 0 | 76.41666666666667 | 50.16666666666667 | yes |

Results: v0.1 = Quiet Cartographer; 002 = multiple_equivalent: Moonlit Orchard, Quiet Cartographer; 003 = clear_recommendation: Quiet Cartographer.

### Case 17: Recent-play ordering with equal interest

Context: 30 minutes; energy low; social solo; experience chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Harvest the orchard | 30 | low | solo | chill | 4 | 2 | 0 | 0.0 |
| 2 | Quiet Cartographer / Map the orchard trail | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |

All policies: ID 2 eligible. ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| v0.1 | 1 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | -10.0 | 76.25 | - | no gate |
| 002 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 002 | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | -3.0 | 81.25 | 58.0 | yes |
| 003 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 003 | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | -3.0 | 81.25 | 58.0 | yes |

Results: v0.1 = Quiet Cartographer; 002 = multiple_equivalent: Quiet Cartographer, Moonlit Orchard; 003 = multiple_equivalent: Quiet Cartographer, Moonlit Orchard.

### Case 18: Total threshold across priority step

Context: 30 minutes; energy low; social solo; experience challenge.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Complete a peaceful chore | 30 | low | solo | chill | 1 | 2 | 0 | 7.0 |
| 2 | Quiet Cartographer / Finish the peaceful atlas | 30 | low | solo | chill | 1 | 3 | 0 | 7.0 |

All policies: ID 2 eligible. ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 2 | 0.0 | 15.0 | 15.0 | 15.0 | 10 | 0 | 0.0 | 0 | 55.0 | - | no gate |
| v0.1 | 1 | 0.0 | 7.5 | 15.0 | 15.0 | 10 | 0 | 0.0 | 0 | 47.5 | - | no gate |
| 002 | 2 | 0.0 | 15.0 | 8.0 | 30 | - | 0 | 0.0 | 0 | 53.0 | 38.0 | yes |
| 002 | 1 | 0.0 | 7.5 | 8.0 | 30 | - | 0 | 0.0 | 0 | 45.5 | 38.0 | no |

002 ID 1 remains eligible but fails acceptance: Total score 45.5 is below 50.
| 003 | 2 | 0.0 | 15.0 | 8.0 | 30 | - | 0 | 0.0 | 0 | 53.0 | 38.0 | yes |
| 003 | 1 | 0.0 | 7.5 | 8.0 | 30 | - | 0 | 0.0 | 0 | 45.5 | 38.0 | no |

003 ID 1 remains eligible but fails acceptance: Total score 45.5 is below 50.

Results: v0.1 = Quiet Cartographer; 002 = clear_recommendation: Quiet Cartographer; 003 = clear_recommendation: Quiet Cartographer.

### Case 19: Suitability gate rejects a high-total mismatch

Context: 30 minutes; energy low; social solo; experience chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Fight the boss again | 30 | high | solo | challenge | 5 | 3 | 0 | 7.0 |

All policies: ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 0 | 0.0 | 0 | 65.0 | - | no gate |
| 002 | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | no |

002 ID 1 remains eligible but fails acceptance: Situational suitability 8.0 is below 25. Total score 48.0 is below 50.
| 003 | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | no |

003 ID 1 remains eligible but fails acceptance: Situational suitability 8.0 is below 25. Total score 48.0 is below 50.

Results: v0.1 = Iron Summit; 002 = no_good_fit; 003 = no_good_fit.

### Case 20: Suitability boundary offset -1

Context: 1000 minutes; energy low; social solo; experience progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Practice the progression drill | 249 | high | solo | progression | 5 | 3 | 0 | 7.0 |

All policies: ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 25.0 | 15.0 | 3.735 | 0.0 | 10 | 20 | 0.0 | 0 | 73.735 | - | no gate |
| 002 | 1 | 25.0 | 15.0 | 10 | 0 | - | 20 | 0.0 | 0 | 70.0 | 30 | yes |
| 003 | 1 | 25.0 | 15.0 | 4.98 | 0 | - | 20 | 0.0 | 0 | 64.98 | 24.98 | no |

003 ID 1 remains eligible but fails acceptance: Situational suitability 24.98 is below 25.

Results: v0.1 = Iron Summit; 002 = clear_recommendation: Iron Summit; 003 = no_good_fit.

### Case 21: Total boundary offset -1

Context: 1000 minutes; energy low; social solo; experience challenge.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Finish the harvest | 249 | low | solo | chill | 1 | 3 | 0 | 7.0 |

All policies: ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 0.0 | 15.0 | 3.735 | 15.0 | 10 | 0 | 0.0 | 0 | 43.735 | - | no gate |
| 002 | 1 | 0.0 | 15.0 | 10 | 30 | - | 0 | 0.0 | 0 | 55.0 | 40 | yes |
| 003 | 1 | 0.0 | 15.0 | 4.98 | 30 | - | 0 | 0.0 | 0 | 49.980000000000004 | 34.980000000000004 | no |

003 ID 1 remains eligible but fails acceptance: Total score 49.980000000000004 is below 50.

Results: v0.1 = Moonlit Orchard; 002 = clear_recommendation: Moonlit Orchard; 003 = no_good_fit.

### Case 22: Near-tie boundary offset -1

Context: 1000 minutes; energy low; social solo; experience chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Harvest the orchard | 500 | low | solo | chill | 5 | 3 | 0 | 7.0 |
| 2 | Quiet Cartographer / Map the orchard trail | 349 | low | solo | chill | 5 | 3 | 0 | 7.0 |

All policies: ID 1 eligible. ID 2 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 25.0 | 15.0 | 7.5 | 15.0 | 10 | 20 | 0.0 | 0 | 92.5 | - | no gate |
| v0.1 | 2 | 25.0 | 15.0 | 5.234999999999999 | 15.0 | 10 | 20 | 0.0 | 0 | 90.235 | - | no gate |
| 002 | 1 | 25.0 | 15.0 | 10 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60 | yes |
| 002 | 2 | 25.0 | 15.0 | 10 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60 | yes |
| 003 | 1 | 25.0 | 15.0 | 10.0 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60.0 | yes |
| 003 | 2 | 25.0 | 15.0 | 6.98 | 30 | - | 20 | 0.0 | 0 | 96.98 | 56.980000000000004 | yes |

Results: v0.1 = Moonlit Orchard; 002 = multiple_equivalent: Moonlit Orchard, Quiet Cartographer; 003 = clear_recommendation: Moonlit Orchard.

### Case 23: Suitability boundary offset 0

Context: 1000 minutes; energy low; social solo; experience progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Practice the progression drill | 250 | high | solo | progression | 5 | 3 | 0 | 7.0 |

All policies: ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 25.0 | 15.0 | 3.75 | 0.0 | 10 | 20 | 0.0 | 0 | 73.75 | - | no gate |
| 002 | 1 | 25.0 | 15.0 | 10 | 0 | - | 20 | 0.0 | 0 | 70.0 | 30 | yes |
| 003 | 1 | 25.0 | 15.0 | 5.0 | 0 | - | 20 | 0.0 | 0 | 65.0 | 25.0 | yes |

Results: v0.1 = Iron Summit; 002 = clear_recommendation: Iron Summit; 003 = clear_recommendation: Iron Summit.

### Case 24: Total boundary offset 0

Context: 1000 minutes; energy low; social solo; experience challenge.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Finish the harvest | 250 | low | solo | chill | 1 | 3 | 0 | 7.0 |

All policies: ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 0.0 | 15.0 | 3.75 | 15.0 | 10 | 0 | 0.0 | 0 | 43.75 | - | no gate |
| 002 | 1 | 0.0 | 15.0 | 10 | 30 | - | 0 | 0.0 | 0 | 55.0 | 40 | yes |
| 003 | 1 | 0.0 | 15.0 | 5.0 | 30 | - | 0 | 0.0 | 0 | 50.0 | 35.0 | yes |

Results: v0.1 = Moonlit Orchard; 002 = clear_recommendation: Moonlit Orchard; 003 = clear_recommendation: Moonlit Orchard.

### Case 25: Near-tie boundary offset 0

Context: 1000 minutes; energy low; social solo; experience chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Harvest the orchard | 500 | low | solo | chill | 5 | 3 | 0 | 7.0 |
| 2 | Quiet Cartographer / Map the orchard trail | 350 | low | solo | chill | 5 | 3 | 0 | 7.0 |

All policies: ID 1 eligible. ID 2 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 25.0 | 15.0 | 7.5 | 15.0 | 10 | 20 | 0.0 | 0 | 92.5 | - | no gate |
| v0.1 | 2 | 25.0 | 15.0 | 5.25 | 15.0 | 10 | 20 | 0.0 | 0 | 90.25 | - | no gate |
| 002 | 1 | 25.0 | 15.0 | 10 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60 | yes |
| 002 | 2 | 25.0 | 15.0 | 10 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60 | yes |
| 003 | 1 | 25.0 | 15.0 | 10.0 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60.0 | yes |
| 003 | 2 | 25.0 | 15.0 | 7.0 | 30 | - | 20 | 0.0 | 0 | 97.0 | 57.0 | yes |

Results: v0.1 = Moonlit Orchard; 002 = multiple_equivalent: Moonlit Orchard, Quiet Cartographer; 003 = multiple_equivalent: Moonlit Orchard, Quiet Cartographer.

### Case 26: Suitability boundary offset 1

Context: 1000 minutes; energy low; social solo; experience progression.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Practice the progression drill | 251 | high | solo | progression | 5 | 3 | 0 | 7.0 |

All policies: ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 25.0 | 15.0 | 3.765 | 0.0 | 10 | 20 | 0.0 | 0 | 73.765 | - | no gate |
| 002 | 1 | 25.0 | 15.0 | 10 | 0 | - | 20 | 0.0 | 0 | 70.0 | 30 | yes |
| 003 | 1 | 25.0 | 15.0 | 5.02 | 0 | - | 20 | 0.0 | 0 | 65.02 | 25.02 | yes |

Results: v0.1 = Iron Summit; 002 = clear_recommendation: Iron Summit; 003 = clear_recommendation: Iron Summit.

### Case 27: Total boundary offset 1

Context: 1000 minutes; energy low; social solo; experience challenge.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Finish the harvest | 251 | low | solo | chill | 1 | 3 | 0 | 7.0 |

All policies: ID 1 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 0.0 | 15.0 | 3.765 | 15.0 | 10 | 0 | 0.0 | 0 | 43.765 | - | no gate |
| 002 | 1 | 0.0 | 15.0 | 10 | 30 | - | 0 | 0.0 | 0 | 55.0 | 40 | yes |
| 003 | 1 | 0.0 | 15.0 | 5.02 | 30 | - | 0 | 0.0 | 0 | 50.019999999999996 | 35.019999999999996 | yes |

Results: v0.1 = Moonlit Orchard; 002 = clear_recommendation: Moonlit Orchard; 003 = clear_recommendation: Moonlit Orchard.

### Case 28: Near-tie boundary offset 1

Context: 1000 minutes; energy low; social solo; experience chill.

| ID | Game / goal | Minutes | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Harvest the orchard | 500 | low | solo | chill | 5 | 3 | 0 | 7.0 |
| 2 | Quiet Cartographer / Map the orchard trail | 351 | low | solo | chill | 5 | 3 | 0 | 7.0 |

All policies: ID 1 eligible. ID 2 eligible.

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v0.1 | 1 | 25.0 | 15.0 | 7.5 | 15.0 | 10 | 20 | 0.0 | 0 | 92.5 | - | no gate |
| v0.1 | 2 | 25.0 | 15.0 | 5.265 | 15.0 | 10 | 20 | 0.0 | 0 | 90.265 | - | no gate |
| 002 | 1 | 25.0 | 15.0 | 10 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60 | yes |
| 002 | 2 | 25.0 | 15.0 | 10 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60 | yes |
| 003 | 1 | 25.0 | 15.0 | 10.0 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60.0 | yes |
| 003 | 2 | 25.0 | 15.0 | 7.02 | 30 | - | 20 | 0.0 | 0 | 97.02 | 57.019999999999996 | yes |

Results: v0.1 = Moonlit Orchard; 002 = multiple_equivalent: Moonlit Orchard, Quiet Cartographer; 003 = multiple_equivalent: Moonlit Orchard, Quiet Cartographer.


## 9. Improvements

- The 90-minute goal clearly outranks the one-minute goal with all other factors equal.
- The 90% scoring cliff becomes a continuous decline; the preferred region remains broad without requiring full-window use.
- Every non-time factor object is asserted equal to its 002 counterpart in all 28 comparisons.
- All four outcomes, additive explanation arithmetic, and deterministic ordering remain intact.

## 10. Regressions and tradeoffs

No new recommendation-set regression appeared in the 19 historical cases, but this hand-designed suite is limited. Short useful goals lose credit and can newly fail acceptance in the immediate-below-threshold probes. A 15-minute goal in two hours earns only 2.5 time points, expressing utilization rather than value or repeatability. Users intentionally wanting a tiny task may disagree with that preference. Relative buffer represents different actual minutes per window; setup time and duration uncertainty remain unknown. A continuous slope can still cross a categorical gate.

## 11. Remaining weaknesses

Threshold calibration and the acceptance/suitability label remain unresolved. Continuation intent, social readiness, per-goal experience variation, and enjoyment evidence are absent. Binary experience match jumps 20 points. High energy still does not itself favor demanding activities. Subjective estimates can affect ranks; near ties retain ID bias for exact totals. Full-window favorites can still win despite less buffer, intentionally.

## 12. Questions requiring human judgment

1. Accept the linear 50-90% plateau and gradual decline to 8 at full time, or prefer another evaluated curve?
2. Should very short tasks remain viable when other factors strongly favor them, even with weak time credit?
3. Should preference/priority help decide abstention, or only rank situationally acceptable candidates? This is the principal unresolved policy question.
4. Are near-tie labels acceptable as presentation conventions, without claiming confidence?
5. Accept 25/50 gates as provisional desirability rules, or run a focused acceptance-policy comparison?

## 13. Recommendation

**Perform another narrowly scoped experiment before selecting the V0.1 replacement; retain production v0.1 meanwhile.** Experiment 003 is the preferred duration candidate for any future proposal. Adopting 002 retains a demonstrated duration regression. Adopting all of 003 now carries forward the demonstrated preference-versus-suitability ambiguity and unreviewed acceptance cliffs.

No broad weight redesign is needed. Obtain human judgment on whether low preference should cause abstention, then compare the current gates with a simpler acceptance rule while keeping this duration function and unrelated weights fixed. If the user explicitly accepts the gates as provisional desirability rules, 003 is a reasonable V0.1 candidate without another duration experiment. Neither experiment was adopted during this task.

## 14. Tests, reproducibility, and immutable provenance

Python 3.12.6; pytest 8.4.2. Commands executed from backend:

`.venv/Scripts/python.exe -m pytest tests/test_scoring.py -q`

```text
..................................................................       [100%]
66 passed in 0.13s
```

`.venv/Scripts/python.exe -m pytest tests/test_policy_002.py -q`

```text
.........................                                                [100%]
25 passed in 0.10s
```

`.venv/Scripts/python.exe -m pytest tests/test_policy_003.py -q`

```text
............................................                             [100%]
44 passed in 0.17s
```


**135 passed: 66 baseline + 25 unchanged Experiment 002 + 44 Experiment 003.** Tests cover all 34 duration points, alternative curves/exclusions, adjacent-minute bounds, frozen factors, repeatability/reversed order, exact breakdown arithmetic, boundary decisions, historical hashes, and the duration fix.

An initial new-test failure was an exact decimal-versus-float expectation (49.980000000000004 vs 49.98); only the new test expectation was corrected to approximate comparison. No scoring or decision thresholds were changed to satisfy it.

Replay: `.venv/Scripts/python.exe -m experiments.comparison_003` prints all inputs, factors, three-policy results, and the alternative curve matrix as JSON, without writing reports. All three alternative curves were evaluated on 34 duration points; only selected A was integrated into the 28 full recommendation comparisons.

Protected SHA-256 values, verified unchanged before and after evaluation:
- `backend/app/scoring.py`: `e0bee04c7f81a53b1881a8777d689bd08bb337155fdf4675702af4fc4d7e87fe`.
- `backend/examples/evaluation_001.py`: `b6a3b4635a643a0fc7428901dd0084e3ffc072edf82a007530d8e25ae5015ab7`.
- `backend/experiments/policy_002.py`: `9e50f8e33c69cddc852e06229cc22291ca0c7329c40c1ecc586676ccfe3c28a4`.
- `backend/experiments/comparison_002.py`: `01a3bd05472851578c6290614d8a2ef9f3299b65b97b6f81949a810fa87d5b3e`.
- `backend/tests/test_scoring.py`: `6da8fc310ca49b924e457479025b94b712b6228afb4088373ccac0eaa86aa2e0`.
- `backend/tests/test_policy_002.py`: `dc1d9e94f25eda7f2ed085944cca0cb1ed02c43c0152c378b0798ba5c15db227`.
- `reports/001_milestone_1_engine_evaluation.md`: `321498eabc0741db9eac22988981bbc3e7ec948035369c732f0c1777b7b299bb`.
- `reports/002_scoring_policy_experiment.md`: `100799e3a6df1d49614a3321d84a5add048fcab5b6f327135ab3543d2596f7aa`.

New source/test hashes:

- `backend/experiments/policy_003.py`: `a1d587cd9dc98a9644c38ab2e25ee8e4d2d1eed8ff3fc6821f7203da2746b73b`.
- `backend/experiments/comparison_003.py`: `d4f9811047ce0936206caa00b5e2781829c3da91f3ea4a4f8e88997bfc55fee7`.
- `backend/tests/test_policy_003.py`: `da89a768ae590a6793b466d6ba93f6ccd5e2aad471896be656259351c8e5dd2a`.

Created those three files and this report; updated only the mutable reports index among existing files. Repeats or corrections require report 004 or the next available number referencing this historical record.
