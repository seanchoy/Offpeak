import { useState } from "react";
import type { FormEvent } from "react";

import { apiFetch } from "../api";
import { toAuthUser } from "../auth/currentUser";
import type { MeResponse } from "../auth/currentUser";
import type { AuthUser } from "../types";

type WelcomePageProps = {
  user: AuthUser;
  // Called with the saved user after Save, or the unchanged user after Skip.
  onDone: (user: AuthUser) => void;
};

/*
  Shown once after a first Google sign-in. The account already exists with the
  name Google provided, so both fields start filled in and skipping is safe.
*/
function WelcomePage({ user, onDone }: WelcomePageProps) {
  const [displayName, setDisplayName] = useState(user.displayName);
  const [accessibility, setAccessibility] = useState(user.accessibility);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");

    const trimmedName = displayName.trim();

    if (!trimmedName) {
      setErrorMessage("Please enter a display name.");
      return;
    }

    setIsSaving(true);

    try {
      const me = await apiFetch<MeResponse>("/api/users/me", {
        method: "PATCH",
        body: JSON.stringify({
          display_name: trimmedName,
          accessibility,
        }),
      });

      onDone(toAuthUser(me));
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Your details could not be saved. Please try again."
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="welcome-page">
      <div className="auth-card welcome-card">
        <p className="section-eyebrow">Welcome to Offpeak</p>
        <h2 id="welcome-title">You're all set</h2>

        <p className="auth-introduction">
          Check how we should greet you and whether to prioritise step-free
          places. You can change both later in your profile.
        </p>

        <form onSubmit={handleSave} aria-labelledby="welcome-title">
          <label>
            Display name
            <input
              type="text"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              autoComplete="name"
              maxLength={50}
              disabled={isSaving}
            />
          </label>

          <label className="accessibility-option">
            <input
              type="checkbox"
              checked={accessibility}
              onChange={(event) => setAccessibility(event.target.checked)}
              disabled={isSaving}
            />

            <span className="accessibility-option-check" aria-hidden="true" />

            <span>
              <strong>Prefer step-free routes</strong>
              <small>
                Accessible places will be prioritised and warnings will be
                shown when accessibility information is unavailable.
              </small>
            </span>
          </label>

          {errorMessage && (
            <p className="auth-message error" role="alert">
              {errorMessage}
            </p>
          )}

          <button
            type="submit"
            className="auth-submit-button"
            disabled={isSaving}
          >
            {isSaving ? "Saving..." : "Save"}
          </button>

          <button
            type="button"
            className="auth-switch-button welcome-skip-button"
            onClick={() => onDone(user)}
            disabled={isSaving}
          >
            Skip for now
          </button>
        </form>
      </div>
    </section>
  );
}

export default WelcomePage;
