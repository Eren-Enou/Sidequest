# 004: Milestone 1 final policy resolution

Date: 2026-10-03 (America/Los_Angeles). Status: verification succeeded; policy adopted; Milestone 1 complete. Milestone 2 remains unstarted.

References: [001](001_milestone_1_engine_evaluation.md), [002](002_scoring_policy_experiment.md), [003](003_duration_and_threshold_experiment.md). All three reports remain byte-for-byte unchanged.

## Decision and verification before promotion

The user accepted Experiment 003 duration fit and the Experiment 002 improvements, with this explicit pipeline: Eligibility -> Situational Suitability -> Preference Ranking -> Recommendation. Interest and priority may order suitable options but must not define situational suitability. The suitability gate is the sole soft abstention gate; minimum_total is removed.

Before modifying production, `backend/experiments/resolution_004.py` evaluated a proposal changing only Experiment 003's acceptance predicate. It ran all 28 existing comparison fixtures (13 original + six Experiment 002 + nine Experiment 003 boundary probes) and all 34 Experiment 003 duration cases. These cover every distinct scenario introduced in the three prior experiments; overlapping originals are imported once with identical data and clock. The fixed clock remains 2026-10-03T19:00:00+00:00.

No serious regression was found. Relative to Experiment 003, two eligible candidates become accepted:

- Case 18: Moonlit Orchard, suitability 38 and total 45.5, was rejected only because priority was lower. It now qualifies, but the higher-priority alternative still wins by 7.5; the recommendation set is unchanged.
- Case 21: the probe immediately below total 50 has suitability 34.98 and total approximately 49.98. It now receives a clear recommendation. This is the sole changed recommendation outcome among all 28 fixtures and directly matches the user's decision.

Both newly accepted candidates have sufficient energy, feasible time, and no requested-experience match. A missing tag is a soft fit shortfall under the retained policy, not an eligibility rule; their remaining situational factors pass the unchanged heuristic. Lower interest or priority is no longer treated as a reason to abstain. This behavior is intentional, although a user expecting desired experience to be mandatory may disagree. That existing limitation is explicitly retained, not disguised as an improvement.

Negative/trivially poor-fit and severe mismatched cases still yield no_good_fit, and the empty-eligibility scenario still yields no_eligible. The one-minute-versus-90-minute fix, low-energy result, favorite continuation-friendly ranking, friction effect, and near-tie behavior are preserved. No duration case changed acceptance from removing minimum_total. This finite synthetic verification supports the authorized promotion; it does not establish that recommendations maximize enjoyment.

## Final adopted production policy

Production engine: `backend/app/scoring.py`, policy identifier **v0.1-final-004**. This identifier distinguishes the final V0.1 product policy from the earlier v0.1 baseline; it does not begin a new application milestone. Production uses only Python's standard library and never imports experiments, FastAPI, SQLAlchemy, SQLite, or React.

| Factor | Contribution | Role |
| --- | --- | --- |
| interest | 25 * (interest - 1) / 4; range 0-25 | Preference ranking only |
| goal_priority | 15 * (priority - 1) / 2; range 0-15 | Preference ranking only |
| time_fit | 20r below r=0.5; 10 through r=0.9; 10 - 20(r - 0.9) above r=0.9 | Situational suitability and ranking |
| energy_fit | 30 when sufficient; 15 for one-level shortfall; 0 for two-level shortfall | Situational suitability and ranking |
| experience_fit | 20 for requested tag match, otherwise 0 | Situational suitability and ranking |
| friction | -10 * friction / 5; range -10 to 0 | Ranking cost only |
| recent_play | -3 * max(0, 1 - elapsed_days / 7); never played: 0 | Ranking cost only |

Social mode is only eligibility; its previous constant bonus is removed. All seven weights are centralized in immutable ScoringWeights. Default positive maxima total 100. Scores remain additive, unclamped, and unrounded; a raw eligible score can be negative. At default weights accepted candidates have suitability >=25 and at most 13 penalty points, so their ranking total is at least 12. A low total does not veto recommendation.

## Hard eligibility

Exclude archived games, completed/archived goals, goals estimated longer than available minutes, social-only when solo is requested, and solo-only when social is requested. Both-mode accepts either explicit preference; either preference accepts all modes. Exact-window duration remains eligible. Malformed values fail domain validation rather than becoming excluded scores. Excluded records retain every applicable reason and receive no score. Goal IDs must be unique.

No energy hard filter was added. A demanding favorite can still be suitable when the other situational factors meet the gate, as the retained demanding-favorite fixture demonstrates.

## Suitability factors and justification

**Suitability = time_fit + energy_fit + experience_fit.** This subtotal is independent of interest, priority, friction, and recency.

- Time fit describes how the proposed session chunk uses the CURRENT available window, including a gentle preference for slack. It is not the importance of the goal. It assumes the user wants a meaningful session rather than solely a tiny task.
- Energy fit compares the game's requirement with CURRENT capacity. It is a strong soft influence rather than a promise the user cannot handle a demanding game.
- Experience fit compares game tags with the CURRENT requested experience. It is a binary, game-level approximation, not general affection for the game.

Interest is general preference, and priority is goal importance; neither defines current fit. Recency reflects historical repetition and cannot establish continuation intent. Friction describes setup/coordination effort but currently has no units of time or reliable context-specific readiness; under the accepted decision it remains a ranking cost, not an inferred situational veto. Social mode is an explicit feasibility constraint, not a constant suitability bonus. These are deliberate limits of the available data.

## Ranking and recommendation

Suitable candidates are ordered by the total of all seven factors descending, then priority descending, goal ID ascending, and game ID ascending. Keeping suitability points in the total preserves the accepted 002/003 ranking tradeoffs among suitable choices; this is not a preference-only lexicographic ranking. Interest/priority influence rank but never change the suitability predicate.

