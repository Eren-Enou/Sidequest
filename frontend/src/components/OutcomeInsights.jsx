import { useEffect, useState } from "react";
import { api } from "../api.js";
import { ErrorNotice } from "./UI.jsx";

const label = (value) => value ? value[0].toUpperCase() + value.slice(1) : "Not recorded / unavailable";
const countLabel = (count) => `${count} completed ${count === 1 ? "session" : "sessions"}`;

function ContextTable({ title, rows, field }) {
  return (
    <table className="outcome-table">
      <caption>{title}</caption>
      <thead><tr><th scope="col">Recorded context</th><th scope="col">Sessions</th><th scope="col">Average / 5</th></tr></thead>
      <tbody>{rows.map((row) => (
        <tr key={row[field] ?? "unknown"}>
          <th scope="row">{label(row[field])}</th>
          <td>{row.completed_session_count}</td>
          <td>{row.average_enjoyment.toFixed(2)}</td>
        </tr>
      ))}</tbody>
    </table>
  );
}

export default function OutcomeInsights({ gameId }) {
  const [open, setOpen] = useState(false);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!open) return;
    let ignore = false;
    setLoading(true);
    setSummary(null);
    setError("");
    api.outcomes(gameId)
      .then((value) => { if (!ignore) setSummary(value); })
      .catch((failure) => { if (!ignore) setError(failure.message); })
      .finally(() => { if (!ignore) setLoading(false); });
    return () => { ignore = true; };
  }, [gameId, open, revision]);
  return (
    <section className="outcome-insights" aria-label="Session outcome insights">
      <button type="button" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
        {open ? "Hide outcome insights" : "Show outcome insights"}
      </button>
      {open && <>
        <h3>Session outcome insights</h3>
        <p className="quiet">Recorded history, not a prediction. These insights do not affect recommendation ranking.</p>
        {loading && <p role="status">Loading outcome insights…</p>}
        <ErrorNotice message={error} />
        {!loading && <button type="button" onClick={() => setRevision((value) => value + 1)}>
          {error ? "Retry outcome insights" : "Refresh outcome insights"}
        </button>}
        {summary && (summary.completed_session_count === 0 ? (
          <p>No completed session history yet.</p>
        ) : <>
          <p><strong>{countLabel(summary.completed_session_count)}</strong></p>
          <p>Average enjoyment: <strong>{summary.average_enjoyment.toFixed(2)} / 5</strong> across {countLabel(summary.completed_session_count)}.</p>
          <p className="quiet">Averages summarize your 1–5 ratings; the distribution shows their variation.</p>
          <table className="outcome-table">
            <caption>Enjoyment distribution</caption>
            <thead><tr><th scope="col">Rating / 5</th><th scope="col">Sessions</th></tr></thead>
            <tbody>{summary.rating_distribution.map(({ rating, count }) => (
              <tr key={rating}><th scope="row">{rating}</th><td>{count}</td></tr>
            ))}</tbody>
          </table>
          <h4>Recent completed sessions</h4>
          <p className="quiet">Latest {summary.recent_sessions.length} of {countLabel(summary.completed_session_count)}.</p>
          <ul className="outcome-recent">{summary.recent_sessions.map((session) => (
            <li key={session.session_id}>
              <time dateTime={session.finished_at}>{new Date(session.finished_at).toLocaleString()}</time>
              {" · "}<strong>{session.enjoyment_rating} / 5</strong>
              <span className="quiet">{session.goal_title_snapshot} · {label(session.desired_experience)} · {label(session.energy)} energy</span>
            </li>
          ))}</ul>
          <ContextTable title="Desired experience at session start" rows={summary.by_desired_experience} field="desired_experience" />
          <ContextTable title="Energy at session start" rows={summary.by_energy} field="energy" />
          <details className="quiet">
            <summary>About this evidence</summary>
            <p>Each context row includes its session count, even when it contains only one session. Small groups can vary considerably. Context describes the start of the session, not its cause or a forecast.</p>
            <p>Older 3 ratings may have been explicitly chosen or accepted from the previous preselected default. They remain included; we cannot distinguish them retrospectively.</p>
          </details>
        </>)}
      </>}
    </section>
  );
}
