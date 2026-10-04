import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../api.js";
import OutcomeInsights from "../components/OutcomeInsights.jsx";
import FinishForm from "../forms/FinishForm.jsx";
import Library from "../views/Library.jsx";

const distribution = (ratings) => [1, 2, 3, 4, 5].map((rating) => ({ rating, count: ratings.filter((r) => r === rating).length }));
function summary(ratings = []) {
  const base = {
    completed_session_count: ratings.length,
    average_enjoyment: ratings.length ? ratings.reduce((a, b) => a + b, 0) / ratings.length : null,
    rating_distribution: distribution(ratings),
  };
  return {
    ...base, game_id: 1,
    recent_sessions: ratings.slice(-5).reverse().map((rating, index) => ({
      session_id: index + 1, enjoyment_rating: rating, finished_at: "2026-10-04T19:00:00Z",
      goal_title_snapshot: "Original recorded quest", energy: "low", desired_experience: "progression",
    })),
    by_desired_experience: ratings.length ? [{ ...base, desired_experience: "progression" }] : [],
    by_energy: ratings.length ? [{ ...base, energy: "low" }] : [],
  };
}
let outcomeRequest;
beforeEach(() => { outcomeRequest = vi.spyOn(api, "outcomes").mockResolvedValue(summary()); });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
async function open() {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Show outcome insights" }));
  await screen.findByRole("button", { name: "Refresh outcome insights" });
  return user;
}

describe("Outcome insights", () => {
  it("loads on demand and shows a meaningful empty state without fake averages", async () => {
    render(<OutcomeInsights gameId={1} />);
    expect(outcomeRequest).not.toHaveBeenCalled();
    await open();
    expect(outcomeRequest).toHaveBeenCalledExactlyOnceWith(1);
    expect(screen.getByText("No completed session history yet.")).toBeVisible();
    expect(screen.queryByText(/Average enjoyment:/)).not.toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
  it("keeps one-session evidence quantity visible with an average", async () => {
    outcomeRequest.mockResolvedValue(summary([5]));
    render(<OutcomeInsights gameId={1} />);
    await open();
    expect(screen.getByText(/Average enjoyment:/)).toHaveTextContent("5.00 / 5 across 1 completed session");
    expect(screen.getByText("1 completed session", { exact: true })).toBeVisible();
    const row = within(screen.getByRole("table", { name: "Desired experience at session start" })).getAllByRole("row")[1];
    expect(row).toHaveTextContent("Progression15.00");
  });
  it("renders distribution, bounded recent evidence and counted context rows", async () => {
    outcomeRequest.mockResolvedValue(summary([1, 2, 3, 4, 5, 5]));
    render(<OutcomeInsights gameId={1} />);
    await open();
    expect(screen.getByText(/Average enjoyment:/)).toHaveTextContent("3.33 / 5 across 6 completed sessions");
    const rows = within(screen.getByRole("table", { name: "Enjoyment distribution" })).getAllByRole("row").slice(1);
    expect(rows.map((row) => within(row).getByRole("cell").textContent)).toEqual(["1", "1", "1", "1", "2"]);
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
    expect(screen.getAllByText(/Original recorded quest/)).toHaveLength(5);
    expect(document.querySelectorAll("time[datetime='2026-10-04T19:00:00Z']")).toHaveLength(5);
    expect(screen.getByRole("table", { name: "Energy at session start" })).toHaveTextContent("Low63.33");
    expect(screen.getByText(/These insights do not affect recommendation ranking/)).toBeVisible();
  });
  it("acknowledges old default-3 ambiguity without excluding that rating", async () => {
    outcomeRequest.mockResolvedValue(summary([3]));
    render(<OutcomeInsights gameId={1} />);
    const user = await open();
    await user.click(screen.getByText("About this evidence"));
    expect(screen.getByText(/Older 3 ratings/)).toBeVisible();
    expect(screen.getByText(/Average enjoyment:/)).toHaveTextContent("3.00 / 5");
  });
  it("shows unknown recorded context without borrowing current game attributes", async () => {
    const data = summary([4]);
    data.by_energy[0].energy = null;
    data.by_desired_experience[0].desired_experience = null;
    outcomeRequest.mockResolvedValue(data);
    render(<OutcomeInsights gameId={1} />);
    await open();
    expect(screen.getAllByText("Not recorded / unavailable")).toHaveLength(2);
  });
  it("shows a retryable failure instead of treating it as no history", async () => {
    outcomeRequest.mockRejectedValueOnce(new Error("Cannot reach Sidequest"));
    render(<OutcomeInsights gameId={1} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Show outcome insights" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach Sidequest");
    expect(screen.queryByText("No completed session history yet.")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry outcome insights" }));
    await screen.findByText("No completed session history yet.");
  });
  it("refreshes evidence without mutating any session", async () => {
    render(<OutcomeInsights gameId={1} />);
    const user = await open();
    outcomeRequest.mockResolvedValue(summary([4]));
    await user.click(screen.getByRole("button", { name: "Refresh outcome insights" }));
    await screen.findByText("1 completed session", { exact: true });
    expect(outcomeRequest).toHaveBeenCalledTimes(2);
  });
  it("does not display an earlier game's delayed response", async () => {
    let resolve;
    outcomeRequest.mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
    const view = render(<OutcomeInsights key={1} gameId={1} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Show outcome insights" }));
    expect(screen.getByRole("status")).toHaveTextContent("Loading outcome insights");
    view.rerender(<OutcomeInsights key={2} gameId={2} />);
    await open();
    await act(async () => resolve(summary([5])));
    expect(screen.getByText("No completed session history yet.")).toBeVisible();
    expect(screen.queryByText(/Average enjoyment:/)).not.toBeInTheDocument();
  });
  it("integrates with the selected library game, including archived games, without shelf-wide requests", async () => {
    const games = [1, 2].map((id) => ({ id, title: `Game ${id}`, current_interest: 3, friction: 0,
      energy_required: "low", social_mode: "solo", experience_tags: ["progression"], archived_at: id === 2 ? "2026-10-04" : null }));
    vi.spyOn(api, "games").mockResolvedValue(games);
    vi.spyOn(api, "goals").mockResolvedValue([]);
    render(<Library />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "low energy, solo Game 1" }));
    expect(outcomeRequest).not.toHaveBeenCalled();
    await open();
    await user.click(screen.getByLabelText("Show archived"));
    await user.click(screen.getByRole("button", { name: "Archived Game 2" }));
    expect(screen.getByRole("button", { name: "Show outcome insights" })).toBeVisible();
    await open();
    expect(outcomeRequest.mock.calls).toEqual([[1], [2]]);
  });
  it("uses the read-only game outcome endpoint", async () => {
    outcomeRequest.mockRestore();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => summary() }));
    await api.outcomes(12);
    expect(fetch).toHaveBeenCalledWith("/api/games/12/outcomes", expect.not.objectContaining({ method: "POST" }));
  });
});