Eligible audit results retain all scores, including unsuitable candidates, with suitability and reasons. Recommendation choices contain only suitable candidates. An unsuitable candidate with total 64 cannot displace a suitable candidate with total 38; a new production test verifies this distinction. Consumers must use recommendations/winner rather than selecting the top of the audit list.

## Abstention and near ties

- no_eligible: nothing passes hard filtering.
- no_good_fit: eligible candidates exist, but every suitability subtotal is below 25.
- clear_recommendation: one suitable option is within the near-tie band.
- multiple_equivalent: two or more suitable options are within the band.

There is **no minimum_total gate**. Suitability >=25 alone admits candidates to preference ranking. Scores within three points inclusive of the best suitable score form the near-equivalent set. Membership is anchored to that best score, not chained across adjacent pairs. Display order remains deterministic; winner returns the first display choice and does not assert unique superiority for multiple_equivalent.

Results retain version, weights, evaluation timestamp, suitability threshold, near-tie margin, factor inputs/reasons, totals, exclusions, and choices. Timestamps must be timezone aware; normalize evaluation to UTC. Only completed play per game supplies recency. Future last-play timestamps clamp to zero elapsed days. Same data/context/clock produces equal output regardless of input order.

## Duration rule and heuristic boundaries

Let r = estimated_minutes / available_minutes. Ineligible estimates remain unscored.

```text
0 < r < 0.5:       time_fit = 20 * r
0.5 <= r <= 0.9:   time_fit = 10
0.9 < r <= 1:      time_fit = 10 - 20 * (r - 0.9)
```

This continuous ramp/plateau/decline fixes the tiny-task regression while avoiding an exact full-window reward. Rational duration calculations are converted to floats after applying the weight, matching Experiment 003. Factor sums and ranking use raw floats.

**Heuristics, not empirically calibrated measures:** suitability 25, near-tie margin 3, 50-90% comfort range, full-window time multiplier 0.8, energy multipliers, seven-day recency window, and all score weights. No threshold was optimized from synthetic results. The 24.98/25 boundary still changes no_good_fit to a recommendation; the 49.98/50 total boundary no longer changes acceptance. A 2.98/3/3.02 best-score gap still changes near-tie classification. Clear means outside this convention, not high confidence.

## Why Experiment 003 and why remove minimum_total

Experiment 003's linear rule is the simplest of the three evaluated continuous curves, gives meaningful differences for tiny versus substantial tasks, keeps broad equivalence for good durations, and softens the old 90% cliff. It preserves the useful 002 outcomes without the one-minute/90-minute tie. No new duration tuning was needed.

minimum_total is removed because it confounded general preference with current fit. The priority-step fixture directly demonstrates the issue: identical suitability 38 was accepted only with higher priority. The sole changed recommendation in the retained fixtures is the intended below-total probe; poor-fit abstention still works. The user's explicit separation and successful preflight support removing this redundant preference-sensitive acceptance gate.

## Comparison with previous production v0.1 and Experiment 003

The frozen original engine is the actual byte-for-byte production source captured before promotion. Previous reports remain immutable. The compact table covers all 28 scenarios; full input and scoring details follow.

| Case | Previous production v0.1 | Experiment 003 | Final production | Changed from 003? |
| --- | --- | --- | --- | --- |
| 1. Low energy + short session + progression | Iron Summit | clear_recommendation: Moonlit Orchard | clear_recommendation: Moonlit Orchard | No |
| 2. High energy + long session + challenge | Iron Summit | multiple_equivalent: Iron Summit, Clockwork Duel | multiple_equivalent: Iron Summit, Clockwork Duel | No |
| 3. Strong interest in a poor situational fit | Quiet Cartographer | clear_recommendation: Quiet Cartographer | clear_recommendation: Quiet Cartographer | No |
| 4. Lower interest with a perfect situational fit | Moonlit Orchard | clear_recommendation: Moonlit Orchard | clear_recommendation: Moonlit Orchard | No |
| 5. Two nearly identical candidates | Forest Foundry | multiple_equivalent: Harbor Builder, Forest Foundry | multiple_equivalent: Harbor Builder, Forest Foundry | No |
| 6. Recently played favorite versus less-recent alternative | Quiet Cartographer | clear_recommendation: Moonlit Orchard | clear_recommendation: Moonlit Orchard | No |
| 7. High-friction favorite versus low-friction alternative | Harbor Builder | clear_recommendation: Harbor Builder | clear_recommendation: Harbor Builder | No |
| 8. Candidate excluded by available time | Clockwork Duel | clear_recommendation: Clockwork Duel | clear_recommendation: Clockwork Duel | No |
| 9. Candidate excluded by solo/social requirements | Starship Crew | multiple_equivalent: Starship Crew, Trail Partners | multiple_equivalent: Starship Crew, Trail Partners | No |
| 10. Multiple conflicting factors | Quiet Cartographer | clear_recommendation: Quiet Cartographer | clear_recommendation: Quiet Cartographer | No |
| 11. Supplement: exact tie and stable order | Moonlit Orchard | multiple_equivalent: Moonlit Orchard, Quiet Cartographer | multiple_equivalent: Moonlit Orchard, Quiet Cartographer | No |
| 12. Supplement: negative-score eligible candidate | Iron Summit | no_good_fit | no_good_fit | No |
| 13. Supplement: no eligible candidate | no_eligible | no_eligible | no_eligible | No |
| 14. Energy mismatch favorite still possible | Iron Summit | clear_recommendation: Iron Summit | clear_recommendation: Iron Summit | No |
| 15. Time buffer band boundary | Forest Foundry | multiple_equivalent: Harbor Builder, Forest Foundry | multiple_equivalent: Harbor Builder, Forest Foundry | No |
| 16. Very short goal in a long window | Quiet Cartographer | clear_recommendation: Quiet Cartographer | clear_recommendation: Quiet Cartographer | No |
| 17. Recent-play ordering with equal interest | Quiet Cartographer | multiple_equivalent: Quiet Cartographer, Moonlit Orchard | multiple_equivalent: Quiet Cartographer, Moonlit Orchard | No |
| 18. Total threshold across priority step | Quiet Cartographer | clear_recommendation: Quiet Cartographer | clear_recommendation: Quiet Cartographer | No |
| 19. Suitability gate rejects a high-total mismatch | Iron Summit | no_good_fit | no_good_fit | No |
| 20. Suitability boundary offset -1 | Iron Summit | no_good_fit | no_good_fit | No |
| 21. Total boundary offset -1 | Moonlit Orchard | no_good_fit | clear_recommendation: Moonlit Orchard | Yes, intentional total-gate removal |
| 22. Near-tie boundary offset -1 | Moonlit Orchard | clear_recommendation: Moonlit Orchard | clear_recommendation: Moonlit Orchard | No |
| 23. Suitability boundary offset 0 | Iron Summit | clear_recommendation: Iron Summit | clear_recommendation: Iron Summit | No |
| 24. Total boundary offset 0 | Moonlit Orchard | clear_recommendation: Moonlit Orchard | clear_recommendation: Moonlit Orchard | No |
| 25. Near-tie boundary offset 0 | Moonlit Orchard | multiple_equivalent: Moonlit Orchard, Quiet Cartographer | multiple_equivalent: Moonlit Orchard, Quiet Cartographer | No |
| 26. Suitability boundary offset 1 | Iron Summit | clear_recommendation: Iron Summit | clear_recommendation: Iron Summit | No |
| 27. Total boundary offset 1 | Moonlit Orchard | clear_recommendation: Moonlit Orchard | clear_recommendation: Moonlit Orchard | No |
| 28. Near-tie boundary offset 1 | Moonlit Orchard | multiple_equivalent: Moonlit Orchard, Quiet Cartographer | multiple_equivalent: Moonlit Orchard, Quiet Cartographer | No |

