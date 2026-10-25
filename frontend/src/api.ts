// Shared API helpers used by the whole frontend.
import { repairApiText } from "./text";
//
// The backend uses HttpOnly cookies for web authentication.
// This means every request must include:
// credentials: "include"
//
// Keeping all fetch logic here prevents every component from
// handling backend responses differently.

type BackendErrorData = {
  detail?: string | Array<{ msg?: string }>;
  message?: string;
};

export type ApiErrorKind = "http" | "network" | "timeout";

/*
  Keeps the failure category and HTTP status available to page components.
  This lets a feature show a useful message without matching technical error
  text returned by the backend.
*/
export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status?: number;

  constructor(
    message: string,
    {
      kind,
      status,
      cause,
    }: {
      kind: ApiErrorKind;
      status?: number;
      cause?: unknown;
    }
  ) {
    super(message, { cause });
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

// Default timeout for ordinary requests. Kept generous enough to survive a
// backend cold start (the free host spins down when idle) instead of aborting
// mid-boot. Slow endpoints (AI chat, itinerary generation) pass their own
// longer signal at the call site.
const API_TIMEOUT_MS = 30_000;

/*
  App.tsx listens for this event so every protected request follows the same
  expired-session behaviour. The event is only sent after the refresh cookie
  is also missing or invalid.
*/
export const AUTHENTICATION_REQUIRED_EVENT =
  "offpeak:authentication-required";

let refreshSessionPromise: Promise<boolean> | null = null;

function isWebAuthRequest(url: string): boolean {
  return url.split("?", 1)[0].startsWith("/api/auth/");
}

function notifyAuthenticationRequired(): void {
  window.dispatchEvent(
    new Event(AUTHENTICATION_REQUIRED_EVENT)
  );
}

async function refreshWebSession(): Promise<boolean> {
  if (refreshSessionPromise) {
    return refreshSessionPromise;
  }

  /*
    Several protected requests can fail together when a page opens. Sharing
    one promise prevents each request from rotating the refresh token.
  */
  refreshSessionPromise = (async () => {
    try {
      const response = await fetch("/api/auth/refresh", {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
        },
        signal: AbortSignal.timeout(API_TIMEOUT_MS),
      });

      return response.ok;
    } catch (error) {
      console.info("The web session could not be refreshed:", error);
      return false;
    }
  })();

  try {
    return await refreshSessionPromise;
  } finally {
    refreshSessionPromise = null;
  }
}

async function sendRequest(
  url: string,
  options: RequestInit,
  headers: Headers
): Promise<Response> {
  return fetch(url, {
    ...options,
    headers,
    credentials: "include",
    /*
      A new timeout signal is created for a retry when the caller did not
      provide one. This gives the repeated request its own response window.
    */
    signal: options.signal ?? AbortSignal.timeout(API_TIMEOUT_MS),
  });
}

/*
  Converts backend errors into messages that make sense to a normal user.

  FastAPI can return errors in several different formats:
  { detail: "Access token missing." }
  { detail: [{ msg: "Field required" }] }
  { message: "Something went wrong." }
*/
export function getErrorMessage(
  data: BackendErrorData | null,
  status?: number
): string {
  // A protected page returned 401 or 403.
  // Do not expose technical token language to the user.
  if (status === 401 || status === 403) {
    return "Please log in to continue.";
  }

  // FastAPI validation errors commonly use an array.
  if (Array.isArray(data?.detail) && data.detail.length > 0) {
    return data.detail[0]?.msg || "Please check the information you entered.";
  }

  if (typeof data?.detail === "string") {
    const detail = data.detail.trim();
    const lowerDetail = detail.toLowerCase();

    // Translate authentication implementation details into useful wording.
    if (
      lowerDetail.includes("access token") ||
      lowerDetail.includes("refresh token") ||
      lowerDetail.includes("not authenticated") ||
      lowerDetail.includes("not authorised") ||
      lowerDetail.includes("not authorized") ||
      lowerDetail.includes("authentication required")
    ) {
      return "Please log in to continue.";
    }

    return detail;
  }

  if (typeof data?.message === "string") {
    return data.message;
  }

  if (status === 404) {
    return "The requested item could not be found.";
  }

  if (status === 409) {
    return "That action could not be completed because of a conflict.";
  }

  if (status === 422) {
    return "Please check the information you entered.";
  }

  if (status !== undefined && status >= 500) {
    return "The server could not complete that request. Please try again.";
  }

  return "Something went wrong. Please try again.";
}

