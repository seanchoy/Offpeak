import { describe, expect, it } from "vitest";

import { getAuthErrorMessage } from "./authError";

describe("Part3 auth_error", () => {
  it("explains a failed or cancelled Google login", () => {
    expect(getAuthErrorMessage("?auth_error=google_failed")).toEqual(
      expect.any(String)
    );
  });

  it("explains an unverified Google email differently", () => {
    const unverified = getAuthErrorMessage("?auth_error=google_unverified");

    expect(unverified).toEqual(expect.any(String));
    expect(unverified).not.toBe(getAuthErrorMessage("?auth_error=google_failed"));
  });

  it("returns null when there is no error", () => {
    expect(getAuthErrorMessage("")).toBeNull();
    expect(getAuthErrorMessage("?tab=saved")).toBeNull();
  });

  it("ignores codes it does not know", () => {
    expect(getAuthErrorMessage("?auth_error=<script>")).toBeNull();
  });
});