## Full fixture scoring record

Inputs are the unchanged scenario objects imported from experiments 001-003; their exact clock is given above. All games/goals are active, game ID equals goal ID, and last play is seven days ago unless the source fixture specifies otherwise. The report lists each original context and candidate identity alongside previous-production, 003, and final raw breakdowns. Suitability is a subtotal, not an extra contribution. Replay JSON includes every candidate field and factor explanation.

### Case 1: Low energy + short session + progression

Context: 20 minutes, low energy, solo, progression.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Upgrade the watering can | 15 | low | solo | chill, progression | 4 | 2 | 1 | 7.0 |
| 2 | Iron Summit / Clear the training arena | 20 | high | solo | challenge, progression | 5 | 3 | 1 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 2 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 20 | -2.0 | 0 | 83.0 | - | no gate |
| old v0.1 | 1 | 18.75 | 7.5 | 11.25 | 15.0 | 10 | 20 | -2.0 | 0 | 80.5 | - | no gate |
| 003 | 1 | 18.75 | 7.5 | 10.0 | 30 | - | 20 | -2.0 | 0 | 84.25 | 60.0 | yes |
| 003 | 2 | 25.0 | 15.0 | 8.0 | 0 | - | 20 | -2.0 | 0 | 66.0 | 28.0 | yes |
| final | 1 | 18.75 | 7.5 | 10.0 | 30 | - | 20 | -2.0 | 0 | 84.25 | 60.0 | yes |
| final | 2 | 25.0 | 15.0 | 8.0 | 0 | - | 20 | -2.0 | 0 | 66.0 | 28.0 | yes |

### Case 2: High energy + long session + challenge

Context: 120 minutes, high energy, solo, challenge.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Conquer the summit boss | 120 | high | solo | challenge | 5 | 3 | 2 | 7.0 |
| 2 | Clockwork Duel / Complete a ranked ladder run | 60 | medium | solo | challenge | 4 | 3 | 0 | 7.0 |
| 3 | Moonlit Orchard / Expand the orchard | 90 | low | solo | chill, progression | 5 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 25.0 | 15.0 | 15.0 | 15.0 | 10 | 20 | -4.0 | 0 | 96.0 | - | no gate |
| old v0.1 | 2 | 18.75 | 15.0 | 7.5 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| old v0.1 | 3 | 25.0 | 15.0 | 11.25 | 15.0 | 10 | 0 | 0.0 | 0 | 76.25 | - | no gate |
| 003 | 1 | 25.0 | 15.0 | 8.0 | 30 | - | 20 | -4.0 | 0 | 94.0 | 58.0 | yes |
| 003 | 2 | 18.75 | 15.0 | 10.0 | 30 | - | 20 | 0.0 | 0 | 93.75 | 60.0 | yes |
| 003 | 3 | 25.0 | 15.0 | 10.0 | 30 | - | 0 | 0.0 | 0 | 80.0 | 40.0 | yes |
| final | 1 | 25.0 | 15.0 | 8.0 | 30 | - | 20 | -4.0 | 0 | 94.0 | 58.0 | yes |
| final | 2 | 18.75 | 15.0 | 10.0 | 30 | - | 20 | 0.0 | 0 | 93.75 | 60.0 | yes |
| final | 3 | 25.0 | 15.0 | 10.0 | 30 | - | 0 | 0.0 | 0 | 80.0 | 40.0 | yes |

### Case 3: Strong interest in a poor situational fit

