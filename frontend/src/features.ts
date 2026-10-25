/*
  Product switches that are expected to flip back on later.

  Email + password sign-up stays hidden until the backend rate-limits the
  auth endpoints; until then new users sign up with Google. Existing password
  accounts can still log in.
*/
export const EMAIL_SIGNUP_ENABLED = false;
