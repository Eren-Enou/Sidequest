import { useRef, useState } from "react";
import { api } from "../api.js";
import {
  energies,
  experiences,
  ErrorNotice,
  Field,
  SelectField,
} from "../components/UI.jsx";
import Recommendation from "../components/Recommendation.jsx";

export default function Tonight({
  active,
  activeUnavailable,
  onStarted,
  refreshActive,
}) {
  const [context, setContext] = useState({
    available_minutes: 45,
    energy: "medium",
    social_preference: "either",
    desired_experience: "progression",
  });
  const [result, setResult] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [stale, setStale] = useState(false);
  const pending = useRef(false);
  function change(key, value) {
    setContext((previous) => ({ ...previous, [key]: value }));
    setResult(null);
    setSelectedId(null);
    setError("");
    setStale(false);
  }
  async function recommend(event) {
    event.preventDefault();
    if (pending.current) return;
    pending.current = true;
    setBusy("recommend");
    setError("");
    try {
      const next = await api.recommend(context);
      setResult(next);
      setSelectedId(next.recommendations[0]?.candidate.goal_id ?? null);
      setStale(false);
    } catch (e) {
      setError(e.message);
      setResult(null);
    } finally {
      pending.current = false;
      setBusy("");
    }
  }
  async function start() {
    const chosen = result?.recommendations.find(
      (item) => item.candidate.goal_id === selectedId,
    );
    if (!chosen || active || activeUnavailable || pending.current || stale)
      return;
    pending.current = true;
    setBusy("start");
    setError("");
    try {
      onStarted(await api.start(chosen.candidate, result.context));
    } catch (e) {
      setError(
        e.status === 409
          ? `${e.message} Refresh your recommendation before trying again.`
          : e.message,
      );
      setStale(true);
      await refreshActive();
    } finally {
      pending.current = false;
      setBusy("");
    }
  }
  return (
    <>
      <div className="page-heading">
        <span className="eyebrow">Tonight</span>
        <h1>
          What should I play
          <br className="desktop-break" /> right now?
        </h1>
        <p>A session that fits your evening. A goal worth picking up.</p>
      </div>
      <div className="tonight-grid">
        <section className="panel situation">
          <h2>Set the scene</h2>
          <form onSubmit={recommend}>
            <fieldset disabled={Boolean(busy)}>
              <Field
                label="Available time"
                hint="Minutes you have for a useful session."
              >
                <input
                  type="number"
                  min="1"
                  step="1"
                  required
                  value={context.available_minutes}
                  onChange={(e) =>
                    change(
                      "available_minutes",
                      e.target.value === "" ? "" : Number(e.target.value),
                    )
                  }
                />
              </Field>
              <SelectField
                label="Your energy"
                value={context.energy}
                onChange={(value) => change("energy", value)}
                options={energies}
              />
              <SelectField
                label="Who’s playing?"
                value={context.social_preference}
                onChange={(value) => change("social_preference", value)}
                options={[
                  ["either", "Either is fine"],
                  ["solo", "Just me"],
                  ["social", "Something social"],
                ]}
              />
              <SelectField
                label="What are you looking for?"
                value={context.desired_experience}
                onChange={(value) => change("desired_experience", value)}
                options={experiences}
              />
            </fieldset>
            <button
              className="primary wide"
              type="submit"
              disabled={Boolean(busy)}
            >
              {busy === "recommend"
                ? "Finding your quest…"
                : stale
                  ? "Refresh recommendation"
                  : "Find my next quest"}
            </button>
          </form>
          <p className="quiet">
            Recommendations use your library and current situation. Every score
            has an explanation.
          </p>
        </section>
        <div className="panel result-panel">
          <ErrorNotice message={error} />
          <Recommendation
            result={result}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          {result?.recommendations.length > 0 && (
            <button
              className="primary wide start-button"
              disabled={
                Boolean(busy) || Boolean(active) || activeUnavailable || stale
              }
              onClick={start}
            >
              {busy === "start"
                ? "Starting session…"
                : active
                  ? "A session is already active"
                  : activeUnavailable
                    ? "Check active session before starting"
                    : "Start selected quest"}
            </button>
          )}
        </div>
      </div>
    </>
  );
}
