from dataclasses import asdict, replace

import pytest

from app.scoring import recommend, MINIMUM_SUITABILITY, NEAR_TIE_MARGIN, ENGINE_VERSION
from examples.evaluation_001 import EVALUATED_AT
from experiments.resolution_004 import verify, verify_durations


@pytest.mark.parametrize("index", range(28))
def test_production_matches_preverified_proposal(index):
    s,b,p2,p3,proposal = verify()[index]
    result = recommend(s.candidates,s.context,evaluated_at=EVALUATED_AT)
    assert result.status == proposal.status
    assert [asdict(x) for x in result.excluded] == [asdict(x) for x in proposal.excluded]
    assert [x.candidate for x in result.recommendations] == [a.scored.candidate for a in proposal.recommendations]
    for item, old in zip(result.ranked,proposal.ranked):
        assert item.candidate == old.scored.candidate
        assert item.breakdown == old.scored.breakdown
        assert item.suitability == old.suitability
        assert item.suitable == old.suitable
        assert item.score == sum(item.breakdown.values())
    assert result == recommend(reversed(s.candidates),s.context,evaluated_at=EVALUATED_AT)


def test_all_duration_probes_match_final_proposal():
    from examples.evaluation_001 import candidate
    from app.scoring import SessionContext
    for available,estimate,old in verify_durations():
        c=candidate(1,"Duration Test","Complete the session goal",estimate,"low",["chill"],4,2,0,7)
        result=recommend([c],SessionContext(available,"low","solo","chill"),evaluated_at=EVALUATED_AT)
        assert result.status == old.status
        assert [asdict(x) for x in result.excluded] == [asdict(x) for x in old.excluded]
        if result.winner:
            assert result.winner.breakdown == old.winner.scored.breakdown


@pytest.mark.parametrize("changes", [
    {"interest":1}, {"interest":5}, {"goal_priority":1}, {"goal_priority":3},
    {"friction":5}, {"last_completed_session_at":EVALUATED_AT},
])
def test_preference_and_costs_never_change_suitability(changes):
    s=verify()[0][0]
    c=s.candidates[0]
    original=recommend([c],s.context,evaluated_at=EVALUATED_AT).ranked[0]
    altered=recommend([replace(c,**changes)],s.context,evaluated_at=EVALUATED_AT).ranked[0]
    assert original.suitability == altered.suitability
    assert original.suitable == altered.suitable


def test_removed_total_gate_and_priority_only_orders():
    s=verify()[17][0]
    result=recommend(s.candidates,s.context,evaluated_at=EVALUATED_AT)
    assert all(x.suitable for x in result.ranked)
    assert [x.suitability for x in result.ranked] == [38,38]
    assert result.ranked[1].score == 45.5
    assert result.ranked[1].unsuitable_reasons == ()
    assert result.winner.candidate.goal_id == 2
    below=verify()[20][0]
    assert recommend(below.candidates,below.context,evaluated_at=EVALUATED_AT).status == "clear_recommendation"


def test_suitability_gate_still_abstains_and_metadata_explains_policy():
    s=verify()[19][0]  # Suitability 24.98, despite a high total.
    result=recommend(s.candidates,s.context,evaluated_at=EVALUATED_AT)
    assert result.status == "no_good_fit"
    assert result.winner is None
    assert result.ranked[0].score > 50
    assert result.ranked[0].unsuitable_reasons
    assert result.minimum_suitability == MINIMUM_SUITABILITY == 25
    assert result.near_tie_margin == NEAR_TIE_MARGIN == 3
    assert result.engine_version == ENGINE_VERSION == "v0.1-final-004"


def test_unsuitable_high_total_cannot_beat_suitable_low_total():
    from examples.evaluation_001 import candidate
    from app.scoring import SessionContext
    bad=candidate(1,"Summit","Training",6,"high",["progression"],5,3,0,7)
    good=candidate(2,"Garden","Harvest",30,"low",["chill"],1,1,0,7)
    result=recommend([bad,good],SessionContext(30,"low","solo","progression"),evaluated_at=EVALUATED_AT)
    assert result.ranked[0].candidate == bad  # Eligible audit ranking retains every score.
    assert result.ranked[0].score == 64
    assert not result.ranked[0].suitable
    assert result.winner.candidate == good
    assert result.winner.score == 38
