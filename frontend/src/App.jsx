import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { ErrorNotice } from "./components/UI.jsx";
import Library from "./views/Library.jsx";
import Tonight from "./views/Tonight.jsx";
import ActiveSession from "./views/ActiveSession.jsx";
import History from "./views/History.jsx";

export default function App() {
  const [view, setView] = useState("tonight");
  const [active, setActive] = useState(null);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState("");
  const [completion, setCompletion] = useState(null);
  const activeRequest = useRef(0);
  const refreshActive = useCallback(async () => {
    const requestId = ++activeRequest.current;
    setChecking(true);
    try {
      const current = await api.active();
      if (requestId === activeRequest.current) {
        setActive(current);
        setError("");
      }
    } catch (e) {
      if (requestId === activeRequest.current) setError(e.message);
    } finally {
      if (requestId === activeRequest.current) setChecking(false);
    }
  }, []);
  useEffect(() => {
    refreshActive();
  }, [refreshActive]);
  function onStarted(row) {
    activeRequest.current++;
    setActive(row);
    setCompletion(null);
    setView("session");
  }
  function onFinished(
    row,
    message = "Sidequest complete. Your progress is saved.",
  ) {
    activeRequest.current++;
    setActive(null);
    setChecking(false);
    setError("");
    setCompletion({ row, message });
    setView("history");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setView("tonight");
          }}
        >
          <span className="brand-mark" aria-hidden="true">
            S
          </span>{" "}
          SIDEQUEST
        </a>
        <nav aria-label="Main navigation">
          <button
            aria-current={view === "tonight" ? "page" : undefined}
            onClick={() => setView("tonight")}
          >
            Tonight
          </button>
          <button
            aria-current={view === "history" ? "page" : undefined}
            onClick={() => setView("history")}
          >
            History
          </button>
          {active && (
            <button
              aria-current={view === "session" ? "page" : undefined}
              onClick={() => setView("session")}
            >
              Active session
            </button>
          )}
          <button
            aria-current={view === "library" ? "page" : undefined}
            onClick={() => setView("library")}
          >
            Library
          </button>
        </nav>
        <span className="shell-caption">A little time. A good quest.</span>
      </header>
      <main>
        {completion && (
          <div className="notice completion-notice" role="status">
            {completion.message}{" "}
            <button
              onClick={() => {
                setView("history");
              }}
            >
              View completed Sidequest
            </button>
            <button
              aria-label="Dismiss completion message"
              onClick={() => setCompletion(null)}
            >
              Dismiss
            </button>
          </div>
        )}
        {checking && (
          <p role="status" className="quiet">
            Checking your active session…
          </p>
        )}
        {error && (
          <div>
            <ErrorNotice message={error} />
            <button onClick={refreshActive} disabled={checking}>
              Retry session check
            </button>
          </div>
        )}
        {active && (
          <aside className="active-banner" role="status">
            <span className="eyebrow">Session active</span>
            <strong>
              {active.game_title_snapshot} <span aria-hidden="true">→</span>{" "}
              {active.goal_title_snapshot}
            </strong>
            <span>
              Started {new Date(active.started_at).toLocaleString()}. Your quest
              is underway.
            </span>
          </aside>
        )}
        {view === "library" ? (
          <Library />
        ) : view === "history" ? (
          <History
            key={completion?.row.id || "history"}
            initialId={completion?.row.id}
          />
        ) : view === "session" ? (
          active ? (
            <ActiveSession
              key={active.id}
              session={active}
              onFinished={onFinished}
              refreshActive={refreshActive}
            />
          ) : (
            <section className="panel">
              <h2>No active Sidequest.</h2>
              <p>Head to Tonight to find your next quest.</p>
              <button onClick={() => setView("tonight")}>Find a quest</button>
            </section>
          )
        ) : (
          <Tonight
            active={active}
            activeUnavailable={checking || Boolean(error)}
            onStarted={onStarted}
            refreshActive={refreshActive}
          />
        )}
      </main>
      <footer>
        YOUR LIBRARY. YOUR PACE.
        <span>Explainable recommendations · Personal & local</span>
      </footer>
    </div>
  );
}
