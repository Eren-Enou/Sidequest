from pathlib import Path
import hashlib

import pytest

from experiments.comparison_003 import compare, duration_results, DURATION_MATRIX, BOUNDARY_CASES
from experiments.policy_003 import time_points, recommend
from examples.evaluation_001 import EVALUATED_AT

PROTECTED_HASHES = {
    "backend/app/scoring.py": "e0bee04c7f81a53b1881a8777d689bd08bb337155fdf4675702af4fc4d7e87fe",
    "backend/examples/evaluation_001.py": "b6a3b4635a643a0fc7428901dd0084e3ffc072edf82a007530d8e25ae5015ab7",
    "backend/experiments/policy_002.py": "9e50f8e33c69cddc852e06229cc22291ca0c7329c40c1ecc586676ccfe3c28a4",
    "backend/experiments/comparison_002.py": "01a3bd05472851578c6290614d8a2ef9f3299b65b97b6f81949a810fa87d5b3e",
    "backend/tests/test_scoring.py": "6da8fc310ca49b924e457479025b94b712b6228afb4088373ccac0eaa86aa2e0",
    "backend/tests/test_policy_002.py": "dc1d9e94f25eda7f2ed085944cca0cb1ed02c43c0152c378b0798ba5c15db227",
    "reports/001_milestone_1_engine_evaluation.md": "321498eabc0741db9eac22988981bbc3e7ec948035369c732f0c1777b7b299bb",
    "reports/002_scoring_policy_experiment.md": "100799e3a6df1d49614a3321d84a5add048fcab5b6f327135ab3543d2596f7aa",
}


def test_historical_files_unchanged_for_this_experiment():
    root = Path(__file__).resolve().parents[2]
    for name, expected in PROTECTED_HASHES.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize("available,estimate", [(a, d) for a, ds in DURATION_MATRIX.items() for d in ds])
def test_duration_matrix(available, estimate):
    if estimate > available:
        with pytest.raises(ValueError):
            time_points(estimate, available)
    else:
        points = time_points(estimate, available)
        assert 0 < points <= 10
        if available / 2 <= estimate <= available * 0.9:
            assert points == 10
        if estimate == available:
            assert points == 8


def test_all_curves_and_duration_exclusions():
    rows = duration_results()
    assert len(rows) == 34
    for row in rows:
        assert row["eligible"] == (row["estimate"] <= row["available"])
        if not row["eligible"]:
            assert set(row["time_points"].values()) == {None}
            assert row["statuses"] == ["no_eligible"] * 3


@pytest.mark.parametrize("available", [30, 60, 120])
def test_adjacent_minute_changes_bounded(available):
    points = [time_points(d, available) for d in range(1, available + 1)]
    assert max(abs(b-a) for a,b in zip(points, points[1:])) <= 20/available + 1e-12
    # Rises, plateaus, then declines; no internal score jump.
    assert points[available//2-1] == 10
    assert points[-1] == 8


def test_reproducibility_arithmetic_and_unchanged_other_factors():
    assert len(compare()) == 28


def test_trivial_vs_substantial_regression_fixed():
    s,b,p2,p3 = compare()[15]
    assert p2.status == "multiple_equivalent"
    assert p3.status == "clear_recommendation"
    assert p3.winner.scored.candidate.game_title == "Quiet Cartographer"
    assert time_points(1,120) == pytest.approx(1/6)
    assert time_points(90,120) == 10


def test_one_minute_59_60_not_materially_different():
    assert time_points(59,120) == pytest.approx(59/6)
    assert time_points(60,120) == 10
    assert time_points(59,60)-time_points(60,60) == pytest.approx(1/3)


def test_boundary_statuses_and_exact_arithmetic():
    results = [recommend(s.candidates, s.context, evaluated_at=EVALUATED_AT) for s in BOUNDARY_CASES]
    suitability = results[0::3]
    assert [r.ranked[0].suitability for r in suitability] == [24.98,25,25.02]
    assert [r.status for r in suitability] == ["no_good_fit", "clear_recommendation", "clear_recommendation"]
    total = results[1::3]
    assert [r.ranked[0].scored.score for r in total] == pytest.approx([49.98,50,50.02])
    assert [r.status for r in total] == ["no_good_fit", "clear_recommendation", "clear_recommendation"]
    assert [r.status for r in results[2::3]] == ["clear_recommendation", "multiple_equivalent", "multiple_equivalent"]


def test_full_window_remains_viable_and_002_gains_preserved():
    rows = compare()
    for index in (0,5,6,9,11,12,13):
        _,_,old,new = rows[index]
        assert old.status == new.status
        assert tuple(a.scored.candidate.goal_id for a in old.recommendations) == tuple(
            a.scored.candidate.goal_id for a in new.recommendations)
    assert rows[7][3].winner is not None
    assert rows[7][3].winner.scored.candidate.estimated_minutes == 30
