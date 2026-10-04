# 001: Milestone 1 engine evaluation

Date: 2026-10-03 (America/Los_Angeles). Milestone: 1. Status: evaluation complete; human policy review pending.

## Purpose and method

Observe the existing engine without changing weights or rules. This is a synthetic behavioral evaluation with fictional games, not evidence of actual user enjoyment. Ten requested scenarios plus three supplemental cases isolate tradeoffs, exact ties, negative scores, and empty eligibility. Candidate IDs are local to each independent scenario. All games are unarchived and all goals active. No database, API, frontend, randomness, or LLM was involved.

Every scenario was run through the actual `recommend` function. Repeat runs and reversed input order produced equal result objects in all 13 cases; every eligible score exactly equaled the sum of its raw breakdown values. These are evaluation assertions, separate from the existing pytest suite.

## Engine configuration and scoring weights

- Engine version: `v0.1`.
- Fixed evaluation timestamp: `2026-10-03T19:00:00+00:00` (synthetic reference clock, not a live execution timestamp).
- Python: 3.12.6. pytest: 8.4.2.
- Engine file SHA-256: `e0bee04c7f81a53b1881a8777d689bd08bb337155fdf4675702af4fc4d7e87fe`.
- Frozen fixture SHA-256: `b6a3b4635a643a0fc7428901dd0084e3ffc072edf82a007530d8e25ae5015ab7`.
- No weight overrides were supplied. Raw floating-point values are retained below; scores are points, not probabilities.

| Factor | Weight / maximum | Formula |
| --- | ---: | --- |
| interest | +25 | 25 * (interest - 1) / 4; interest 1-5 |
| goal_priority | +15 | 15 * (priority - 1) / 2; priority 1-3 |
| time_fit | +15 | 15 * estimated_minutes / available_minutes |
| energy_fit | +15 | Required energy at/below context: 15; one level above: 7.5; two above: 0 |
| social_fit | +10 | 10 for every eligible candidate |
| experience_fit | +20 | 20 if desired experience is in game tags, otherwise 0 |
| friction | -10 | -10 * friction / 5; friction 0-5 |
| recent_play | -10 | -10 * max(0, 1 - elapsed_days / 7); never played: 0 |

Elapsed days use UTC elapsed seconds / 86,400; future last-play values clamp to zero elapsed. Only last completed play per game is supplied. Seven days ago and never played have identical recency contributions. Positive maxima total 100. Every eligible candidate earns 10 social points and positive time points, so the default eligible score range is strictly greater than -10 and at most 100. The earlier PROJECT.md claim of a theoretical -20 minimum is an overly loose bound, not an attainable default score. No behavior was changed to address this documentation issue.

Tie rule: raw score descending, priority descending, goal ID ascending, then game ID ascending. Duplicate goal IDs are invalid, making the final game-ID tie key redundant. Exclusions sort by ID; no score is computed for excluded candidates.

## Current eligibility rules

- Exclude archived games and completed/archived goals.
- Exclude estimated minutes greater than available minutes; exact equality is eligible.
- Solo rejects social-only; social rejects solo-only; both-mode accepts either explicit preference; either preference accepts every mode.
- Energy, interest, priority, experience, friction, and recency do not exclude candidates.
- No minimum score or fallback relaxation exists. Empty eligibility returns no winner.
- Malformed values raise validation errors instead of becoming exclusions. IDs/time must be positive integers; ratings/enums/timestamps follow the documented domain constraints.

## Existing test-suite result

Command (from `backend/`): `.venv/Scripts/python.exe -m pytest -q`

```text
..................................................................       [100%]
66 passed in 0.07s
```

Exit code: 0. Tests cover scoring direction/boundaries, time/social filters, inactive records, explanations, deterministic ties, repeatability, validation, timezone behavior, and the original fictional example. No tests or engine code were changed for this evaluation.

## Evaluation scenarios and full scoring results

Input-table legend: interest 1-5; priority 1-3; friction 0-5. Last completed play is expressed as exact elapsed days before the fixed timestamp; never means null. In these fixtures game ID equals goal ID. All omitted lifecycle values are game_archived=false and goal_status=active. Tables list all eight factors in their engine accumulation order; values are unrounded Python representations. Zero penalties may display as -0.0, which equals 0.

