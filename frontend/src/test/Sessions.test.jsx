import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App.jsx";
import { GameForm, GoalForm } from "../forms/LibraryForms.jsx";

const NOW = Date.parse("2026-10-03T19:30:00Z");
const context = {
  available_minutes: 45,
  energy: "low",
  social_preference: "solo",
  desired_experience: "progression",
};
const candidate = {
  game_id: 1,
  goal_id: 1,
  game_title: "Moonlit Orchard",
  goal_title: "Harvest crops",
  estimated_minutes: 30,
  energy_required: "low",
  social_mode: "solo",
};
const breakdown = {
  interest: 18.75,
  goal_priority: 7.5,
  time_fit: 10,
  energy_fit: 30,
  experience_fit: 20,
  friction: -2,
  recent_play: 0,
};
const scored = {
  candidate,
  score: 84.25,
  suitability: 60,
  suitable: true,
  breakdown,
  unsuitable_reasons: [],
  factors: Object.entries(breakdown).map(([name, points]) => ({
    name,
    points,
    weight: 10,
    inputs: { value: 1 },
    reason: `Saved ${name} explanation`,
  })),
};
const result = {
  status: "clear_recommendation",
  engine_version: "v0.1-final-004",
  evaluated_at: "2026-10-03T19:00:00Z",
  context,
  recommendations: [scored],
  ranked: [scored],
  excluded: [],
  winner: scored,
};
const original = {
  id: 1,
  game_id: 1,
  goal_id: 1,
  game_title_snapshot: candidate.game_title,
  goal_title_snapshot: candidate.goal_title,
  started_at: "2026-10-03T19:00:00Z",
  finished_at: null,
  situation_snapshot: context,
  recommendation_snapshot: {
    snapshot_version: 1,
    selected: scored,
    evaluation: result,
  },
};
let active, history, finishError, readsFail;
const reply = (payload, status = 200) =>
  Promise.resolve({
    ok: status < 400,
    status,
    json: async () => structuredClone(payload),
  });
beforeEach(() => {
  vi.spyOn(Date, "now").mockReturnValue(NOW);
  active = structuredClone(original);
  history = [];
  finishError = null;
  readsFail = false;
  vi.stubGlobal(
    "fetch",
    vi.fn((url, options = {}) => {
      if (url === "/api/sessions/active") return reply(active);
      if (url === "/api/sessions")
        return readsFail ? reply({}, 503) : reply(history);
      if (url === "/api/sessions/1")
        return readsFail
          ? reply({}, 503)
          : reply(history.find((row) => row.id === 1) || active);
      if (url === "/api/sessions/1/finish") {
        if (finishError) return reply({ detail: finishError }, 409);
        const body = JSON.parse(options.body);
        const completed = {
          ...active,
          ...body,
          finished_at: "2026-10-03T19:30:00Z",
        };
        history = [completed];
        active = null;
        return reply(completed);
      }
      if (url === "/api/recommendations") {
        const response = structuredClone(result);
        response.context = JSON.parse(options.body);
        if (history.length) {
          response.recommendations[0].score = 81.25;
          response.recommendations[0].breakdown.recent_play = -3;
          response.recommendations[0].factors.find(
            (f) => f.name === "recent_play",
          ).points = -3;
        }
        return reply(response);
      }
      if (url === "/api/sessions/start") {
        active = structuredClone(original);
        return reply(active, 201);
      }
      if (url.startsWith("/api/games?"))
        return reply([
          {
            id: 1,
            title: "Renamed live game",
            energy_required: "low",
            social_mode: "solo",
            friction: 5,
            current_interest: 1,
            experience_tags: ["chill"],
            archived_at: "2026-10-03",
          },
        ]);
      throw new Error(`Unhandled ${url}`);
    }),
  );
});
afterEach(() => vi.restoreAllMocks());
async function ready() {
  render(<App />);
  await waitFor(() =>
    expect(
      screen.queryByText("Checking your active session…"),
    ).not.toBeInTheDocument(),
  );
  return userEvent.setup();
}
async function finishForm(user) {
  await user.click(
    screen.getByRole("button", { name: "Active session", exact: true }),
  );
  await user.click(
    screen.getByRole("button", { name: "Finish Sidequest", exact: true }),
  );
}
async function save(user) {
  await user.type(screen.getByLabelText("Progress"), "Level 23 → 25");
  await user.click(
    screen.getByRole("button", { name: "Save completed Sidequest" }),
  );
  await screen.findByText("Sidequest complete. Your progress is saved.");
}
const finishCalls = () =>
  fetch.mock.calls.filter(([url]) => url === "/api/sessions/1/finish");

