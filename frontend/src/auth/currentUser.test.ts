import { describe, expect, it, vi } from "vitest";

import { fetchCurrentUser } from "./currentUser";

type Route = { status: number; body?: unknown };

/*
  Replaces window.fetch: each URL answers from its own queue of responses, so a
  test can say "first 401, then 200" for the same endpoint.
*/
function stubFetch(routes: Record<string, Route[]>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const next = routes[url]?.shift();

    if (!next) {
      throw new Error(`Unexpected request to ${url}`);
    }

    return new Response(
      next.body === undefined ? "" : JSON.stringify(next.body),
      { status: next.status, headers: { "Content-Type": "application/json" } }
    );
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const ME = {
  email: "sean@example.com",
  display_name: "Sean Cai",
  accessibility: true,
};

describe("Part4 fetchCurrentUser", () => {
  it("returns the signed-in user in the frontend's shape", async () => {
    stubFetch({ "/api/users/me": [{ status: 200, body: ME }] });

    await expect(fetchCurrentUser()).resolves.toEqual({
      email: "sean@example.com",
      displayName: "Sean Cai",
      accessibility: true,
    });
  });

  it("returns null when nobody is signed in", async () => {
    stubFetch({
      "/api/users/me": [{ status: 401, body: { detail: "Access token missing." } }],
      "/api/auth/refresh": [{ status: 401 }],
    });

    await expect(fetchCurrentUser()).resolves.toBeNull();
  });

  it("survives an expired access token by refreshing once", async () => {
    const fetchMock = stubFetch({
      "/api/users/me": [
        { status: 401, body: { detail: "Your session has expired." } },
        { status: 200, body: ME },
      ],
      "/api/auth/refresh": [{ status: 200, body: { message: "ok" } }],
    });

    await expect(fetchCurrentUser()).resolves.toMatchObject({
      displayName: "Sean Cai",
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/refresh", expect.anything());
  });

  it("does not hide server errors as 'signed out'", async () => {
    stubFetch({ "/api/users/me": [{ status: 500, body: { detail: "boom" } }] });

    await expect(fetchCurrentUser()).rejects.toThrow();
  });
});
