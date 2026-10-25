import { ApiError, apiFetch } from "../api";
import type { AuthUser } from "../types";

type MeResponse = {
  email: string;
  display_name: string;
  accessibility: boolean;
};

/*
  Asks the backend who the authentication cookie belongs to.

  This is how the app learns about a Google sign-in, which arrives as a full
  page redirect rather than a JSON response. It lives under /api/users/ (not
  /api/auth/) so apiFetch refreshes an expired access token before giving up.

  Returns null only when nobody is signed in. Server and network errors are
  rethrown so a temporary outage does not log the user out.
*/
export async function fetchCurrentUser(): Promise<AuthUser | null> {
  try {
    const me = await apiFetch<MeResponse>(
      "/api/users/me",
      {},
      { quietAuthFailure: true }
    );
    return toAuthUser(me);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }

    throw error;
  }
}

/* Converts the backend's snake_case response into the frontend user shape. */
export function toAuthUser(me: MeResponse): AuthUser {
  return {
    email: me.email,
    displayName: me.display_name,
    accessibility: me.accessibility,
  };
}

export type { MeResponse };
