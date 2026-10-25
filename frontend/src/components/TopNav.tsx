import type { AuthUser } from "../types";
import offpeakLogo from "../assets/offpeak-logo-blue.png";

type TopNavProps = {
  currentPage: string;
  onPageChange: (page: string) => void;

  /*
    I keep these props optional so the navigation remains reusable in logged-in and logged-out states.
    This keeps the project building while we update one file at a time.
  */
  user?: AuthUser | null;
  onLoginClick?: () => void;
  onRegisterClick?: () => void;
  onLogoutClick?: () => void;
};

function getInitials(displayName: string): string {
  const parts = displayName
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  if (parts.length === 0) {
    return "U";
  }

  if (parts.length === 1) {
    return parts[0].charAt(0).toUpperCase();
  }

  return `${parts[0].charAt(0)}${parts[parts.length - 1].charAt(0)}`.toUpperCase();
}

function TopNav({
  currentPage,
  onPageChange,
  user = null,
  onLoginClick,
  onRegisterClick,
  onLogoutClick,
}: TopNavProps) {
  function navigate(page: string) {
    onPageChange(page);
  }

  return (
    <nav className="top-nav" aria-label="Main navigation">
      <div className="top-nav-inner">
        {/*
          The brand is a navigation control, but CSS will remove the normal
          button appearance so it displays as a proper wordmark.
        */}
        <button
          type="button"
          className="top-nav-brand"
          onClick={() => navigate("explore")}
          aria-label="Offpeak home"
        >
          <span className="top-nav-brand-mark" aria-hidden="true">
            <img src={offpeakLogo} alt="" />
          </span>

          <span className="top-nav-brand-name">Offpeak</span>
        </button>

        <div className="top-nav-links">
          <button
            type="button"
            className={currentPage === "explore" ? "active" : ""}
            onClick={() => navigate("explore")}
            aria-current={currentPage === "explore" ? "page" : undefined}
          >
            Explore
          </button>

          <button
            type="button"
            className={currentPage === "ai" ? "active" : ""}
            onClick={() => navigate("ai")}
            aria-current={currentPage === "ai" ? "page" : undefined}
          >
            AI Planner
          </button>

          <button
            type="button"
            className={currentPage === "itinerary" ? "active" : ""}
            onClick={() => navigate("itinerary")}
            aria-current={currentPage === "itinerary" ? "page" : undefined}
          >
            My Itinerary
          </button>

          <button
            type="button"
            className={currentPage === "saved" ? "active" : ""}
            onClick={() => navigate("saved")}
            aria-current={currentPage === "saved" ? "page" : undefined}
          >
            Saved
          </button>

          {user && (
            <button
              type="button"
              className={currentPage === "profile" ? "active" : ""}
              onClick={() => navigate("profile")}
              aria-current={currentPage === "profile" ? "page" : undefined}
            >
              Profile
            </button>
          )}
        </div>

        <div className="top-nav-account">
          {user ? (
            <>
              <button
                type="button"
                className="top-nav-user"
                onClick={() => navigate("profile")}
                aria-label={`Open ${user.displayName}'s profile`}
              >
                <span className="top-nav-user-name">
                  {user.displayName}
                </span>

                <span className="top-nav-avatar" aria-hidden="true">
                  {getInitials(user.displayName)}
                </span>
              </button>

              {onLogoutClick && (
                <button
                  type="button"
                  className="top-nav-logout"
                  onClick={onLogoutClick}
                >
                  Log out
                </button>
              )}
            </>
          ) : (
            <div className="top-nav-auth-actions">
              <button
                type="button"
                className="top-nav-login"
                onClick={onLoginClick}
              >
                Log in
              </button>

              {onRegisterClick && (
                <button
                  type="button"
                  className="top-nav-register"
                  onClick={onRegisterClick}
                >
                  Register
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

export default TopNav;