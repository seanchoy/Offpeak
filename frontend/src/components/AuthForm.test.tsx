import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AuthForm from "./AuthForm";

function renderForm(authMode: "login" | "register" = "login") {
  const noop = () => {};
  render(
    <AuthForm
      authMode={authMode}
      onXClick={noop}
      onLoginClick={noop}
      onRegisterClick={noop}
    />
  );
}

describe("Part2 Google button", () => {
  it("links to the backend Google login route", () => {
    renderForm();

    const link = screen.getByRole("link", { name: /continue with google/i });

    expect(link).toHaveAttribute("href", "/api/auth/google/login");
  });

  it("is offered on the register form too", () => {
    renderForm("register");

    expect(
      screen.getByRole("link", { name: /continue with google/i })
    ).toBeInTheDocument();
  });

  it("tells Google users where to sign in", () => {
    renderForm();

    expect(screen.getByText(/signed up with google/i)).toBeInTheDocument();
  });
});