/*
  Recognises the messages getErrorMessage produces for an expired or missing
  session. Several pages need this to show a login prompt instead of a
  technical failure, so it lives here beside the wording it matches.
*/
export function isAuthenticationError(error: unknown): boolean {
  if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
    return true;
  }

  if (!(error instanceof Error)) {
    return false;
  }

  const message = error.message.toLowerCase();

  return (
    message.includes("log in") ||
    message.includes("not authenticated") ||
    message.includes("authentication failed") ||
    message.includes("unauthorised") ||
    message.includes("unauthorized")
  );
}

/*
  Attempts to read a response body safely.

  Some backend failures return plain text instead of JSON.
  Previously, JSON.parse caused errors such as:

  Unexpected token 'I', "Internal Server Error" is not valid JSON

  This helper prevents that technical parsing error from appearing in the UI.
*/
async function readResponseBody(
  response: Response
): Promise<BackendErrorData | null> {
  const text = await response.text();

  if (!text.trim()) {
    return null;
  }

  try {
    return JSON.parse(text) as BackendErrorData;
  } catch {
    // The server returned plain text rather than JSON.
    return {
      detail: text,
    };
  }
}

/*
  Shared fetch function.

  Example:
  const pois = await apiFetch<POI[]>("/api/pois");

  Example with POST:
  await apiFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
*/
type ApiFetchSettings = {
  /*
    Skip the app-wide "please log in" event when a request still fails with
    401. The startup session check uses this: for a logged-out visitor a 401
    is the expected answer, not a reason to open the login modal.
  */
  quietAuthFailure?: boolean;
};

export async function apiFetch<T>(
  url: string,
  options: RequestInit = {},
  settings: ApiFetchSettings = {}
): Promise<T> {
  const headers = new Headers(options.headers);

  // Tell the backend that the frontend expects JSON responses.
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  // Only add JSON Content-Type when a request actually has a body.
  // This avoids adding unnecessary Content-Type headers to GET requests.
  if (
    options.body !== undefined &&
    !(options.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;

  try {
    response = await sendRequest(url, options, headers);

    /*
      Access cookies expire before refresh cookies. For a protected request,
      refresh once and then repeat the original request once. Authentication
      endpoints are excluded so an incorrect login cannot start this flow.
    */
    if (response.status === 401 && !isWebAuthRequest(url)) {
      const sessionWasRefreshed = await refreshWebSession();

      if (sessionWasRefreshed) {
        response = await sendRequest(url, options, headers);
      } else {
        // The original 401 is handled below after its response body is read.
      }
    }
  } catch (error) {
    console.error(`Could not connect to ${url}:`, error);

    if (
      error instanceof DOMException &&
      (error.name === "AbortError" || error.name === "TimeoutError")
    ) {
      throw new ApiError(
        "The server took too long to respond. Check that the backend is running, then try again.",
        {
          kind: "timeout",
          cause: error,
        }
      );
    }

    throw new ApiError(
      "Could not connect to the server. Check that the backend is running.",
      {
        kind: "network",
        cause: error,
      }
    );
  }

  const data = await readResponseBody(response);

  if (!response.ok) {
    if (
      response.status === 401 &&
      !isWebAuthRequest(url) &&
      !settings.quietAuthFailure
    ) {
      notifyAuthenticationRequired();
    }

    /*
      On the auth endpoints a 401 means the credentials were wrong, not that a
      session expired, and the backend's message is written for the user
      ("Incorrect email or password..."), so it is shown as it is.
    */
    const message =
      response.status === 401 &&
      isWebAuthRequest(url) &&
      typeof data?.detail === "string"
        ? data.detail
        : getErrorMessage(data, response.status);

    throw new ApiError(message, {
      kind: "http",
      status: response.status,
    });
  }

  return repairApiText(data as T);
}