### Scenario 1: Low energy + short session + progression

Situation: available_minutes=20; energy=low; social_preference=solo; desired_experience=progression.

| Game/goal ID | Game | Goal | Minutes | Energy | Mode | Experience tags | Interest | Priority | Friction | Last play (days ago) |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard | Upgrade the watering can | 15 | low | solo | chill, progression | 4 | 2 | 1 | 7.0 |
| 2 | Iron Summit | Clear the training arena | 20 | high | solo | challenge, progression | 5 | 3 | 1 | 7.0 |

Eligibility/exclusions:

- ID 2: eligible.
- ID 1: eligible.

| Rank | Goal ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 20 | -2.0 | 0 | 83.0 |
| 2 | 1 | 18.75 | 7.5 | 11.25 | 15.0 | 10 | 20 | -2.0 | 0 | 80.5 |

Winner: **Iron Summit - Clear the training arena**, 83.0 points.

Why: Iron Summit wins: +6.25 interest, +7.5 priority, and +3.75 time fit outweigh its -15 energy-fit disadvantage by 2.5 points.

Surprising/potentially undesirable: A high-energy activity can win in a low-energy context. Energy is soft, so this is policy behavior, not an eligibility bug.

### Scenario 2: High energy + long session + challenge

Situation: available_minutes=120; energy=high; social_preference=solo; desired_experience=challenge.

| Game/goal ID | Game | Goal | Minutes | Energy | Mode | Experience tags | Interest | Priority | Friction | Last play (days ago) |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit | Conquer the summit boss | 120 | high | solo | challenge | 5 | 3 | 2 | 7.0 |
| 2 | Clockwork Duel | Complete a ranked ladder run | 60 | medium | solo | challenge | 4 | 3 | 0 | 7.0 |
| 3 | Moonlit Orchard | Expand the orchard | 90 | low | solo | chill, progression | 5 | 3 | 0 | 7.0 |

Eligibility/exclusions:

- ID 1: eligible.
- ID 2: eligible.
- ID 3: eligible.

| Rank | Goal ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 25.0 | 15.0 | 15.0 | 15.0 | 10 | 20 | -4.0 | 0 | 96.0 |
| 2 | 2 | 18.75 | 15.0 | 7.5 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 |
| 3 | 3 | 25.0 | 15.0 | 11.25 | 15.0 | 10 | 0 | 0.0 | 0 | 76.25 |

Winner: **Iron Summit - Conquer the summit boss**, 96.0 points.

Why: Iron Summit beats Clockwork Duel by 9.75: +6.25 interest and +7.5 time fit offset -4 friction. It beats the orchard by 19.75, principally through the matching challenge tag.

Surprising/potentially undesirable: High energy gives all energy requirements full points. It does not itself favor demanding activities; challenge tags supply that preference.

### Scenario 3: Strong interest in a poor situational fit

Situation: available_minutes=30; energy=low; social_preference=solo; desired_experience=chill.

| Game/goal ID | Game | Goal | Minutes | Energy | Mode | Experience tags | Interest | Priority | Friction | Last play (days ago) |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit | Practice a boss phase | 30 | high | solo | challenge | 5 | 3 | 0 | 7.0 |
| 2 | Quiet Cartographer | Sketch the lakeside trail | 20 | low | solo | chill | 2 | 2 | 0 | 7.0 |

Eligibility/exclusions:

- ID 2: eligible.
- ID 1: eligible.

| Rank | Goal ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | 6.25 | 7.5 | 10.0 | 15.0 | 10 | 20 | 0.0 | 0 | 68.75 |
| 2 | 1 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 0 | 0.0 | 0 | 65.0 |

Winner: **Quiet Cartographer - Sketch the lakeside trail**, 68.75 points.

Why: Quiet Cartographer wins by 3.75. Its +15 energy and +20 experience advantages overcome -18.75 interest, -7.5 priority, and -5 time fit.

