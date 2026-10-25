import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import WelcomePage from "./WelcomePage";

const USER = {
  email: "sean@example.com",
  displayName: "Sean Cai",
  accessibility: false,
};

function stubPatch(status: number, body: unknown) {
  const fetchMock = vi.fn(async () =>
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    })
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderPage(onDone = vi.fn()) {
  render(<WelcomePage user={USER} onDone={onDone} />);
  return onDone;
}

describe("Part5 WelcomePage", () => {
  it("starts from the name Google gave us", () => {
    renderPage();

    expect(screen.getByLabelText(/display name/i)).toHaveValue("Sean Cai");
    expect(screen.getByRole("checkbox", { name: /step-free/i })).not.toBeChecked();
  });

  it("saves the edited profile and hands back the updated user", async () => {
    const fetchMock = stubPatch(200, {
      email: "sean@example.com",
      display_name: "Sean",
      accessibility: true,
    });
    const onDone = renderPage();
    const user = userEvent.setup();

    const name = screen.getByLabelText(/display name/i);
    await user.clear(name);
    await user.type(name, "  Sean  ");
    await user.click(screen.getByRole("checkbox", { name: /step-free/i }));
    await user.click(screen.getByRole("button", { name: /save/i }));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/users/me");
    expect(options.method).toBe("PATCH");
    expect(JSON.parse(String(options.body))).toEqual({
      display_name: "Sean",
      accessibility: true,
    });
    expect(onDone).toHaveBeenCalledWith({
      email: "sean@example.com",
      displayName: "Sean",
      accessibility: true,
    });
  });

  it("does not send a blank name", async () => {
    const fetchMock = stubPatch(200, {});
    const onDone = renderPage();
    const user = userEvent.setup();

    await user.clear(screen.getByLabelText(/display name/i));
    await user.type(screen.getByLabelText(/display name/i), "   ");
    await user.click(screen.getByRole("button", { name: /save/i }));

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(onDone).not.toHaveBeenCalled();
  });

  it("shows an error and stays on the page when saving fails", async () => {
    stubPatch(500, { detail: "boom" });
    const onDone = renderPage();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /save/i }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(onDone).not.toHaveBeenCalled();
  });

  it("can be skipped without saving", async () => {
    const fetchMock = stubPatch(200, {});
    const onDone = renderPage();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /skip/i }));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(onDone).toHaveBeenCalledWith(USER);
  });
});