describe("Usability terminology", () => {
  it("explains getting started and preserves all six backend values", async () => {
    const user = userEvent.setup(),
      onSave = vi.fn();
    render(<GameForm onSave={onSave} onCancel={() => {}} busy={false} />);
    const effort = screen.getByLabelText("How hard is it to get started?");
    expect(screen.getByText(/between deciding to play/)).toBeInTheDocument();
    expect(
      within(effort)
        .getAllByRole("option")
        .map((item) => item.value),
    ).toEqual(["0", "1", "2", "3", "4", "5"]);
    expect(screen.getByText("5 · Big commitment")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Game title"), "Quiet game");
    await user.click(screen.getByRole("button", { name: "Save game" }));
    expect(onSave.mock.calls[0][0].friction).toBe(0);
  });
  it("describes a rough worthwhile session rather than total goal duration", () => {
    render(
      <GoalForm
        gameId={1}
        onSave={() => {}}
        onCancel={() => {}}
        busy={false}
      />,
    );
    expect(screen.getByLabelText("Useful session length")).toHaveValue(30);
    expect(screen.getByText(/A rough estimate is fine/)).toHaveTextContent(
      "not total goal-completion time",
    );
  });
});
describe("Active and finish", () => {
  it("reconstructs an active session after unmounting and reloading the app", async () => {
    const first = render(<App />);
    await screen.findByText("Session active", { exact: true });
    first.unmount();
    const user = await ready();
    await finishForm(user);
    expect(screen.getByLabelText("Actual play time (minutes)")).toHaveValue(30);
    expect(
      fetch.mock.calls.filter(([url]) => url === "/api/sessions/active"),
    ).toHaveLength(2);
  });
  it("recovers the full active view and saved evidence from the backend", async () => {
    const user = await ready();
    await user.click(
      screen.getByRole("button", { name: "Active session", exact: true }),
    );
    expect(
      screen.getByRole("heading", { name: "Moonlit Orchard", exact: true }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Harvest crops", { exact: true }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "30m 0s elapsed" }),
    ).toBeInTheDocument();
    expect(screen.getByText("45 min")).toBeInTheDocument();
    await user.click(screen.getByText("Why this? See all score factors"));
    expect(screen.getByText("Saved energy_fit explanation")).toBeVisible();
  });
  it("suggests elapsed minutes but accepts edited actual duration", async () => {
    const user = await ready();
    await finishForm(user);
    expect(screen.getByLabelText("Actual play time (minutes)")).toHaveValue(30);
    await user.clear(screen.getByLabelText("Actual play time (minutes)"));
    await user.type(screen.getByLabelText("Actual play time (minutes)"), "18");
    await save(user);
    expect(JSON.parse(finishCalls()[0][1].body).actual_duration_minutes).toBe(
      18,
    );
  });
  it("does not rewrite edited duration when the timer advances", async () => {
    const user = await ready();
    await finishForm(user);
    await user.clear(screen.getByLabelText("Actual play time (minutes)"));
    await user.type(screen.getByLabelText("Actual play time (minutes)"), "12");
    vi.mocked(Date.now).mockReturnValue(NOW + 120000);
    await waitFor(
      () =>
        expect(
          screen.getByRole("heading", { name: "32m 0s elapsed" }),
        ).toBeInTheDocument(),
      { timeout: 2000 },
    );
    expect(screen.getByLabelText("Actual play time (minutes)")).toHaveValue(12);
    expect(finishCalls()).toHaveLength(0);
  });
  it("validates blank progress without a write", async () => {
    const user = await ready();
    await finishForm(user);
    fireEvent.change(screen.getByLabelText("Progress"), {
      target: { value: "  " },
    });
    fireEvent.submit(screen.getByRole("form", { name: "Finish Sidequest" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "describe your progress",
    );
    expect(finishCalls()).toHaveLength(0);
  });
  it.each([0, -1, 1.5])("rejects actual duration %s", async (value) => {
    const user = await ready();
    await finishForm(user);
    fireEvent.change(screen.getByLabelText("Actual play time (minutes)"), {
      target: { value: String(value) },
    });
    fireEvent.change(screen.getByLabelText("Progress"), {
      target: { value: "Tried a quest" },
    });
    fireEvent.submit(screen.getByRole("form", { name: "Finish Sidequest" }));
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(finishCalls()).toHaveLength(0);
  });
  it("sends enjoyment, progress, optional notes and goal completion exactly", async () => {
    const user = await ready();
    await finishForm(user);
    await user.selectOptions(
      screen.getByLabelText("How much did you enjoy it?"),
      "5",
    );
    await user.type(
      screen.getByLabelText("Session notes (optional)"),
      "Next time: the greenhouse",
    );
    await user.click(
      screen.getByRole("checkbox", { name: "Mark this goal completed" }),
    );
    await save(user);
    expect(JSON.parse(finishCalls()[0][1].body)).toEqual({
      actual_duration_minutes: 30,
      enjoyment_rating: 5,
      progress: "Level 23 → 25",
      notes: "Next time: the greenhouse",
      mark_goal_completed: true,
    });
    expect(
      screen.queryByText("Session active", { exact: true }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "History", exact: true }),
    ).toHaveAttribute("aria-current", "page");
  });
  it("omits optional notes and leaves the goal open by default", async () => {
    const user = await ready();
    await finishForm(user);
    await save(user);
    const body = JSON.parse(finishCalls()[0][1].body);
    expect(body.notes).toBeNull();
    expect(body.mark_goal_completed).toBe(false);
    expect(
      screen.queryByRole("button", { name: "Active session", exact: true }),
    ).not.toBeInTheDocument();
  });
  it("keeps the draft and active state on a recoverable finish conflict", async () => {
    finishError =
      "Restore the game and goal before completing it; session remains active";
    const user = await ready();
    await finishForm(user);
    await user.type(screen.getByLabelText("Progress"), "Beat the boss");
    await user.click(
      screen.getByRole("button", { name: "Save completed Sidequest" }),
    );
    await screen.findByRole("alert");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "session remains active",
    );
    expect(screen.getByLabelText("Progress")).toHaveValue("Beat the boss");
    expect(
      screen.getByText("Session active", { exact: true }),
    ).toBeInTheDocument();
  });
  it("recovers an already-finished result without overwriting history", async () => {
    const user = await ready();
    await finishForm(user);
    const saved = {
      ...original,
      finished_at: "2026-10-03T19:30:00Z",
      actual_duration_minutes: 20,
      enjoyment_rating: 4,
      progress: "Recorded elsewhere",
      notes: null,
    };
    history = [saved];
    active = null;
    finishError = "Session is already finished; history cannot be overwritten";
    await user.type(screen.getByLabelText("Progress"), "Do not overwrite");
    await user.click(
      screen.getByRole("button", { name: "Save completed Sidequest" }),
    );
    await screen.findByText(
      "This Sidequest was already recorded. Showing the saved result.",
    );
    expect(screen.getAllByText("Recorded elsewhere").length).toBeGreaterThan(0);
    expect(finishCalls()).toHaveLength(1);
  });
  it("recovers a successful finish whose write response was lost", async () => {
    const user = await ready();
    await finishForm(user);
    const delegate = fetch.getMockImplementation();
    fetch.mockImplementationOnce((url, options) => {
      delegate(url, options);
      return Promise.reject(new TypeError("lost response"));
    });
    await user.type(
      screen.getByLabelText("Progress"),
      "Saved despite disconnect",
    );
    await user.click(
      screen.getByRole("button", { name: "Save completed Sidequest" }),
    );
    await screen.findByText(
      "This Sidequest was already recorded. Showing the saved result.",
    );
    expect(
      screen.queryByText("Session active", { exact: true }),
    ).not.toBeInTheDocument();
    expect(finishCalls()).toHaveLength(1);
  });
  it("guards repeated finish submission", async () => {
    const user = await ready();
    await finishForm(user);
    await user.type(screen.getByLabelText("Progress"), "Finished chapter 4");
    await user.dblClick(
      screen.getByRole("button", { name: "Save completed Sidequest" }),
    );
    await screen.findByText("Sidequest complete. Your progress is saved.");
    expect(finishCalls()).toHaveLength(1);
  });
  it("can keep playing without submitting a finish", async () => {
    const user = await ready();
    await finishForm(user);
    await user.click(screen.getByRole("button", { name: "Keep playing" }));
    expect(
      screen.getByRole("button", { name: "Finish Sidequest", exact: true }),
    ).toBeInTheDocument();
    expect(finishCalls()).toHaveLength(0);
  });
});
describe("History and feedback", () => {
  function seedHistory() {
    history = [
      {
        ...structuredClone(original),
        finished_at: "2026-10-03T19:30:00Z",
        actual_duration_minutes: 30,
        enjoyment_rating: 4,
        progress: "Finished chapter 4",
        notes: "A good evening",
      },
    ];
    active = null;
  }
  it("has a clear empty history state", async () => {
    active = null;
    const user = await ready();
    await user.click(
      screen.getByRole("button", { name: "History", exact: true }),
    );
    await screen.findByRole("heading", {
      name: "No completed Sidequests yet.",
    });
  });
  it("shows completed snapshot titles, duration, enjoyment and progress", async () => {
    seedHistory();
    const user = await ready();
    await user.click(
      screen.getByRole("button", { name: "History", exact: true }),
    );
    const list = await screen.findByRole("region", {
      name: "Completed Sidequests",
    });
    expect(within(list).getByText("Moonlit Orchard")).toBeInTheDocument();
    expect(
      within(list).getByText("30 min played · Enjoyment 4/5"),
    ).toBeInTheDocument();
    expect(within(list).getByText("Finished chapter 4")).toBeInTheDocument();
    expect(within(list).queryByText("v0.1-final-004")).not.toBeInTheDocument();
  });
  it("loads individual saved details and explanation without live-library substitution", async () => {
    seedHistory();
    const user = await ready();
    await user.click(
      screen.getByRole("button", { name: "History", exact: true }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Inspect Harvest crops" }),
    );
    const detail = screen.getByRole("region", { name: "Session detail" });
    await within(detail).findByText("A good evening");
    expect(
      within(detail).getByRole("heading", { name: "Moonlit Orchard" }),
    ).toBeInTheDocument();
    await user.click(
      within(detail).getByText("Why this? See all score factors"),
    );
    expect(
      within(detail).getByText("Saved interest explanation"),
    ).toBeVisible();
    expect(within(detail).getByText(/v0.1-final-004/)).toBeInTheDocument();
    expect(fetch.mock.calls.some(([url]) => url === "/api/sessions/1")).toBe(
      true,
    );
    expect(fetch.mock.calls.some(([url]) => url.startsWith("/api/games"))).toBe(
      false,
    );
  });
  it("still uses old snapshots after visiting a renamed archived game", async () => {
    seedHistory();
    const user = await ready();
    await user.click(
      screen.getByRole("button", { name: "Library", exact: true }),
    );
    await user.click(screen.getByRole("checkbox", { name: "Show archived" }));
    await screen.findByRole("button", { name: /Renamed live game/ });
    await user.click(
      screen.getByRole("button", { name: "History", exact: true }),
    );
    await screen.findByRole("button", { name: "Inspect Harvest crops" });
    expect(screen.queryByText("Renamed live game")).not.toBeInTheDocument();
    expect(screen.getByText("Moonlit Orchard")).toBeInTheDocument();
  });
  it("recovers history after an application remount", async () => {
    seedHistory();
    const first = render(<App />);
    await screen.findByRole("button", { name: "History", exact: true });
    first.unmount();
    const user = await ready();
    await user.click(
      screen.getByRole("button", { name: "History", exact: true }),
    );
    await screen.findByText("Finished chapter 4");
  });
  it("retries unavailable history", async () => {
    seedHistory();
    readsFail = true;
    const user = await ready();
    await user.click(
      screen.getByRole("button", { name: "History", exact: true }),
    );
    await screen.findByRole("alert");
    readsFail = false;
    await user.click(screen.getByRole("button", { name: "Retry history" }));
    await screen.findByText("Finished chapter 4");
  });
  it("finishes and displays recency from the subsequent server recommendation", async () => {
    const user = await ready();
    await finishForm(user);
    await save(user);
    await user.click(
      screen.getByRole("button", { name: "Tonight", exact: true }),
    );
    await user.click(
      screen.getByRole("button", { name: "Find my next quest" }),
    );
    await screen.findByRole("heading", { name: "Here’s your next quest." });
    await user.click(screen.getByText("Why this? See all score factors"));
    expect(screen.getByText("-3 points")).toBeVisible();
    expect(screen.getByText("81.25")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Start selected quest" }),
    ).toBeEnabled();
  });
  it("starts, finishes, inspects history and recommends again through the UI", async () => {
    active = null;
    const user = await ready();
    await user.click(
      screen.getByRole("button", { name: "Find my next quest" }),
    );
    await screen.findByRole("heading", { name: "Here’s your next quest." });
    await user.click(
      screen.getByRole("button", { name: "Start selected quest" }),
    );
    await screen.findByRole("button", {
      name: "Finish Sidequest",
      exact: true,
    });
    await user.click(
      screen.getByRole("button", { name: "Finish Sidequest", exact: true }),
    );
    await save(user);
    await screen.findByRole("button", { name: "Inspect Harvest crops" });
    await user.click(
      screen.getByRole("button", { name: "Tonight", exact: true }),
    );
    await user.click(
      screen.getByRole("button", { name: "Find my next quest" }),
    );
    await screen.findByText("81.25");
  });
});