Surprising/potentially undesirable: A modest change in priority or recency could reverse this narrow win. Poor fit remains eligible if time and social mode fit.

### Scenario 4: Lower interest with a perfect situational fit

Situation: available_minutes=30; energy=low; social_preference=solo; desired_experience=chill.

| Game/goal ID | Game | Goal | Minutes | Energy | Mode | Experience tags | Interest | Priority | Friction | Last play (days ago) |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard | Finish the evening harvest | 30 | low | solo | chill | 2 | 3 | 0 | 7.0 |
| 2 | Iron Summit | Practice a boss phase | 30 | high | solo | challenge | 5 | 3 | 0 | 7.0 |

Eligibility/exclusions:

- ID 1: eligible.
- ID 2: eligible.

| Rank | Goal ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 6.25 | 15.0 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 81.25 |
| 2 | 2 | 25.0 | 15.0 | 15.0 | 0.0 | 10 | 0 | 0.0 | 0 | 65.0 |

Winner: **Moonlit Orchard - Finish the evening harvest**, 81.25 points.

Why: Moonlit Orchard wins by 16.25: its +35 combined energy/experience advantage exceeds the favorite's +18.75 interest advantage. Both fit the time window exactly.

Surprising/potentially undesirable: Perfect fit does not imply a score of 100: low interest still limits the score. Compare scenario 3 to see how the fitted candidate's priority and duration affect the margin.

### Scenario 5: Two nearly identical candidates

Situation: available_minutes=30; energy=medium; social_preference=solo; desired_experience=progression.

| Game/goal ID | Game | Goal | Minutes | Energy | Mode | Experience tags | Interest | Priority | Friction | Last play (days ago) |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Harbor Builder | Construct the west pier | 29 | medium | solo | progression | 4 | 2 | 0 | 7.0 |
| 2 | Forest Foundry | Construct the sawmill | 30 | medium | solo | progression | 4 | 2 | 0 | 7.0 |

Eligibility/exclusions:

- ID 2: eligible.
- ID 1: eligible.

| Rank | Goal ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 |
| 2 | 1 | 18.75 | 7.5 | 14.5 | 15.0 | 10 | 20 | 0.0 | 0 | 85.75 |

Winner: **Forest Foundry - Construct the sawmill**, 86.25 points.

Why: Forest Foundry wins by 0.5, entirely from the extra estimated minute: 15 versus 14.5 time points. Lower ID does not override a higher score.

Surprising/potentially undesirable: One minute of estimation noise can determine the winner. There is no confidence band or near-tie treatment.

### Scenario 6: Recently played favorite versus less-recent alternative

Situation: available_minutes=30; energy=low; social_preference=solo; desired_experience=chill.

| Game/goal ID | Game | Goal | Minutes | Energy | Mode | Experience tags | Interest | Priority | Friction | Last play (days ago) |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Moonlit Orchard | Harvest the greenhouse | 30 | low | solo | chill | 5 | 2 | 0 | 0.0 |
| 2 | Quiet Cartographer | Map the old village | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |

Eligibility/exclusions:

- ID 2: eligible.
- ID 1: eligible.

| Rank | Goal ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 |
| 2 | 1 | 25.0 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | -10.0 | 82.5 |

Winner: **Quiet Cartographer - Map the old village**, 86.25 points.

Why: Quiet Cartographer wins by 3.75. Avoiding the favorite's -10 recent-play penalty outweighs the favorite's +6.25 interest advantage.

Surprising/potentially undesirable: The engine discourages repeating a favorite even when repetition was enjoyable. Enjoyment and a desire to continue are not inputs.

### Scenario 7: High-friction favorite versus low-friction alternative

Situation: available_minutes=30; energy=medium; social_preference=solo; desired_experience=progression.

| Game/goal ID | Game | Goal | Minutes | Energy | Mode | Experience tags | Interest | Priority | Friction | Last play (days ago) |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Starship Workshop | Install the engine upgrade | 30 | medium | solo | progression | 5 | 2 | 5 | 7.0 |
| 2 | Harbor Builder | Upgrade the fishing dock | 30 | medium | solo | progression | 4 | 2 | 0 | 7.0 |