Context: 30 minutes, low energy, solo, chill.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Practice a boss phase | 30 | high | solo | challenge | 5 | 3 | 0 | 7.0 |
| 2 | Quiet Cartographer / Sketch the lakeside trail | 20 | low | solo | chill | 2 | 2 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 2 | 6.25 | 7.5 | 10.0 | 15.0 | 10 | 20 | 0.0 | 0 | 68.75 | - | no gate |
| old v0.1 | 1 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 0 | 0.0 | 0 | 65.0 | - | no gate |
| 003 | 2 | 6.25 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 73.75 | 60.0 | yes |
| 003 | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | no |
| final | 2 | 6.25 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 73.75 | 60.0 | yes |
| final | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | no |

Final ID 1 remains eligible but unsuitable: Situational suitability 8.0 is below 25.

### Case 4: Lower interest with a perfect situational fit

Context: 30 minutes, low energy, solo, chill.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Finish the evening harvest | 30 | low | solo | chill | 2 | 3 | 0 | 7.0 |
| 2 | Iron Summit / Practice a boss phase | 30 | high | solo | challenge | 5 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 6.25 | 15.0 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 81.25 | - | no gate |
| old v0.1 | 2 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 0 | 0.0 | 0 | 65.0 | - | no gate |
| 003 | 1 | 6.25 | 15.0 | 8.0 | 30 | - | 20 | 0.0 | 0 | 79.25 | 58.0 | yes |
| 003 | 2 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | no |
| final | 1 | 6.25 | 15.0 | 8.0 | 30 | - | 20 | 0.0 | 0 | 79.25 | 58.0 | yes |
| final | 2 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | no |

Final ID 2 remains eligible but unsuitable: Situational suitability 8.0 is below 25.

### Case 5: Two nearly identical candidates

Context: 30 minutes, medium energy, solo, progression.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Harbor Builder / Construct the west pier | 29 | medium | solo | progression | 4 | 2 | 0 | 7.0 |
| 2 | Forest Foundry / Construct the sawmill | 30 | medium | solo | progression | 4 | 2 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| old v0.1 | 1 | 18.75 | 7.5 | 14.5 | 15.0 | 10 | 20 | 0.0 | 0 | 85.75 | - | no gate |
| 003 | 1 | 18.75 | 7.5 | 8.666666666666666 | 30 | - | 20 | 0.0 | 0 | 84.91666666666666 | 58.666666666666664 | yes |
| 003 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| final | 1 | 18.75 | 7.5 | 8.666666666666666 | 30 | - | 20 | 0.0 | 0 | 84.91666666666666 | 58.666666666666664 | yes |
| final | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |

### Case 6: Recently played favorite versus less-recent alternative

Context: 30 minutes, low energy, solo, chill.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Harvest the greenhouse | 30 | low | solo | chill | 5 | 2 | 0 | 0.0 |
| 2 | Quiet Cartographer / Map the old village | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| old v0.1 | 1 | 25.0 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | -10.0 | 82.5 | - | no gate |
| 003 | 1 | 25.0 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | -3.0 | 87.5 | 58.0 | yes |
| 003 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| final | 1 | 25.0 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | -3.0 | 87.5 | 58.0 | yes |
| final | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |

### Case 7: High-friction favorite versus low-friction alternative

Context: 30 minutes, medium energy, solo, progression.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Starship Workshop / Install the engine upgrade | 30 | medium | solo | progression | 5 | 2 | 5 | 7.0 |
| 2 | Harbor Builder / Upgrade the fishing dock | 30 | medium | solo | progression | 4 | 2 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| old v0.1 | 1 | 25.0 | 7.5 | 15.0 | 15.0 | 10 | 20 | -10.0 | 0 | 82.5 | - | no gate |
| 003 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 003 | 1 | 25.0 | 7.5 | 8.0 | 30 | - | 20 | -10.0 | 0 | 80.5 | 58.0 | yes |
| final | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| final | 1 | 25.0 | 7.5 | 8.0 | 30 | - | 20 | -10.0 | 0 | 80.5 | 58.0 | yes |

### Case 8: Candidate excluded by available time

Context: 30 minutes, high energy, solo, challenge.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Finish the full boss encounter | 31 | high | solo | challenge | 5 | 3 | 0 | 7.0 |
| 2 | Clockwork Duel / Play one ranked match | 30 | high | solo | challenge | 3 | 2 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 2 | 12.5 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 80.0 | - | no gate |
| 003 | 2 | 12.5 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 78.0 | 58.0 | yes |
| final | 2 | 12.5 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 78.0 | 58.0 | yes |

ID 1 excluded in all policies: Needs 31 minutes; only 30 available.

### Case 9: Candidate excluded by solo/social requirements

Context: 45 minutes, medium energy, social, progression.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Harbor Builder / Upgrade the solo town | 45 | medium | solo | progression | 5 | 3 | 0 | 7.0 |
| 2 | Starship Crew / Complete a co-op expedition | 45 | medium | social | progression | 4 | 2 | 1 | 7.0 |
| 3 | Trail Partners / Restore the shared campsite | 30 | low | both | progression | 3 | 2 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | -2.0 | 0 | 84.25 | - | no gate |
| old v0.1 | 3 | 12.5 | 7.5 | 10.0 | 15.0 | 10 | 20 | 0.0 | 0 | 75.0 | - | no gate |
| 003 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | -2.0 | 0 | 82.25 | 58.0 | yes |
| 003 | 3 | 12.5 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 80.0 | 60.0 | yes |
| final | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | -2.0 | 0 | 82.25 | 58.0 | yes |
| final | 3 | 12.5 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 80.0 | 60.0 | yes |

ID 1 excluded in all policies: Activity is solo-only; preference is social.

### Case 10: Multiple conflicting factors

