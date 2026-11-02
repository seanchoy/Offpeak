import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AIPlanner from "./AiPlanner";

beforeEach(() => {
  // Layout scrolling is verified in the browser; jsdom has no layout engine.
  vi.stubGlobal("requestAnimationFrame", vi.fn(() => 1));
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
});

function renderPlanner() {
  const onLoginRequired = vi.fn();
  render(
    <AIPlanner
      pois={[]}
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