Eligibility/exclusions:

- ID 2: eligible.
- ID 1: eligible.

| Rank | Goal ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 |
| 2 | 1 | 25.0 | 7.5 | 15.0 | 15.0 | 10 | 20 | -10.0 | 0 | 82.5 |

Winner: **Harbor Builder - Upgrade the fishing dock**, 86.25 points.

Why: Harbor Builder wins by 3.75: avoiding -10 friction outweighs the favorite's +6.25 interest advantage.

Surprising/potentially undesirable: Friction is only a point penalty, not minutes. A 30-minute goal remains eligible in a 30-minute window even with maximum setup friction.

### Scenario 8: Candidate excluded by available time

Situation: available_minutes=30; energy=high; social_preference=solo; desired_experience=challenge.

| Game/goal ID | Game | Goal | Minutes | Energy | Mode | Experience tags | Interest | Priority | Friction | Last play (days ago) |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit | Finish the full boss encounter | 31 | high | solo | challenge | 5 | 3 | 0 | 7.0 |
| 2 | Clockwork Duel | Play one ranked match | 30 | high | solo | challenge | 3 | 2 | 0 | 7.0 |

Eligibility/exclusions:

- ID 2: eligible.
- ID 1: excluded. Needs 31 minutes; only 30 available. Score: not calculated.

| Rank | Goal ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | 12.5 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 80.0 |

Winner: **Clockwork Duel - Play one ranked match**, 80.0 points.

Why: Clockwork Duel is the sole eligible candidate. The 31-minute favorite gets no score; interest and priority cannot override the time filter.

Surprising/potentially undesirable: The cutoff is abrupt at one minute beyond the window, while exact fits have no buffer for setup or overrun.

### Scenario 9: Candidate excluded by solo/social requirements

Situation: available_minutes=45; energy=medium; social_preference=social; desired_experience=progression.

| Game/goal ID | Game | Goal | Minutes | Energy | Mode | Experience tags | Interest | Priority | Friction | Last play (days ago) |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Harbor Builder | Upgrade the solo town | 45 | medium | solo | progression | 5 | 3 | 0 | 7.0 |
| 2 | Starship Crew | Complete a co-op expedition | 45 | medium | social | progression | 4 | 2 | 1 | 7.0 |
| 3 | Trail Partners | Restore the shared campsite | 30 | low | both | progression | 3 | 2 | 0 | 7.0 |

Eligibility/exclusions:

- ID 2: eligible.
- ID 3: eligible.
- ID 1: excluded. Activity is solo-only; preference is social. Score: not calculated.

| Rank | Goal ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | -2.0 | 0 | 84.25 |
| 2 | 3 | 12.5 | 7.5 | 10.0 | 15.0 | 10 | 20 | 0.0 | 0 | 75.0 |

Winner: **Starship Crew - Complete a co-op expedition**, 84.25 points.

Why: The solo-only town goal is excluded. Starship Crew beats Trail Partners by 9.25: +6.25 interest and +5 time fit offset -2 friction. Social-only and both receive identical social points.

Surprising/potentially undesirable: Social compatibility does not establish that friends are available. A both-mode game is not preferred over social-only. Explicit solo rejecting social-only is covered by the existing test matrix.

### Scenario 10: Multiple conflicting factors

Situation: available_minutes=60; energy=medium; social_preference=either; desired_experience=novelty.

| Game/goal ID | Game | Goal | Minutes | Energy | Mode | Experience tags | Interest | Priority | Friction | Last play (days ago) |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Starship Crew | Explore the new nebula | 60 | high | social | challenge, novelty | 5 | 3 | 4 | 0.0 |
| 2 | Quiet Cartographer | Explore the desert atlas | 40 | low | solo | chill, novelty | 3 | 2 | 0 | 7.0 |
| 3 | Harbor Builder | Complete the harbor expansion | 60 | medium | solo | progression | 4 | 3 | 1 | 3.5 |

Eligibility/exclusions:

- ID 2: eligible.
- ID 1: eligible.
- ID 3: eligible.

