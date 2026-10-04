import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { ErrorNotice } from "../components/UI.jsx";
import { GameForm, GoalForm } from "../forms/LibraryForms.jsx";
import OutcomeInsights from "../components/OutcomeInsights.jsx";

export default function Library() {
  const [games, setGames] = useState([]),
    [goals, setGoals] = useState([]);
  const [selected, setSelected] = useState(null),
    [showArchived, setShowArchived] = useState(false);
  const [gameEditor, setGameEditor] = useState(null),
    [goalEditor, setGoalEditor] = useState(null);
  const [loading, setLoading] = useState(true),
    [goalsLoading, setGoalsLoading] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const mutation = useRef(false);
  const game = games.find((item) => item.id === selected);
  async function loadGames() {
    setLoading(true);
    try {
      const rows = await api.games();
      setGames(rows);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    loadGames();
  }, []);
  useEffect(() => {
    let ignore = false;
    setGoals([]);
    setGoalEditor(null);
    if (!selected) return;
    setGoalsLoading(true);
    api
      .goals(selected)
      .then((rows) => {
        if (!ignore) setGoals(rows);
      })
      .catch((e) => {
        if (!ignore) setError(e.message);
      })
      .finally(() => {
        if (!ignore) setGoalsLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, [selected]);
  async function mutate(action, after) {
    if (mutation.current) return;
    mutation.current = true;
    setBusy(true);
    setError("");
    let saved = false;
    try {
      const value = await action();
      saved = true;
      await after(value);
    } catch (e) {
      setError(
        saved
          ? `Your change was saved, but refreshing the library failed. Retry library to reload. ${e.message}`
          : e.message,
      );
    } finally {
      mutation.current = false;
      setBusy(false);
    }
  }
  const saveGame = (body, id) =>
    mutate(
      () => api.saveGame(body, id),
      async (row) => {
        setSelected(row.id);
        setGameEditor(null);
        setGames(await api.games());
      },
    );
  const saveGoal = (body, id) =>
    mutate(
      () => api.saveGoal(body, id),
      async () => {
        setGoalEditor(null);
        setGoals(await api.goals(selected));
      },
    );
  const gameAction = () =>
    mutate(
      () =>
        game.archived_at ? api.restoreGame(game.id) : api.archiveGame(game.id),
      async () => {
        setGames(await api.games());
        setGoalEditor(null);
      },
    );
  const goalAction = (id, action) =>
    mutate(
      () => api.goalAction(id, action),
      async () => {
        setGoals(await api.goals(selected));
        setGoalEditor(null);
      },
    );
  const visible = games.filter((item) => showArchived || !item.archived_at);
  async function retryLibrary() {
    await loadGames();
    if (selected) {
      setGoalsLoading(true);
      try {
        setGoals(await api.goals(selected));
      } catch (e) {
        setError(e.message);
      } finally {
        setGoalsLoading(false);
      }
    }
  }
  return (
    <>
      <div className="page-heading library-heading">
        <div>
          <span className="eyebrow">Library</span>
          <h1>Your games. Your quests.</h1>
          <p>Keep a few good things ready for your next session.</p>
        </div>
        <button
          className="primary"
          disabled={busy}
          onClick={() => {
            setGameEditor("new");
            setGoalEditor(null);
          }}
        >
          Add game
        </button>
      </div>
      <ErrorNotice message={error} />
      {error && (
        <button
          onClick={retryLibrary}
          disabled={busy || loading || goalsLoading}
        >
          Retry library
        </button>
      )}
      {gameEditor !== null && (
        <div className="panel">
          <GameForm
            key={gameEditor === "new" ? "new" : gameEditor.id}
            game={gameEditor === "new" ? null : gameEditor}
            onSave={saveGame}
            busy={busy}
            onCancel={() => setGameEditor(null)}
          />
        </div>
      )}
      <div className="library-grid">
        <section className="game-list" aria-label="Games">
          <div className="section-head">
            <h2>
              On your shelf <span className="count">{visible.length}</span>
            </h2>
            <label className="inline-check">
              <input
                type="checkbox"
                checked={showArchived}
                onChange={(e) => setShowArchived(e.target.checked)}
              />
              Show archived
            </label>
          </div>
          {loading ? (
            <p role="status">Loading your library…</p>
          ) : visible.length === 0 ? (
            <div className="panel empty">
              <h3>
                {games.length ? "Your shelf is archived." : "No games yet."}
              </h3>
              <p>
                {games.length
                  ? "Show archived games to restore one."
                  : "Add something you’re currently playing. Then give it a quest to work toward."}
              </p>
            </div>
          ) : (
            visible.map((item) => (
              <button
                key={item.id}
                className={`game-card ${selected === item.id ? "selected" : ""}`}
                aria-label={`${item.archived_at ? "Archived" : `${item.energy_required} energy, ${item.social_mode}`} ${item.title}`}
                aria-pressed={selected === item.id}
                disabled={busy}
                onClick={() => {
                  setSelected(item.id);
                  setGameEditor(null);
                  setError("");
                }}
              >
                <span className="eyebrow">
                  {item.archived_at
                    ? "Archived"
                    : `${item.energy_required} energy · ${item.social_mode === "both" ? "solo or social" : item.social_mode}`}
                </span>
                <strong>{item.title}</strong>
                <span className="tags">
                  {item.experience_tags.map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                </span>
              </button>
            ))
          )}
        </section>
        <section className="panel quest-panel" aria-label="Game quests">
          {!game ? (
            <div className="empty">
              <h2>Pick a game from your shelf.</h2>
              <p>
                Give each game a useful goal. That’s how Sidequest finds
                something meaningful to play.
              </p>
            </div>
          ) : (
            <>
              <div className="section-head">
                <div>
                  <span className="eyebrow">
                    {game.archived_at ? "Archived game" : "Quest journal"}
                  </span>
                  <h2>{game.title}</h2>
                </div>
                <button
                  disabled={busy}
                  onClick={() => {
                    setGameEditor(game);
                    setGoalEditor(null);
                  }}
                >
                  Edit game
                </button>
              </div>
              <p className="quiet">
                Interest {game.current_interest}/5 · Getting-started effort{" "}
                {game.friction}/5 · {game.energy_required} energy
              </p>
              {game.notes && <p className="notes">{game.notes}</p>}
              <div className="actions">
                <button disabled={busy} onClick={gameAction}>
                  {game.archived_at ? "Restore game" : "Archive game"}
                </button>
                <button
                  className="primary"
                  disabled={busy || Boolean(game.archived_at)}
                  onClick={() => {
                    setGoalEditor("new");
                    setGameEditor(null);
                  }}
                >
                  Add goal
                </button>
              </div>
              {game.archived_at && (
                <p className="notice">
                  Restore this game to add, reopen, or complete goals. Existing
                  goals and session records are preserved.
                </p>
              )}
              <OutcomeInsights key={game.id} gameId={game.id} />
              {goalEditor !== null && (
                <GoalForm
                  key={goalEditor === "new" ? "new" : goalEditor.id}
                  goal={goalEditor === "new" ? null : goalEditor}
                  gameId={game.id}
                  busy={busy}
                  onSave={saveGoal}
                  onCancel={() => setGoalEditor(null)}
                />
              )}
              {goalsLoading ? (
                <p role="status">Loading quests…</p>
              ) : goals.length === 0 ? (
                <div className="empty">
                  <h3>No quests yet.</h3>
                  <p>
                    Add a goal you can make progress on during a session. A game
                    needs an active goal to be recommended.
                  </p>
                </div>
              ) : (
                goals.map((goal) => (
                  <article className="goal-card" key={goal.id}>
                    <div className="section-head">
                      <h3>{goal.title}</h3>
                      <span className={`status ${goal.status}`}>
                        {goal.status}
                      </span>
                    </div>
                    <p className="quiet">
                      {goal.estimated_minutes} min · Priority {goal.priority}/3
                    </p>
                    {goal.notes && <p>{goal.notes}</p>}
                    <div className="actions">
                      <button
                        disabled={busy}
                        onClick={() => {
                          setGoalEditor(goal);
                          setGameEditor(null);
                        }}
                      >
                        Edit goal
                      </button>
                      {goal.status === "active" && (
                        <button
                          disabled={busy || Boolean(game.archived_at)}
                          onClick={() => goalAction(goal.id, "complete")}
                        >
                          Complete goal
                        </button>
                      )}
                      {goal.status !== "archived" && (
                        <button
                          disabled={busy}
                          onClick={() => goalAction(goal.id, "archive")}
                        >
                          Archive goal
                        </button>
                      )}
                      {goal.status !== "active" && (
                        <button
                          disabled={busy || Boolean(game.archived_at)}
                          onClick={() => goalAction(goal.id, "restore")}
                        >
                          {goal.status === "completed"
                            ? "Reopen goal"
                            : "Restore goal"}
                        </button>
                      )}
                    </div>
                  </article>
                ))
              )}
            </>
          )}
        </section>
      </div>
    </>
  );
}