Context: 60 minutes, medium energy, either, novelty.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Starship Crew / Explore the new nebula | 60 | high | social | challenge, novelty | 5 | 3 | 4 | 0.0 |
| 2 | Quiet Cartographer / Explore the desert atlas | 40 | low | solo | chill, novelty | 3 | 2 | 0 | 7.0 |
| 3 | Harbor Builder / Complete the harbor expansion | 60 | medium | solo | progression | 4 | 3 | 1 | 3.5 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 2 | 12.5 | 7.5 | 10.0 | 15.0 | 10 | 20 | 0.0 | 0 | 75.0 | - | no gate |
| old v0.1 | 1 | 25.0 | 15.0 | 15.0 | 7.5 | 10 | 20 | -8.0 | -10.0 | 74.5 | - | no gate |
| old v0.1 | 3 | 18.75 | 15.0 | 15.0 | 15.0 | 10 | 0 | -2.0 | -5.0 | 66.75 | - | no gate |
| 003 | 2 | 12.5 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 80.0 | 60.0 | yes |
| 003 | 1 | 25.0 | 15.0 | 8.0 | 15.0 | - | 20 | -8.0 | -3.0 | 72.0 | 43.0 | yes |
| 003 | 3 | 18.75 | 15.0 | 8.0 | 30 | - | 0 | -2.0 | -1.5 | 68.25 | 38.0 | yes |
| final | 2 | 12.5 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 80.0 | 60.0 | yes |
| final | 1 | 25.0 | 15.0 | 8.0 | 15.0 | - | 20 | -8.0 | -3.0 | 72.0 | 43.0 | yes |
| final | 3 | 18.75 | 15.0 | 8.0 | 30 | - | 0 | -2.0 | -1.5 | 68.25 | 38.0 | yes |

### Case 11: Supplement: exact tie and stable order

Context: 30 minutes, low energy, solo, chill.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 2 | Quiet Cartographer / Sketch the river bend | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |
| 1 | Moonlit Orchard / Harvest the river plot | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| old v0.1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| 003 | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 003 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| final | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| final | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |

### Case 12: Supplement: negative-score eligible candidate

Context: 60 minutes, low energy, solo, chill.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Do a one-minute combat drill | 1 | high | solo | challenge | 1 | 1 | 5 | 0.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 0.0 | 0.0 | 0.25 | 0.0 | 10 | 0 | -10.0 | -10.0 | -9.75 | - | no gate |
| 003 | 1 | 0.0 | 0.0 | 0.3333333333333333 | 0 | - | 0 | -10.0 | -3.0 | -12.666666666666666 | 0.3333333333333333 | no |
| final | 1 | 0.0 | 0.0 | 0.3333333333333333 | 0 | - | 0 | -10.0 | -3.0 | -12.666666666666666 | 0.3333333333333333 | no |

Final ID 1 remains eligible but unsuitable: Situational suitability 0.3333333333333333 is below 25.

### Case 13: Supplement: no eligible candidate

Context: 15 minutes, low energy, solo, chill.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Starship Crew / Complete a co-op expedition | 30 | medium | social | progression | 5 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |

ID 1 excluded in all policies: Needs 30 minutes; only 15 available. Activity is social-only; preference is solo.

### Case 14: Energy mismatch favorite still possible

Context: 30 minutes, low energy, solo, progression.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Train the new combat skill | 30 | high | solo | progression | 5 | 3 | 0 | 7.0 |
| 2 | Moonlit Orchard / Grow a basic crop | 30 | low | solo | progression | 1 | 1 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 20 | 0.0 | 0 | 85.0 | - | no gate |
| old v0.1 | 2 | 0.0 | 0.0 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 60.0 | - | no gate |
| 003 | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 20 | 0.0 | 0 | 68.0 | 28.0 | yes |
| 003 | 2 | 0.0 | 0.0 | 8.0 | 30 | - | 20 | 0.0 | 0 | 58.0 | 58.0 | yes |
| final | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 20 | 0.0 | 0 | 68.0 | 28.0 | yes |
| final | 2 | 0.0 | 0.0 | 8.0 | 30 | - | 20 | 0.0 | 0 | 58.0 | 58.0 | yes |

### Case 15: Time buffer band boundary

Context: 30 minutes, medium energy, solo, progression.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Forest Foundry / Build the workshop | 28 | medium | solo | progression | 4 | 2 | 0 | 7.0 |
| 2 | Harbor Builder / Build the dock | 27 | medium | solo | progression | 4 | 2 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 18.75 | 7.5 | 14.0 | 15.0 | 10 | 20 | 0.0 | 0 | 85.25 | - | no gate |
| old v0.1 | 2 | 18.75 | 7.5 | 13.5 | 15.0 | 10 | 20 | 0.0 | 0 | 84.75 | - | no gate |
| 003 | 2 | 18.75 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 86.25 | 60.0 | yes |
| 003 | 1 | 18.75 | 7.5 | 9.333333333333334 | 30 | - | 20 | 0.0 | 0 | 85.58333333333334 | 59.333333333333336 | yes |
| final | 2 | 18.75 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 86.25 | 60.0 | yes |
| final | 1 | 18.75 | 7.5 | 9.333333333333334 | 30 | - | 20 | 0.0 | 0 | 85.58333333333334 | 59.333333333333336 | yes |

### Case 16: Very short goal in a long window

