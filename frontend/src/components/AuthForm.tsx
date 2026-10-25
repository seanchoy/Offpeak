import { useState } from "react";
import type { FormEvent } from "react";

import { apiFetch } from "../api";
import { EMAIL_SIGNUP_ENABLED } from "../features";
import type { AuthMode, AuthResponse, AuthUser } from "../types";

type AuthFormProps = {
  onXClick: () => void;
  onLoginClick: () => void;
  onRegisterClick: () => void;
  authMode: AuthMode;
  onAuthSuccess?: (user: AuthUser) => void;
  // An error to show when the form opens, e.g. after a failed Google sign-in.
  initialError?: string;
};

/*
  Creates a readable display name from an email address.

  Example:
  perry.smith@example.com becomes Perry Smith
*/
function getNameFromEmail(email: string): string {
  const emailName = email.split("@")[0] || "Traveller";

  return emailName
    .replace(/[._-]+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

/*
  Normalises the web login and registration responses into the display
  information used by the frontend.
*/
function buildAuthenticatedUser(
  response: AuthResponse,
  submittedEmail: string,
  submittedDisplayName?: string
): AuthUser {
  const responseEmail =
    response.user?.email || response.email || submittedEmail.trim();

  const responseDisplayName =
    response.user?.display_name ||
    response.user?.username ||
    response.display_name ||
    response.username ||
    submittedDisplayName?.trim() ||
    getNameFromEmail(responseEmail);

  return {
    email: responseEmail,
    displayName: responseDisplayName,
    accessibility:
      response.user?.accessibility ??
      response.accessibility ??
      false,
  };
}

function AuthForm({
  onXClick,
  onRegisterClick,
  onLoginClick,
  authMode,
  onAuthSuccess,
  initialError,
}: AuthFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // These fields are only used during registration.
  const [username, setUsername] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [accessibility, setAccessibility] = useState(false);

  // Message shown inside the authentication modal.
  const [authMessage, setAuthMessage] = useState(initialError ?? "");
  const [isError, setIsError] = useState(Boolean(initialError));
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isLogin = authMode === "login";

  function clearFeedback() {
    setAuthMessage("");
    setIsError(false);
  }

  function showError(message: string) {
    setAuthMessage(message);
    setIsError(true);
  }

  function validateLogin(): boolean {
    if (!email.trim()) {
      showError("Please enter your email address.");
      return false;
    }

    if (!password) {
      showError("Please enter your password.");
      return false;
    }

    return true;
  }

  function validateRegistration(): boolean {
    if (!username.trim()) {
      showError("Please enter a display name.");
      return false;
    }

    if (!email.trim()) {
      showError("Please enter your email address.");
      return false;
    }

    if (!password) {
      showError("Please enter a password.");
      return false;
    }

    if (password.length < 6) {
      showError("Your password must contain at least 6 characters.");
      return false;
    }

    if (password !== confirmPassword) {
      showError("The passwords do not match.");
      return false;
    }

    return true;
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFeedback();

    if (!validateLogin()) {
      return;
    }

    try {
      setIsSubmitting(true);

      const response = await apiFetch<AuthResponse>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      const user = buildAuthenticatedUser(response, email);

      /*
        Only display information is stored locally.

        The authentication token remains in the secure HttpOnly cookie and is
        not stored in localStorage.
      */
      localStorage.setItem("offpeak_user", JSON.stringify(user));

      setAuthMessage(response.message || "You are now logged in.");
      setIsError(false);

      onAuthSuccess?.(user);
    } catch (error) {
      console.error("Login failed:", error);

      showError(
        error instanceof Error
          ? error.message
          : "Login could not be completed."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFeedback();

    if (!validateRegistration()) {
      return;
    }

    let accountCreated = false;

    try {
      setIsSubmitting(true);

      const signupResponse = await apiFetch<AuthResponse>("/api/auth/signup", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim(),
          display_name: username.trim(),
          accessibility,
          password,
          confirm_password: confirmPassword,
        }),
      });
      accountCreated = true;

      /*
        Signup creates the account but does not establish the HttpOnly cookie
        session. Logging in immediately keeps the navbar and protected requests
        consistent with the server-side authentication state.
      */
      const loginResponse = await apiFetch<AuthResponse>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      const user = buildAuthenticatedUser(
        loginResponse,
        email,
        signupResponse.display_name || username
      );

      localStorage.setItem("offpeak_user", JSON.stringify(user));

      setAuthMessage("Your account has been created and you are now logged in.");
      setIsError(false);

      onAuthSuccess?.(user);
    } catch (error) {
      console.error("Registration failed:", error);

      if (accountCreated) {
        showError(
          "Your account was created, but automatic login failed. Please switch to Log in and continue with the same details."
        );
      } else {
        showError(
          error instanceof Error
            ? error.message
            : "Registration could not be completed."
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function switchToRegister() {
    clearFeedback();
    setPassword("");
    setConfirmPassword("");
    onRegisterClick();
  }

  function switchToLogin() {
    clearFeedback();
    setPassword("");
    setConfirmPassword("");
    onLoginClick();
  }

  return (
    <section
      className="auth-card"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-title"
    >
      <button
        type="button"
        className="close-button"
        onClick={onXClick}
        aria-label="Close authentication window"
      >
        ×
      </button>

      <p className="section-eyebrow">
        {isLogin ? "Welcome back" : "Create your account"}
      </p>

      <h2 id="auth-title">{isLogin ? "Log in" : "Register"}</h2>

      <p className="auth-introduction">
        {isLogin
          ? "Log in to save attractions and manage your Manhattan itineraries."
          : "Create an account to save places and keep your itineraries together."}
      </p>

      {/*
        A plain link, not fetch: the backend answers with a redirect to Google,
        and only a full page navigation lets the browser follow it.
      */}
      <a className="google-signin-button" href="/api/auth/google/login">
        Continue with Google
      </a>

      {/*
        Always shown, whatever was typed, so the login form never reveals
        which emails belong to Google-only accounts.
      */}
      <p className="google-signin-hint">
        Signed up with Google? Use the button above instead of a password.
      </p>

      <p className="auth-divider">
        <span>or use your email</span>
      </p>

      <form onSubmit={isLogin ? handleLogin : handleRegister}>
        {!isLogin && (
          <label>
            Display name
            <input
              type="text"
              placeholder="What should we call you?"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="name"
              disabled={isSubmitting}
            />
          </label>
        )}

        <label>
          Email address
          <input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            disabled={isSubmitting}
          />
        </label>

        <label>
          Password
          <input
            type="password"
            placeholder={
              isLogin ? "Enter your password" : "At least 6 characters"
            }
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={isLogin ? "current-password" : "new-password"}
            disabled={isSubmitting}
          />
        </label>

        {!isLogin && (
          <label>
            Confirm password
            <input
              type="password"
              placeholder="Enter the same password again"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              autoComplete="new-password"
              disabled={isSubmitting}
            />
          </label>
        )}

        {!isLogin && (
          <label className="accessibility-option">
            <input
              type="checkbox"
              checked={accessibility}
              onChange={(event) => setAccessibility(event.target.checked)}
              disabled={isSubmitting}
            />

            <span className="accessibility-option-check" aria-hidden="true" />

            <span>
              <strong>I need wheelchair-accessible attractions</strong>
              <small>
                Accessible places will be prioritised and warnings will be
                shown when accessibility information is unavailable.
              </small>
            </span>
          </label>
        )}

        {isLogin && (
          <p className="forgot-password">
            Password recovery is not available yet.
          </p>
        )}

        {authMessage && (
          <p
            className={isError ? "auth-message error" : "auth-message success"}
            role={isError ? "alert" : "status"}
          >
            {authMessage}
          </p>
        )}

        <button
          type="submit"
          className="auth-submit-button"
          disabled={isSubmitting}
        >
          {isSubmitting
            ? isLogin
              ? "Logging in..."
              : "Creating account..."
            : isLogin
              ? "Log in"
              : "Create account"}
        </button>
      </form>

      {isLogin && !EMAIL_SIGNUP_ENABLED ? (
        <p className="signup-link">
          New to Offpeak? Continue with Google to create your account.
        </p>
      ) : (
        <p className="signup-link">
          {isLogin ? "New to Offpeak? " : "Already have an account? "}

          <button
            type="button"
            className="auth-switch-button"
            onClick={isLogin ? switchToRegister : switchToLogin}
            disabled={isSubmitting}
          >
            {isLogin ? "Create an account" : "Log in"}
          </button>
        </p>
      )}
    </section>
  );
}

export default AuthForm;