| Rank | Goal ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | 12.5 | 7.5 | 10.0 | 15.0 | 10 | 20 | 0.0 | 0 | 75.0 |
| 2 | 1 | 25.0 | 15.0 | 15.0 | 7.5 | 10 | 20 | -8.0 | -10.0 | 74.5 |
| 3 | 3 | 18.75 | 15.0 | 15.0 | 15.0 | 10 | 0 | -2.0 | -5.0 | 66.75 |

Winner: **Quiet Cartographer - Explore the desert atlas**, 75.0 points.

Why: Quiet Cartographer wins by 0.5 over Starship Crew. Against the favorite it loses 12.5 interest, 7.5 priority, and 5 time points, but gains 7.5 energy, 8 friction, and 10 recency points. Harbor Builder loses mainly because it lacks novelty.

Surprising/potentially undesirable: A 0.5-point win is mathematically decisive but not strong evidence of better enjoyment. Either permits a social recommendation without any coordination readiness input.

### Scenario 11: Supplement: exact tie and stable order

Situation: available_minutes=30; energy=low; social_preference=solo; desired_experience=chill.

| Game/goal ID | Game | Goal | Minutes | Energy | Mode | Experience tags | Interest | Priority | Friction | Last play (days ago) |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 2 | Quiet Cartographer | Sketch the river bend | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |
| 1 | Moonlit Orchard | Harvest the river plot | 30 | low | solo | chill | 4 | 2 | 0 | 7.0 |

Eligibility/exclusions:

- ID 1: eligible.
- ID 2: eligible.

| Rank | Goal ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 |
| 2 | 2 | 18.75 | 7.5 | 15.0 | 15.0 | 10 | 20 | 0.0 | 0 | 86.25 |

Winner: **Moonlit Orchard - Harvest the river plot**, 86.25 points.

Why: Both score 86.25 and have priority 2. Moonlit Orchard wins only because goal ID 1 precedes ID 2, despite being supplied second.

Surprising/potentially undesirable: An exact tie can systematically favor older IDs. The final game-ID key cannot resolve any additional tie because duplicate goal IDs are rejected.

### Scenario 12: Supplement: negative-score eligible candidate

Situation: available_minutes=60; energy=low; social_preference=solo; desired_experience=chill.

| Game/goal ID | Game | Goal | Minutes | Energy | Mode | Experience tags | Interest | Priority | Friction | Last play (days ago) |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Iron Summit | Do a one-minute combat drill | 1 | high | solo | challenge | 1 | 1 | 5 | 0.0 |

Eligibility/exclusions:

- ID 1: eligible.

| Rank | Goal ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 0.0 | 0.0 | 0.25 | 0.0 | 10 | 0 | -10.0 | -10.0 | -9.75 |

Winner: **Iron Summit - Do a one-minute combat drill**, -9.75 points.

Why: Iron Summit is the sole eligible candidate and wins with -9.75 points: 10 social + 0.25 time - 10 friction - 10 recency. There is no minimum-score gate.

Surprising/potentially undesirable: The engine will recommend an eligible activity despite low apparent suitability. The exact default lower bound is greater than -10, not -20 as the earlier PROJECT.md range suggests, because every eligible candidate earns +10 social points and a strictly positive time contribution.

### Scenario 13: Supplement: no eligible candidate

Situation: available_minutes=15; energy=low; social_preference=solo; desired_experience=chill.

| Game/goal ID | Game | Goal | Minutes | Energy | Mode | Experience tags | Interest | Priority | Friction | Last play (days ago) |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Starship Crew | Complete a co-op expedition | 30 | medium | social | progression | 5 | 3 | 0 | 7.0 |

Eligibility/exclusions:

- ID 1: excluded. Needs 30 minutes; only 15 available. Activity is social-only; preference is solo. Score: not calculated.

| Rank | Goal ID | interest | goal_priority | time_fit | energy_fit | social_fit | experience_fit | friction | recent_play | Total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |

No eligible scores.

Winner: **None**.

Why: No winner is returned. The only candidate has both time and social exclusions; neither is relaxed.

Surprising/potentially undesirable: No best-effort fallback is provided. The future UI must make the exclusions actionable instead of presenting an unexplained empty result.

