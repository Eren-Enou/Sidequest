# Experiment and report index

Numbered reports are immutable historical records. Never overwrite an earlier report, including a prior uncommitted experiment. Allocate the next number greater than every existing numbered report; never reuse a number. Repeat experiments and corrections use a new report referencing earlier evidence. Update this index whenever a report is added. Once committed, do not rewrite a report to represent a later experiment. Do not use a repeatedly overwritten generic report.md.

Dates use America/Los_Angeles; engine evaluation timestamps are specified within each report.

| Number | Title | Date | Milestone | Purpose | Outcome/status |
| --- | --- | --- | --- | --- | --- |
| 001 | [Milestone 1 engine evaluation](001_milestone_1_engine_evaluation.md) | 2026-10-03 | 1 | Observe the unchanged engine across realistic situational conflicts and boundary cases before tuning. | Complete: 66 tests passed; 13 scenarios evaluated; technical baseline ready to freeze subject to human policy review; weights unchanged. |
| 002 | [Recommendation scoring policy comparison](002_scoring_policy_experiment.md) | 2026-10-03 | 1 policy investigation | Compare a separate revised policy against all 13 baseline scenarios and six discriminating cases. | Complete: 66 baseline + 25 experimental tests passed; 19 comparisons; recommend another experiment; baseline unchanged. |
| 003 | [Duration-fit and suitability-boundary refinement](003_duration_and_threshold_experiment.md) | 2026-10-03 | 1 policy investigation | Compare three duration curves, preserve 002 non-time choices, and probe acceptance/equivalence boundaries. | Complete: 135 tests passed; 19 historical + 9 boundary comparisons and 34 duration matrix points; duration regression fixed; recommend focused acceptance-policy review/experiment before adoption. |
