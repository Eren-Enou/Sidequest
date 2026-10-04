import { WhyThis } from "./Recommendation.jsx";

const number = (value) =>
  new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value);
export function Situation({ context }) {
  const social = { solo: "Solo", social: "Social", either: "Either" };
  return (
    <dl className="session-context">
      <div>
        <dt>Available time</dt>
        <dd>{context.available_minutes} min</dd>
      </div>
      <div>
        <dt>Energy</dt>
        <dd>{context.energy}</dd>
      </div>
      <div>
        <dt>Play preference</dt>
        <dd>{social[context.social_preference]}</dd>
      </div>
      <div>
        <dt>Experience</dt>
        <dd>{context.desired_experience}</dd>
      </div>
    </dl>
  );
}

export default function SessionEvidence({ session }) {
  const { selected, evaluation } = session.recommendation_snapshot;
  return (
    <section aria-label="Saved recommendation">
      <h2>The plan at session start</h2>
      <Situation context={session.situation_snapshot} />
      <div className="scores">
        <div>
          <span>Saved recommendation score</span>
          <strong>
            {number(selected.score)} <small>points</small>
          </strong>
        </div>
        <div>
          <span>Saved suitability</span>
          <strong>
            {number(selected.suitability)} <small>points</small>
          </strong>
        </div>
      </div>
      <WhyThis item={selected} />
      <p className="policy-note">
        Saved at {new Date(evaluation.evaluated_at).toLocaleString()} ·{" "}
        {evaluation.engine_version} · Original session evidence
      </p>
    </section>
  );
}