## Observations

- The hard filters behave consistently: situational impossibility cannot be rescued by interest or priority. All reasons survive when multiple filters fail.
- Situational fit sometimes beats strong interest (scenarios 3-4), but low energy does not guarantee a low-energy winner (scenario 1).
- One interest step is 6.25 points; one priority step is 7.5; one energy shortfall is 7.5; one friction step is 2; experience match is binary at 20. These tradeoffs explain the observed reversals without invoking a defect.
- Recency and friction independently reverse the same 6.25-point interest lead in scenarios 6-7.
- Time fit creates a full-window preference. The shorter near-identical candidate loses by 0.5 in scenario 5.
- The conflict scenario also has a 0.5-point margin. Determinism gives a repeatable answer, not confidence that the winner is meaningfully better.
- No invariant failures were observed. This confirms internal consistency for these fixtures, not broad product usefulness.

## Potential weaknesses discovered

1. Energy shortfall is compensable. A demanding activity can outrank an appropriate activity when the user reports low energy.
2. Estimates and setup: exact fits get maximum time points without slack. Friction does not consume time, and estimated duration uncertainty is ignored.
3. Repetition preference: recency uniformly discourages replay; enjoyment, story continuity, and intentional repeated practice are not represented.
4. Binary experience tags: the 20-point jump is large; broad tags may dominate narrower tagging. Game-level tags may not describe every goal.
5. Social factor is constant after filtering. It affects totals without affecting ranking; both-mode and social-only receive no readiness distinction.
6. Tiny score differences and exact ties: no near-tie policy exists. Older goal IDs can win exact ties without a product reason.
7. Negative winners: an eligible candidate can be recommended with a negative score because there is no suitability threshold. Negative scores need explanation in the eventual UI.
8. Score-range documentation: PROJECT.md states -20 to 100, but default eligible scores are strictly above -10 due to the constant social bonus and positive time term. Record a future correction rather than changing this historical report.
9. Cold start and history: never played and a week-old game get equal recency treatment; caller consistency in supplying per-game completed history is essential. These examples do not evaluate real users or noisy estimates.

## Questions requiring human judgment

1. Is the scenario 1 high-energy winner acceptable when energy is low, or should future policy prioritize energy more strongly? No change is proposed without review.
2. Should time fit reward filling the entire window, or should the eventual product favor spare time for setup and overruns? Are estimates intended to include setup?
3. Should a favorite played today lose to a slightly less interesting alternative, as in scenario 6, even when the user wants to continue it?
4. Is maximum friction worth only 10 points? Is a game-level rating sufficient for situational coordination effort?
5. Should social fit remain a constant explained contribution, and does either really mean social activities are currently feasible?
6. Should near ties be presented as equally reasonable alternatives? Is goal-ID ordering acceptable for exact ties?
7. Is recommending a negative-score winner acceptable, or should a future version offer a no-good-fit outcome?
8. Are game-level binary experience tags accurate enough for goals, or should this be revisited after actual use?

## Recommendation about freezing Milestone 1

**Ready to freeze as the technical v0.1 baseline, subject to explicit human acceptance of the tradeoffs above.** The existing suite passes, explanation arithmetic is consistent, and fixed-input/order checks are deterministic. These experiments expose policy limitations rather than demonstrated algorithm defects. Preserve current weights while reviewing energy, time slack, replay, near ties, and negative-score behavior. Do not interpret a freeze as evidence that weights are optimal or recommendations improve enjoyment. Milestone 2 remains unstarted.

## Reproduction and historical preservation

Frozen inputs: `backend/examples/evaluation_001.py`. From `backend/`, run `.venv/Scripts/python.exe -m examples.evaluation_001` to print current results as JSON (including candidate inputs and factor inputs/reasons). Compare engine/fixture hashes above before expecting identical outputs. The fixture prints results and never writes or overwrites this report. Changing the engine later may change its output.

This is report 001, the first investigation; there is no earlier report. Later repeats, corrections, or tuning experiments must create the next numbered report, reference this record, and update reports/README.md. This historical file must not be overwritten.
