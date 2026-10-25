/*
  The Google callback cannot show an error page of its own, so it redirects
  home with ?auth_error=<code>. Only the codes below are recognised: the
  wording lives here rather than in the URL, so a crafted link cannot make the
  site display arbitrary text.
*/
const AUTH_ERROR_MESSAGES: Record<string, string> = {
  google_failed: "Google sign-in didn't complete. Please try again.",
  google_unverified:
    "Your Google account's email address hasn't been verified yet. Verify it with Google, then try again.",
};

export function getAuthErrorMessage(search: string): string | null {
  const code = new URLSearchParams(search).get("auth_error");

  if (!code || !Object.hasOwn(AUTH_ERROR_MESSAGES, code)) {
    return null;
  }

  return AUTH_ERROR_MESSAGES[code];
}
