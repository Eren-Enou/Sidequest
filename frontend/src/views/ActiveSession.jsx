import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { ErrorNotice } from "../components/UI.jsx";
import SessionEvidence from "../components/SessionEvidence.jsx";
import FinishForm from "../forms/FinishForm.jsx";

export function elapsedSeconds(startedAt, now = Date.now()) {
  return Math.max(0, Math.floor((now - new Date(startedAt).getTime()) / 1000));
}

export default function ActiveSession({ session, onFinished, refreshActive }) {
  const [now, setNow] = useState(Date.now());
  const [finishing, setFinishing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(false);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const elapsed = elapsedSeconds(session.started_at, now);
  async function finish(body) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      onFinished(await api.finish(session.id, body));
    } catch (e) {
      setError(e.message);
      // A lost response or another tab may have finished it. Read the saved result;
      // never assume success or repeat a write with different completion data.
      try {
        const saved = await api.session(session.id);
        if (saved.finished_at) {
          onFinished(
            saved,
            "This Sidequest was already recorded. Showing the saved result.",
          );
          return;
        }
      } catch {
        /* The original error remains useful if recovery also fails. */
      }
      await refreshActive();
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <span className="eyebrow">Your active Sidequest</span>
        <h1>{session.game_title_snapshot}</h1>
        <p className="active-goal">{session.goal_title_snapshot}</p>
      </div>
      <div className="session-grid">
        <section className="panel">
          <span className="eyebrow">In progress</span>
          <h2>
            {Math.floor(elapsed / 60)}m {elapsed % 60}s elapsed
          </h2>
          <p>Started {new Date(session.started_at).toLocaleString()}</p>
          <p className="quiet">
            Elapsed time is a guide. You’ll confirm actual play time when you
            finish.
          </p>
          <ErrorNotice message={error} />
          {finishing ? (
            <FinishForm
              suggestedMinutes={Math.max(1, Math.round(elapsed / 60))}
              onSubmit={finish}
              onCancel={() => {
                setFinishing(false);
                setError("");
              }}
              busy={busy}
            />
          ) : (
            <button
              className="primary"
              onClick={() => {
                setNow(Date.now());
                setFinishing(true);
              }}
            >
              Finish Sidequest
            </button>
          )}
        </section>
        <section className="panel">
          <SessionEvidence session={session} />
        </section>
      </div>
    </>
  );
}
