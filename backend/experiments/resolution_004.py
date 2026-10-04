"""Verify suitability-only acceptance before and after production promotion.

The proposal changes only the acceptance predicate of Experiment 003. Earlier
policies are replayed through a frozen baseline so later promotion cannot alter
the meaning of historical comparisons. This module never writes reports.
"""

from dataclasses import asdict, replace
import json

from examples.evaluation_001 import EVALUATED_AT, candidate
from experiments.comparison_003 import compare, DURATION_MATRIX
from app.scoring import SessionContext
from experiments.policy_003 import recommend as previous
from experiments.policy_002 import POLICY


def proposal(candidates, context, *, evaluated_at):
    old = previous(candidates, context, evaluated_at=evaluated_at)
    ranked = tuple(replace(a, unsuitable_reasons=(() if a.suitability >= POLICY.minimum_suitability else
                        (f"Situational suitability {a.suitability} is below {POLICY.minimum_suitability}.",)))
                   for a in old.ranked)
    suitable = [a for a in ranked if a.suitable]
    choices = tuple(a for a in suitable if suitable[0].scored.score - a.scored.score <= POLICY.near_tie_margin)
    status = ("no_eligible" if not ranked else "no_good_fit" if not suitable else
              "multiple_equivalent" if len(choices) > 1 else "clear_recommendation")
    return replace(old, ranked=ranked, recommendations=choices, status=status, version="resolution-004")


def verify():
    rows = []
    for s,b,p2,p3 in compare():
        final = proposal(s.candidates, s.context, evaluated_at=EVALUATED_AT)
        assert final == proposal(reversed(s.candidates), s.context, evaluated_at=EVALUATED_AT)
        assert final.excluded == b.excluded
        assert all(a.suitable == (a.suitability >= POLICY.minimum_suitability) for a in final.ranked)
        assert all(a.scored == old.scored for a,old in zip(final.ranked,p3.ranked))
        rows.append((s,b,p2,p3,final))
    return tuple(rows)


def verify_durations():
    rows = []
    for available, estimates in DURATION_MATRIX.items():
        for estimate in estimates:
            c = candidate(1,"Duration Test","Complete the session goal",estimate,"low",["chill"],4,2,0,7)
            context = SessionContext(available,"low","solo","chill")
            result = proposal([c],context,evaluated_at=EVALUATED_AT)
            assert bool(result.ranked) == (estimate <= available)
            rows.append((available,estimate,result))
    return tuple(rows)


if __name__ == "__main__":
    print(json.dumps({"comparisons": [{"scenario": asdict(s),"baseline": asdict(b),"002": asdict(p2),
                                      "003": asdict(p3),"final": asdict(final)}
                                     for s,b,p2,p3,final in verify()],
                      "durations": [{"available":a,"estimate":e,"result":asdict(r)}
                                    for a,e,r in verify_durations()]}, indent=2, default=str))
