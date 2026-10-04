const names = {
  interest: "Current interest",
  goal_priority: "Quest priority",
  time_fit: "Time fit",
  energy_fit: "Energy fit",
  experience_fit: "Experience match",
  friction: "Getting started",
  recent_play: "Recent play",
};
const number = (value) =>
  new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value);

export function WhyThis({ item }) {
  return (
    <details className="why">
      <summary>Why this? See all score factors</summary>
      <dl className="factor-list">
        {item.factors.map((factor) => (
          <div key={factor.name} className="factor">
            <dt>{names[factor.name] || factor.name}</dt>
            <dd className={factor.points < 0 ? "negative" : "positive"}>
              {factor.points > 0 ? "+" : ""}
              {number(factor.points)} points
            </dd>
            <p>{factor.reason}</p>
            <small>
              {Object.entries(factor.inputs)
                .map(
                  ([key, value]) =>
                    `${key === "friction" ? "getting-started effort" : key === "estimated_minutes" ? "useful session minutes" : key.replaceAll("_", " ")}: ${Array.isArray(value) ? value.join(", ") : (value ?? "none")}`,
                )
                .join(" · ")}
            </small>
          </div>
        ))}
      </dl>
    </details>
  );
}

export default function Recommendation({ result, selectedId, onSelect }) {
  if (!result)
    return (
      <div className="empty-result">
        <span className="eyebrow">Your next sidequest</span>
        <h2>Make room for a good session.</h2>
        <p>
          Tell us what you have time and energy for. We’ll find a quest in your
          library and show you how it fits.
        </p>
        <p className="quiet">
          Each game needs an active goal to be recommended.
        </p>
      </div>
    );
  const equivalent = result.status === "multiple_equivalent";
  const accepted = result.status === "clear_recommendation" || equivalent;
  return (
    <section aria-label="Recommendation result">
      <span className="eyebrow">
        {accepted ? "Your next sidequest" : "Let’s adjust the plan"}
      </span>
      <h2>
        {equivalent
          ? "A few equally good choices."
          : accepted
            ? "Here’s your next quest."
            : result.status === "no_good_fit"
              ? "Available, but not a good fit."
              : "No quest fits this session yet."}
      </h2>
      {equivalent && (
        <p>
          These choices are essentially equivalent. Pick the one you feel like
          playing.
        </p>
      )}
      {result.status === "no_good_fit" && (
        <p>
          Sidequest found available activities, but none fit your current
          situation well enough. Try changing your energy or desired experience,
          or add a different goal.
        </p>
      )}
      {result.status === "no_eligible" && (
        <p>
          Nothing can currently be recommended. Try more time, a different
          social preference, or add an active goal to a game in your library.
        </p>
      )}
      {accepted && (
        <div className="choices">
          {result.recommendations.map((item) => (
            <article
              key={item.candidate.goal_id}
              className={`choice ${selectedId === item.candidate.goal_id ? "selected" : ""}`}
            >
              {equivalent && (
                <label className="choice-radio">
                  <input
                    type="radio"
                    name="recommendation-choice"
                    checked={selectedId === item.candidate.goal_id}
                    onChange={() => onSelect(item.candidate.goal_id)}
                  />
                  Choose {item.candidate.game_title} —{" "}
                  {item.candidate.goal_title}
                </label>
              )}
              <span className="game-name">{item.candidate.game_title}</span>
              <h3>{item.candidate.goal_title}</h3>
              <div className="tags">
                <span>{item.candidate.estimated_minutes} min quest</span>
                <span>{item.candidate.energy_required} energy</span>
                <span>
                  {item.candidate.social_mode === "both"
                    ? "solo or social"
                    : item.candidate.social_mode}
                </span>
              </div>
              <div className="scores">
                <div>
                  <span>Recommendation score</span>
                  <strong>
                    {number(item.score)} <small>points</small>
                  </strong>
                </div>
                <div>
                  <span>Situational suitability</span>
                  <strong>
                    {number(item.suitability)} <small>points</small>
                  </strong>
                </div>
              </div>
              <p className="quiet">
                Fits the current session according to Sidequest’s suitability
                rule.
              </p>
              <WhyThis item={item} />
            </article>
          ))}
        </div>
      )}
      {(result.excluded.length > 0 ||
        result.ranked.some((item) => !item.suitable)) && (
        <details className="audit">
          <summary>Other quests: exclusions and fit details</summary>
          {result.excluded.map((item) => (
            <div key={item.candidate.goal_id}>
              <strong>
                {item.candidate.game_title} — {item.candidate.goal_title}
              </strong>
              <ul>
                {item.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
          ))}
          {result.ranked
            .filter((item) => !item.suitable)
            .map((item) => (
              <div key={item.candidate.goal_id}>
                <strong>
                  {item.candidate.game_title} — {item.candidate.goal_title}
                </strong>
                <p>{item.unsuitable_reasons.join(" ")}</p>
                <WhyThis item={item} />
              </div>
            ))}
        </details>
      )}
      <p className="policy-note">
        {result.engine_version} · Evaluated{" "}
        {new Date(result.evaluated_at).toLocaleString()} · Scores are points,
        not confidence percentages.
      </p>
    </section>
  );
}
