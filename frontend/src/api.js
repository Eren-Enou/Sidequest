export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
      ...(options.body === undefined
        ? {}
        : { body: JSON.stringify(options.body) }),
    });
  } catch {
    throw new ApiError(
      "Cannot reach Sidequest. Check that the backend is running, then retry.",
      0,
    );
  }
  const payload =
    response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const validation = Array.isArray(detail)
      ? detail
          .map(
            (item) =>
              `${item.loc?.filter((part) => part !== "body").join(" › ") || "Form"}: ${item.msg}`,
          )
          .join("; ")
      : null;
    const message =
      response.status >= 500
        ? "Sidequest is unavailable or busy. Check the backend and retry."
        : validation ||
          (typeof detail === "string" ? detail : detail?.message) ||
          "This action could not be completed. Please retry.";
    throw new ApiError(message, response.status, detail);
  }
  return payload;
}

export const api = {
  games: () => request("/games?include_archived=true"),
  goals: (gameId) => request(`/goals?game_id=${gameId}&include_archived=true`),
  outcomes: (gameId) => request(`/games/${gameId}/outcomes`),
  saveGame: (body, id) =>
    request(`/games${id ? `/${id}` : ""}`, {
      method: id ? "PATCH" : "POST",
      body,
    }),
  archiveGame: (id) => request(`/games/${id}`, { method: "DELETE" }),
  restoreGame: (id) => request(`/games/${id}/restore`, { method: "POST" }),
  saveGoal: (body, id) =>
    request(`/goals${id ? `/${id}` : ""}`, {
      method: id ? "PATCH" : "POST",
      body,
    }),
  goalAction: (id, action) =>
    request(`/goals/${id}${action === "archive" ? "" : `/${action}`}`, {
      method: action === "archive" ? "DELETE" : "POST",
    }),
  recommend: (body) => request("/recommendations", { method: "POST", body }),
  start: (candidate, situation) =>
    request("/sessions/start", {
      method: "POST",
      body: {
        game_id: candidate.game_id,
        goal_id: candidate.goal_id,
        situation,
      },
    }),
  active: () => request("/sessions/active"),
  finish: (id, body) =>
    request(`/sessions/${id}/finish`, { method: "POST", body }),
  history: () => request("/sessions"),
  session: (id) => request(`/sessions/${id}`),
};
