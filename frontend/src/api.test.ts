import { describe, expect, it, vi } from "vitest";

import { apiFetch } from "./api";

function stubResponse(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      })
    )
  );
}

describe("apiFetch error messages", () => {
  it("shows the backend's message for a wrong password", async () => {
    stubResponse(401, { detail: "Incorrect email or password. Please try again." });

    await expect(
      apiFetch("/api/auth/login", { method: "POST", body: "{}" })
    ).rejects.toThrow("Incorrect email or password. Please try again.");
  });

  it("keeps the generic wording for an expired session elsewhere", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: "Access token missing." }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        })
      )
    );

    await expect(apiFetch("/api/users/me/saved-pois")).rejects.toThrow(
      "Please log in to continue."
    );
  });
});