Context: 120 minutes, low energy, solo, chill.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Water one plant | 1 | low | solo | chill | 4 | 2 | 0 | 7.0 |
| 2 | Quiet Cartographer / Map the whole forest | 90 | low | solo | chill | 4 | 2 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 2 | 18.75 | 7.5 | 11.25 | 15.0 | 10 | 20 | 0.0 | 0 | 82.5 | - | no gate |
| old v0.1 | 1 | 18.75 | 7.5 | 0.125 | 15.0 | 10 | 20 | 0.0 | 0 | 71.375 | - | no gate |
| 003 | 2 | 18.75 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 86.25 | 60.0 | yes |
| 003 | 1 | 18.75 | 7.5 | 0.16666666666666666 | 30 | - | 20 | 0.0 | 0 | 76.41666666666667 | 50.16666666666667 | yes |
| final | 2 | 18.75 | 7.5 | 10.0 | 30 | - | 20 | 0.0 | 0 | 86.25 | 60.0 | yes |
| final | 1 | 18.75 | 7.5 | 0.16666666666666666 | 30 | - | 20 | 0.0 | 0 | 76.41666666666667 | 50.16666666666667 | yes |

### Case 17: Recent-play ordering with equal interest

Context: 30 minutes, low energy, solo, chill.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Harvest the orchard | 30 | low | solo | chill | 4 | 2 | 0 | 0.0 |
| 2 | Quiet Cartographer / Map the orchard trail | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 | - | no gate |
| old v0.1 | 1 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | -10.0 | 76.25 | - | no gate |
| 003 | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| 003 | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | -3.0 | 81.25 | 58.0 | yes |
| final | 2 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | 0 | 84.25 | 58.0 | yes |
| final | 1 | 18.75 | 7.5 | 8.0 | 30 | - | 20 | 0.0 | -3.0 | 81.25 | 58.0 | yes |

### Case 18: Total threshold across priority step

Context: 30 minutes, low energy, solo, challenge.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Complete a peaceful chore | 30 | low | solo | chill | 1 | 2 | 0 | 7.0 |
| 2 | Quiet Cartographer / Finish the peaceful atlas | 30 | low | solo | chill | 1 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 2 | 0.0 | 15.0 | 15.0 | 15.0 | 10 | 0 | 0.0 | 0 | 55.0 | - | no gate |
| old v0.1 | 1 | 0.0 | 7.5 | 15.0 | 15.0 | 10 | 0 | 0.0 | 0 | 47.5 | - | no gate |
| 003 | 2 | 0.0 | 15.0 | 8.0 | 30 | - | 0 | 0.0 | 0 | 53.0 | 38.0 | yes |
| 003 | 1 | 0.0 | 7.5 | 8.0 | 30 | - | 0 | 0.0 | 0 | 45.5 | 38.0 | no |
| final | 2 | 0.0 | 15.0 | 8.0 | 30 | - | 0 | 0.0 | 0 | 53.0 | 38.0 | yes |
| final | 1 | 0.0 | 7.5 | 8.0 | 30 | - | 0 | 0.0 | 0 | 45.5 | 38.0 | yes |

### Case 19: Suitability gate rejects a high-total mismatch

Context: 30 minutes, low energy, solo, chill.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Fight the boss again | 30 | high | solo | challenge | 5 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 0 | 0.0 | 0 | 65.0 | - | no gate |
| 003 | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | no |
| final | 1 | 25.0 | 15.0 | 8.0 | 0 | - | 0 | 0.0 | 0 | 48.0 | 8.0 | no |

Final ID 1 remains eligible but unsuitable: Situational suitability 8.0 is below 25.

### Case 20: Suitability boundary offset -1

Context: 1000 minutes, low energy, solo, progression.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Practice the progression drill | 249 | high | solo | progression | 5 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 25.0 | 15.0 | 3.735 | 0.0 | 10 | 20 | 0.0 | 0 | 73.735 | - | no gate |
| 003 | 1 | 25.0 | 15.0 | 4.98 | 0 | - | 20 | 0.0 | 0 | 64.98 | 24.98 | no |
| final | 1 | 25.0 | 15.0 | 4.98 | 0 | - | 20 | 0.0 | 0 | 64.98 | 24.98 | no |

Final ID 1 remains eligible but unsuitable: Situational suitability 24.98 is below 25.

### Case 21: Total boundary offset -1

Context: 1000 minutes, low energy, solo, challenge.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Finish the harvest | 249 | low | solo | chill | 1 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 0.0 | 15.0 | 3.735 | 15.0 | 10 | 0 | 0.0 | 0 | 43.735 | - | no gate |
| 003 | 1 | 0.0 | 15.0 | 4.98 | 30 | - | 0 | 0.0 | 0 | 49.980000000000004 | 34.980000000000004 | no |
| final | 1 | 0.0 | 15.0 | 4.98 | 30 | - | 0 | 0.0 | 0 | 49.980000000000004 | 34.980000000000004 | yes |

### Case 22: Near-tie boundary offset -1

Context: 1000 minutes, low energy, solo, chill.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Harvest the orchard | 500 | low | solo | chill | 5 | 3 | 0 | 7.0 |
| 2 | Quiet Cartographer / Map the orchard trail | 349 | low | solo | chill | 5 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 25.0 | 15.0 | 7.5 | 15.0 | 10 | 20 | 0.0 | 0 | 92.5 | - | no gate |
| old v0.1 | 2 | 25.0 | 15.0 | 5.234999999999999 | 15.0 | 10 | 20 | 0.0 | 0 | 90.235 | - | no gate |
| 003 | 1 | 25.0 | 15.0 | 10.0 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60.0 | yes |
| 003 | 2 | 25.0 | 15.0 | 6.98 | 30 | - | 20 | 0.0 | 0 | 96.98 | 56.980000000000004 | yes |
| final | 1 | 25.0 | 15.0 | 10.0 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60.0 | yes |
| final | 2 | 25.0 | 15.0 | 6.98 | 30 | - | 20 | 0.0 | 0 | 96.98 | 56.980000000000004 | yes |

### Case 23: Suitability boundary offset 0

