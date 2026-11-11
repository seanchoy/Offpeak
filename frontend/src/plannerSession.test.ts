import { beforeEach, describe, expect, it } from "vitest";

import {
  clearPlannerSession,
  loadPlannerSession,
  savePlannerSession,
  type PlannerSession,
} from "./plannerSession";

const SESSION: PlannerSession = {
  conversationId: "conv-1",
  messages: [
    { id: 1, role: "assistant", text: "Hi!" },
    { id: 2, role: "user", text: "Somewhere quiet?" },
    { id: 3, role: "assistant", text: "Try The Ramble Central Park.", showPlaces: true },
  ],
  uiAction: null,
  itinerary: null,
  savedItineraryId: "itinerary-1",
};

beforeEach(() => sessionStorage.clear());

describe("planner session", () => {
  it("restores what was saved", () => {
    savePlannerSession(SESSION);
    expect(loadPlannerSession()).toEqual(SESSION);
  });

  it("is empty after it is cleared", () => {
    savePlannerSession(SESSION);
    clearPlannerSession();
    expect(loadPlannerSession()).toBeNull();
  });

  it("ignores storage it cannot read", () => {
    sessionStorage.setItem("offpeak.planner.session", "{not json");
    expect(loadPlannerSession()).toBeNull();

    sessionStorage.setItem("offpeak.planner.session", JSON.stringify({ messages: [{ role: "x" }] }));
    expect(loadPlannerSession()).toBeNull();
  });
});