describe("Explicit enjoyment selection", () => {
  it("starts without a rating and rejects both click and programmatic implicit submission", async () => {
    const submit = vi.fn(), user = userEvent.setup();
    render(<FinishForm suggestedMinutes={30} onSubmit={submit} onCancel={() => {}} busy={false} />);
    expect(screen.getByLabelText("How much did you enjoy it?")).toHaveValue("");
    await user.type(screen.getByLabelText("Progress"), "Rested");
    await user.click(screen.getByRole("button", { name: "Save completed Sidequest" }));
    expect(submit).not.toHaveBeenCalled();
    fireEvent.submit(screen.getByRole("form", { name: "Finish Sidequest" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Choose an enjoyment rating from 1 to 5");
    expect(submit).not.toHaveBeenCalled();
  });
  it.each([1, 2, 3, 4, 5])("submits explicitly selected numeric rating %s", async (rating) => {
    const submit = vi.fn(), user = userEvent.setup();
    render(<FinishForm suggestedMinutes={30} onSubmit={submit} onCancel={() => {}} busy={false} />);
    await user.type(screen.getByLabelText("Progress"), " Rested ");
    await user.selectOptions(screen.getByLabelText("How much did you enjoy it?"), String(rating));
    await user.click(screen.getByRole("button", { name: "Save completed Sidequest" }));
    expect(submit).toHaveBeenCalledExactlyOnceWith({ actual_duration_minutes: 30, enjoyment_rating: rating,
      progress: "Rested", notes: null, mark_goal_completed: false });
  });
  it("rejects a selection cleared back to the placeholder", async () => {
    const submit = vi.fn(), user = userEvent.setup();
    render(<FinishForm suggestedMinutes={30} onSubmit={submit} onCancel={() => {}} busy={false} />);
    await user.type(screen.getByLabelText("Progress"), "Rested");
    await user.selectOptions(screen.getByLabelText("How much did you enjoy it?"), "3");
    await user.selectOptions(screen.getByLabelText("How much did you enjoy it?"), "");
    fireEvent.submit(screen.getByRole("form", { name: "Finish Sidequest" }));
    expect(submit).not.toHaveBeenCalled();
  });
});
