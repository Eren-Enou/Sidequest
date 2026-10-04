import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { ErrorNotice } from "./components/UI.jsx";
import Library from "./views/Library.jsx";
import Tonight from "./views/Tonight.jsx";

export default function App() {
  const [view, setView] = useState("tonight");
  const [active, setActive] = useState(null);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState("");
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
            aria-current={view === "library" ? "page" : undefined}
            onClick={() => setView("library")}
          >
            Library
          </button>
        </nav>
        <span className="shell-caption">A little time. A good quest.</span>
      </header>
      <main>
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
        ) : (
          <Tonight
            active={active}
            activeUnavailable={checking || Boolean(error)}
            onStarted={setActive}
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
