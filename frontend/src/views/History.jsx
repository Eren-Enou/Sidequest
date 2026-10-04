import { useEffect, useState } from "react";
import { api } from "../api.js";
import { ErrorNotice } from "../components/UI.jsx";
import SessionEvidence from "../components/SessionEvidence.jsx";

export default function History({ initialId = null }) {
  const [sessions, setSessions] = useState([]),
    [selected, setSelected] = useState(initialId),
    [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true),
    [detailLoading, setDetailLoading] = useState(false),
    [error, setError] = useState(""),
    [revision, setRevision] = useState(0);
  useEffect(() => {
    let ignore = false;
    setLoading(true);
    setError("");
    api
      .history()
      .then((rows) => {
        if (!ignore) setSessions(rows);
      })
      .catch((e) => {
        if (!ignore) setError(e.message);
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, [revision]);
  useEffect(() => {
    let ignore = false;
    setDetail(null);
    if (!selected) return;
    setDetailLoading(true);
    api
      .session(selected)
      .then((row) => {
        if (!ignore) setDetail(row);
      })
      .catch((e) => {
        if (!ignore) setError(e.message);
      })
      .finally(() => {
        if (!ignore) setDetailLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, [selected, revision]);
  return (
    <>
      <div className="page-heading">
        <span className="eyebrow">History</span>
        <h1>A journal of time well spent.</h1>
        <p>Your sessions, just as they were. A little progress adds up.</p>
      </div>
      <ErrorNotice message={error} />
      {error && (
        <button
          onClick={() => setRevision((value) => value + 1)}
          disabled={loading || detailLoading}
        >
          Retry history
        </button>
      )}
      {loading ? (
        <p role="status">Loading your Sidequests…</p>
      ) : sessions.length === 0 && !error ? (
        <div className="panel empty">
          <h2>No completed Sidequests yet.</h2>
          <p>
            Finish a session and it will appear here with your progress and the
            original recommendation.
          </p>
        </div>
      ) : (
        <div className="history-grid">
          <section aria-label="Completed Sidequests">
            {sessions.map((row) => (
              <article
                className={`panel history-card ${selected === row.id ? "selected" : ""}`}
                key={row.id}
              >
                <span className="eyebrow">
                  {new Date(row.finished_at).toLocaleDateString(undefined, {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </span>
                <span className="game-name">{row.game_title_snapshot}</span>
                <h2>{row.goal_title_snapshot}</h2>
                <p className="quiet">
                  {row.actual_duration_minutes} min played · Enjoyment{" "}
                  {row.enjoyment_rating}/5
                </p>
                <p className="notes">{row.progress}</p>
                <button
                  aria-pressed={selected === row.id}
                  onClick={() => {
                    setSelected(row.id);
                    setError("");
                  }}
                >
                  Inspect {row.goal_title_snapshot}
                </button>
              </article>
            ))}
          </section>
          <section className="panel history-detail" aria-label="Session detail">
            {detailLoading ? (
              <p role="status">Loading saved session…</p>
            ) : detail ? (
              <>
                <span className="eyebrow">Recorded Sidequest</span>
                <h2>{detail.game_title_snapshot}</h2>
                <h3>{detail.goal_title_snapshot}</h3>
                <p>
                  Started {new Date(detail.started_at).toLocaleString()}
                  <br />
                  Finished {new Date(detail.finished_at).toLocaleString()}
                </p>
                <p>
                  {detail.actual_duration_minutes} min played · Enjoyment{" "}
                  {detail.enjoyment_rating}/5
                </p>
                <h3>Progress</h3>
                <p className="notes">{detail.progress}</p>
                <h3>Notes</h3>
                <p className="notes">{detail.notes || "No notes recorded."}</p>
                <SessionEvidence session={detail} />
              </>
            ) : (
              <div className="empty">
                <h2>Pick a Sidequest to look back.</h2>
                <p>
                  Inspect its notes, original situation and saved
                  recommendation.
                </p>
              </div>
            )}
          </section>
        </div>
      )}
    </>
  );
}