Context: 1000 minutes, low energy, solo, progression.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Practice the progression drill | 250 | high | solo | progression | 5 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 25.0 | 15.0 | 3.75 | 0.0 | 10 | 20 | 0.0 | 0 | 73.75 | - | no gate |
| 003 | 1 | 25.0 | 15.0 | 5.0 | 0 | - | 20 | 0.0 | 0 | 65.0 | 25.0 | yes |
| final | 1 | 25.0 | 15.0 | 5.0 | 0 | - | 20 | 0.0 | 0 | 65.0 | 25.0 | yes |

### Case 24: Total boundary offset 0

Context: 1000 minutes, low energy, solo, challenge.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Finish the harvest | 250 | low | solo | chill | 1 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 0.0 | 15.0 | 3.75 | 15.0 | 10 | 0 | 0.0 | 0 | 43.75 | - | no gate |
| 003 | 1 | 0.0 | 15.0 | 5.0 | 30 | - | 0 | 0.0 | 0 | 50.0 | 35.0 | yes |
| final | 1 | 0.0 | 15.0 | 5.0 | 30 | - | 0 | 0.0 | 0 | 50.0 | 35.0 | yes |

### Case 25: Near-tie boundary offset 0

Context: 1000 minutes, low energy, solo, chill.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Harvest the orchard | 500 | low | solo | chill | 5 | 3 | 0 | 7.0 |
| 2 | Quiet Cartographer / Map the orchard trail | 350 | low | solo | chill | 5 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 25.0 | 15.0 | 7.5 | 15.0 | 10 | 20 | 0.0 | 0 | 92.5 | - | no gate |
| old v0.1 | 2 | 25.0 | 15.0 | 5.25 | 15.0 | 10 | 20 | 0.0 | 0 | 90.25 | - | no gate |
| 003 | 1 | 25.0 | 15.0 | 10.0 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60.0 | yes |
| 003 | 2 | 25.0 | 15.0 | 7.0 | 30 | - | 20 | 0.0 | 0 | 97.0 | 57.0 | yes |
| final | 1 | 25.0 | 15.0 | 10.0 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60.0 | yes |
| final | 2 | 25.0 | 15.0 | 7.0 | 30 | - | 20 | 0.0 | 0 | 97.0 | 57.0 | yes |

### Case 26: Suitability boundary offset 1

Context: 1000 minutes, low energy, solo, progression.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit / Practice the progression drill | 251 | high | solo | progression | 5 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 25.0 | 15.0 | 3.765 | 0.0 | 10 | 20 | 0.0 | 0 | 73.765 | - | no gate |
| 003 | 1 | 25.0 | 15.0 | 5.02 | 0 | - | 20 | 0.0 | 0 | 65.02 | 25.02 | yes |
| final | 1 | 25.0 | 15.0 | 5.02 | 0 | - | 20 | 0.0 | 0 | 65.02 | 25.02 | yes |

### Case 27: Total boundary offset 1

Context: 1000 minutes, low energy, solo, challenge.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Finish the harvest | 251 | low | solo | chill | 1 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 0.0 | 15.0 | 3.765 | 15.0 | 10 | 0 | 0.0 | 0 | 43.765 | - | no gate |
| 003 | 1 | 0.0 | 15.0 | 5.02 | 30 | - | 0 | 0.0 | 0 | 50.019999999999996 | 35.019999999999996 | yes |
| final | 1 | 0.0 | 15.0 | 5.02 | 30 | - | 0 | 0.0 | 0 | 50.019999999999996 | 35.019999999999996 | yes |

### Case 28: Near-tie boundary offset 1

Context: 1000 minutes, low energy, solo, chill.

| ID | Game / goal | Estimate | Energy | Mode | Tags | Interest | Priority | Friction | Last play days |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard / Harvest the orchard | 500 | low | solo | chill | 5 | 3 | 0 | 7.0 |
| 2 | Quiet Cartographer / Map the orchard trail | 351 | low | solo | chill | 5 | 3 | 0 | 7.0 |

| Policy | ID | Interest | Priority | Time | Energy | Social | Experience | Friction | Recent | Total | Suitability | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| old v0.1 | 1 | 25.0 | 15.0 | 7.5 | 15.0 | 10 | 20 | 0.0 | 0 | 92.5 | - | no gate |
| old v0.1 | 2 | 25.0 | 15.0 | 5.265 | 15.0 | 10 | 20 | 0.0 | 0 | 90.265 | - | no gate |
| 003 | 1 | 25.0 | 15.0 | 10.0 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60.0 | yes |
| 003 | 2 | 25.0 | 15.0 | 7.02 | 30 | - | 20 | 0.0 | 0 | 97.02 | 57.019999999999996 | yes |
| final | 1 | 25.0 | 15.0 | 10.0 | 30 | - | 20 | 0.0 | 0 | 100.0 | 60.0 | yes |
| final | 2 | 25.0 | 15.0 | 7.02 | 30 | - | 20 | 0.0 | 0 | 97.02 | 57.019999999999996 | yes |

## Duration matrix verification

All 34 inherited duration inputs were checked before promotion. All 31 eligible duration candidates remain accepted with the suitability-only gate; the three estimates one minute over their windows remain excluded. Production is checked against the verified proposal for every entry.

