import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { savePlannerSession } from "../plannerSession";
import type { Poi } from "../types";
import AIPlanner from "./AiPlanner";

beforeEach(() => {
  // Layout scrolling is verified in the browser; jsdom has no layout engine.
  vi.stubGlobal("requestAnimationFrame", vi.fn(() => 1));
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
  sessionStorage.clear();
});

function renderPlanner(pois: Poi[] = []) {
  const onLoginRequired = vi.fn();
  render(
    <AIPlanner
      pois={pois}
      isAuthenticated={false}
      onLoginRequired={onLoginRequired}
      onItineraryGenerated={vi.fn()}
    />
  );
  return onLoginRequired;
}

describe("AI Planner composer", () => {
  it("expands the panel before scrolling messages and hands off at the top", () => {
    renderPlanner();
    const history = screen.getByRole("log").parentElement!;
    const stage = history.closest(".ai-chat-stage")!;
    const bounds = vi.spyOn(stage, "getBoundingClientRect");
    bounds.mockReturnValue({ top: 200 } as DOMRect);
    const scrollPage = vi.spyOn(window, "scrollBy").mockImplementation(() => {});

    expect(fireEvent.wheel(history, { deltaY: 120, cancelable: true })).toBe(false);
    expect(scrollPage).toHaveBeenLastCalledWith({ top: 120, behavior: "instant" });
    expect(history.scrollTop).toBe(0);

    // A gesture crossing the expansion boundary passes its remainder inside.
    fireEvent.wheel(history, { deltaY: 220, cancelable: true });
    expect(scrollPage).toHaveBeenLastCalledWith({ top: 180, behavior: "instant" });
    expect(history.scrollTop).toBe(40);

    bounds.mockReturnValue({ top: 20 } as DOMRect);
    scrollPage.mockClear();
    expect(fireEvent.wheel(history, { deltaY: 120, cancelable: true })).toBe(true);
    expect(scrollPage).not.toHaveBeenCalled();
  });

  it("keeps empty input editable and disables sending whitespace", async () => {
    renderPlanner();
    const input = screen.getByRole("textbox");
    const send = screen.getByRole("button", { name: "Send to AI Planner" });
    expect(input).toBeEnabled();
    expect(send).toBeDisabled();
    await userEvent.type(input, "   ");
    expect(send).toBeDisabled();
    await userEvent.type(input, "Museums");
    expect(send).toBeEnabled();
  });

  it("lets people edit a suggested trip before sending it", async () => {
    const onLoginRequired = renderPlanner();
    await userEvent.click(screen.getByRole("button", { name: /Art & architecture/ }));
    expect(screen.getByRole("textbox")).toHaveValue(
      "Plan a low-crowd day with museums and architecture."
    );
    expect(screen.getByRole("textbox")).toHaveFocus();
    expect(onLoginRequired).not.toHaveBeenCalled();
  });

  it("only submits Enter after composition finishes and without Shift", () => {
    const onLoginRequired = renderPlanner();
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "博物馆" } });
    fireEvent.keyDown(input, { key: "Enter", isComposing: true });
    fireEvent.keyDown(input, { key: "Enter", keyCode: 229 });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
    expect(input).toHaveValue("博物馆");
    expect(onLoginRequired).not.toHaveBeenCalled();
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onLoginRequired).toHaveBeenCalledOnce();
  });
});

describe("AI Planner conversation", () => {
  it("restores the conversation from earlier in this tab, with its place cards", () => {
    savePlannerSession({
      conversationId: "conv-1",
      messages: [
        { id: 1, role: "assistant", text: "Hi!" },
        { id: 2, role: "user", text: "Somewhere quiet?" },
        { id: 3, role: "assistant", text: "Try The Ramble Central Park.", showPlaces: true },
      ],
      uiAction: null,
      itinerary: null,
    });
    const ramble = {
      slug: "the-ramble-central-park",
      name: "The Ramble Central Park",
      type: "park",
      borough: "Manhattan",
      neighborhood: "Central Park",
    } as Poi;

    renderPlanner([ramble]);

    expect(screen.getByText("Somewhere quiet?")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /The Ramble Central Park/ })).toHaveAttribute(
      "href",
      "/explore/the-ramble-central-park"
    );
    expect(screen.getByRole("button", { name: /Start again/ })).toBeInTheDocument();
  });

  it("forgets the saved conversation when the visitor starts again", async () => {
    savePlannerSession({
      conversationId: "conv-1",
      messages: [{ id: 2, role: "user", text: "Somewhere quiet?" }],
      uiAction: null,
      itinerary: null,
    });

    renderPlanner();
    await userEvent.click(screen.getByRole("button", { name: /Start again/ }));

    expect(screen.queryByText("Somewhere quiet?")).not.toBeInTheDocument();
    expect(sessionStorage.getItem("offpeak.planner.session")).toBeNull();
  });
});

describe("AI Planner itinerary", () => {
  const itinerary = {
    trip_name: "Winter Escape",
    start_date: "2026-11-12",
    end_date: "2026-11-12",
    warning: null,
    accessibility: [],
    stops: [
      {
        poi_id: 1, poi_name: "Whitney Museum of American Art", slug: "whitney", day_number: 1,
        visit_date: "2026-11-12", slot: "morning", slot_start: "09:00", slot_end: "12:00",
        position: 0, poi_type: "museum", crowd_level: "Quiet", hero_image_url: "",
        borough: "Manhattan", neighborhood: "West Village", suggested_duration: 120,
        accessibility: null, flags: [], busyness_for_day: [],
      },
    ],
  };

  function restoreItinerary(savedItineraryId: string | null) {
    savePlannerSession({
      conversationId: "conv-1",
      messages: [{ id: 2, role: "user", text: "Generate it" }],
      uiAction: null,
      itinerary,
      savedItineraryId,
    });
  }

  it("offers to save an itinerary that has not been saved", () => {
    restoreItinerary(null);
    renderPlanner();
    expect(screen.getByRole("button", { name: "Save itinerary" })).toBeEnabled();
  });

  it("cannot save the same itinerary twice", () => {
    restoreItinerary("itinerary-1");
    renderPlanner();
    expect(screen.getByRole("button", { name: "Saved ✓" })).toBeDisabled();
  });
});