| Available | Estimate | Final time contribution | Final outcome |
| ---: | ---: | ---: | --- |
| 30 | 1 | 0.6666666666666666 | clear_recommendation |
| 30 | 5 | 3.3333333333333335 | clear_recommendation |
| 30 | 10 | 6.666666666666667 | clear_recommendation |
| 30 | 15 | 10.0 | clear_recommendation |
| 30 | 20 | 10.0 | clear_recommendation |
| 30 | 25 | 10.0 | clear_recommendation |
| 30 | 27 | 10.0 | clear_recommendation |
| 30 | 28 | 9.333333333333334 | clear_recommendation |
| 30 | 29 | 8.666666666666666 | clear_recommendation |
| 30 | 30 | 8.0 | clear_recommendation |
| 30 | 31 | - | no_eligible |
| 60 | 1 | 0.3333333333333333 | clear_recommendation |
| 60 | 5 | 1.6666666666666667 | clear_recommendation |
| 60 | 15 | 5.0 | clear_recommendation |
| 60 | 30 | 10.0 | clear_recommendation |
| 60 | 40 | 10.0 | clear_recommendation |
| 60 | 45 | 10.0 | clear_recommendation |
| 60 | 50 | 10.0 | clear_recommendation |
| 60 | 55 | 9.666666666666666 | clear_recommendation |
| 60 | 59 | 8.333333333333334 | clear_recommendation |
| 60 | 60 | 8.0 | clear_recommendation |
| 60 | 61 | - | no_eligible |
| 120 | 1 | 0.16666666666666666 | clear_recommendation |
| 120 | 15 | 2.5 | clear_recommendation |
| 120 | 30 | 5.0 | clear_recommendation |
| 120 | 45 | 7.5 | clear_recommendation |
| 120 | 60 | 10.0 | clear_recommendation |
| 120 | 90 | 10.0 | clear_recommendation |
| 120 | 100 | 10.0 | clear_recommendation |
| 120 | 108 | 10.0 | clear_recommendation |
| 120 | 115 | 8.833333333333334 | clear_recommendation |
| 120 | 119 | 8.166666666666666 | clear_recommendation |
| 120 | 120 | 8.0 | clear_recommendation |
| 120 | 121 | - | no_eligible |


## Known weaknesses

Low-interest options can now be recommended when they are the best available suitable option; this is the intended decision, not hidden by a total threshold. Desired experience remains soft: enough energy/time fit can offset a missing tag. Friction does not consume minutes, social compatibility does not establish friends' availability, and recency cannot identify continuation intent. Tags and energy are game-level approximations. A tiny goal may still qualify if its other situational factors are strong, but loses duration credit when alternatives exist. No user-enjoyment validation has occurred.

The gate and near-tie boundaries remain categorical heuristics. Floating-point summation is unrounded and can show harmless decimal representation artifacts. Equality in score uses deterministic priority/ID ordering and may favor older IDs. No UI or persistence exists yet to communicate these nuances; future implementation must retain the explanations and policy metadata.

## Complete tests and historical replay preservation

The old production source was frozen unchanged into backend/experiments/baseline_001.py before promotion. Its original 66 tests and example were copied into dedicated historical replay files. The original experiment fixture values were not edited. Imports in replay harnesses were redirected to the frozen baseline so comparisons cannot silently change when production evolves. Experiment 002 and 003 numerical rules were not retuned.

The historical hash test now pins the frozen old source instead of the deliberately changed production file, tracks explicit replay adapter changes, and adds Report 003 preservation. Current production expectations were updated to the adopted weights/duration/outcomes; the archived 66 original expectations still pass separately. Cross-module exclusion comparisons use dataclass field values rather than Python class identity. An initial four-test failure was this archived-versus-current class identity distinction, not changed exclusions; those new comparison assertions were corrected without changing behavior.

Final command from backend: `.venv/Scripts/python.exe -m pytest -q`

```text
........................................................................ [ 30%]
........................................................................ [ 60%]
........................................................................ [ 90%]
.......................                                                  [100%]
239 passed in 1.34s
```

**239 passed:** 66 frozen original baseline + 66 adopted production scoring/validation + 25 Experiment 002 + 44 Experiment 003 + 38 final-policy tests. Exit code 0. Final checks compare all 28 fixtures and 34 duration cases with the pre-promotion proposal, verify deterministic reversal, arithmetic, separate eligibility/suitability, preference-independent acceptance, below-50 recommendations, and unsuitable high-total exclusion from choices.

Replay: `.venv/Scripts/python.exe -m experiments.resolution_004` prints historical policies and final proposal JSON without overwriting reports. Production behavior is verified against that proposal by test_final_policy.py. `.venv/Scripts/python.exe -m examples.recommendation` prints a current production example with outcome, suitability, full breakdowns, and explanations.

## Provenance and completion

Historical hashes, verified unchanged before and after final evaluation:

- `reports/001_milestone_1_engine_evaluation.md`: `321498eabc0741db9eac22988981bbc3e7ec948035369c732f0c1777b7b299bb`.
- `reports/002_scoring_policy_experiment.md`: `100799e3a6df1d49614a3321d84a5add048fcab5b6f327135ab3543d2596f7aa`.
- `backend/experiments/baseline_001.py`: `e0bee04c7f81a53b1881a8777d689bd08bb337155fdf4675702af4fc4d7e87fe`.
- `reports/003_duration_and_threshold_experiment.md`: `e6f32387a0c3e2fc412d808b237d9f22f02fab4cba10d2a50660de37c08ef390`.
- Final `backend/app/scoring.py`: `b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a`.
- Final `backend/experiments/resolution_004.py`: `a4763a4fa62ee4473e78543b806b7389977ada188e1bcb33896a10893a720f60`.
- Final `backend/tests/test_final_policy.py`: `7ecac6ba70f82e296cb3be4d27cfb5bd41a343b4f09f4aa64a5695b4fe57ad45`.

Updated PROJECT.md, README.md, IMPLEMENTATION_PLAN.md, current sample/tests, historical replay adapters, and the reports index. Created the frozen baseline/source example/tests, the verification harness, final-policy tests, and this report. No prior report was modified.

**Milestone 1 is complete; v0.1-final-004 is the production V0.1 engine. minimum_total is removed.** Verification found no serious or unexpected historical regression. The single changed recommendation outcome versus 003 is deliberate. Future changes require a new numbered report; Milestone 2 has not begun.
