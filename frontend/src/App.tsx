import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import "./App.css";

import AIPlanner from "./components/AiPlanner";
import AttractionCard from "./components/AttractionCard";
import AuthForm from "./components/AuthForm";
import BusynessChart from "./components/BusynessChart";
import CategoryTabs from "./components/CategoryTabs";
import GoogleMapsCredit from "./components/GoogleMapsCredit";
import ItineraryDetail from "./components/ItineraryDetail";
import MyItinerary from "./components/MyItinerary";
import PhotoCredit from "./components/PhotoCredit";
import Profile from "./components/Profile";
import SavedItineraries from "./components/SavedItineraries";
import SearchBar from "./components/SearchBar";
import TopNav from "./components/TopNav";
import WelcomePage from "./components/WelcomePage";
import poiPhotoFallback from "./assets/poi-photo-fallback.svg";

import {
  apiFetch,
  AUTHENTICATION_REQUIRED_EVENT,
} from "./api";

import { getAuthErrorMessage } from "./auth/authError";
import { EMAIL_SIGNUP_ENABLED } from "./features";
import { fetchPhotoAttribution, isGooglePlacesPhoto } from "./poiPhoto";
import type { PhotoAttribution } from "./poiPhoto";
import { fetchCurrentUser } from "./auth/currentUser";

import {
  confirmedAccessibilityLabels,
  formatAccessibilityLabel,
  isWheelchairAccessible,
} from "./accessibility";

import type {
  ApiMessageResponse,
  AuthMode,
  AuthUser,
  ItineraryResponse,
  PoiCrowdForecast,
  Poi,
  ProfilePreferences,
} from "./types";

type Page =
  | "explore"
  | "ai"
  | "itinerary"
  | "saved"
  | "profile"
  | "welcome";

const PAGE_PATHS: Record<Page, string> = {
  explore: "/explore",
  ai: "/planner",
  itinerary: "/itinerary",
  saved: "/saved",
  profile: "/profile",
  welcome: "/welcome",
};

const PROTECTED_PAGES: Page[] = ["itinerary", "saved", "profile", "welcome"];

function normalisePath(pathname: string): string {
  return pathname.length > 1
    ? pathname.replace(/\/+$/, "")
    : pathname;
}

function getPageFromPath(pathname: string): Page {
  const path = normalisePath(pathname);

  if (path === "/planner") {
    return "ai";
  }

  /*
    A saved itinerary detail page still belongs to the My Itinerary area, so the
    nav keeps that tab highlighted while /itinerary/{id} is open.
  */
  if (path === "/itinerary" || /^\/itinerary\/[^/]+$/.test(path)) {
    return "itinerary";
  }

  if (path === "/saved") {
    return "saved";
  }

  if (path === "/profile") {
    return "profile";
  }

  if (path === "/welcome") {
    return "welcome";
  }

  return "explore";
}

function getPoiSlugFromPath(pathname: string): string | null {
  const match = normalisePath(pathname).match(/^\/explore\/([^/]+)$/);

  if (!match) {
    return null;
  }

  try {
    return decodeURIComponent(match[1]);
  } catch {
    return null;
  }
}

function getItineraryIdFromPath(pathname: string): string | null {
  const match = normalisePath(pathname).match(/^\/itinerary\/([^/]+)$/);

  if (!match) {
    return null;
  }

  try {
    return decodeURIComponent(match[1]);
  } catch {
    return null;
  }
}

function isKnownAppPath(pathname: string): boolean {
  const path = normalisePath(pathname);

  return (
    Object.values(PAGE_PATHS).includes(path) ||
    /^\/explore\/[^/]+$/.test(path) ||
    /^\/itinerary\/[^/]+$/.test(path)
  );
}

const USER_STORAGE_KEY = "offpeak_user";
const PROFILE_PREFERENCES_KEY = "offpeak_profile_preferences";

type ForecastPeriod = "today" | "tomorrow" | "weekend";

/*
  Reads the locally stored display information for the logged-in user.

  The actual authentication token is not stored here. It remains inside
  the backend's secure HttpOnly cookie.
*/
function loadStoredUser(): AuthUser | null {
  try {
    const storedUser = localStorage.getItem(USER_STORAGE_KEY);

    if (!storedUser) {
      return null;
    }

    const parsedUser = JSON.parse(storedUser) as Partial<AuthUser>;

    if (
      typeof parsedUser.email !== "string" ||
      typeof parsedUser.displayName !== "string"
    ) {
      localStorage.removeItem(USER_STORAGE_KEY);
      return null;
    }

    return {
      email: parsedUser.email,
      displayName: parsedUser.displayName,
      accessibility: parsedUser.accessibility === true,
    };
  } catch (error) {
    console.error("Could not read the stored user:", error);
    localStorage.removeItem(USER_STORAGE_KEY);
    return null;
  }
}

/* Remembers the signed-in user's display information on this device. */
function saveStoredUser(user: AuthUser): void {
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

/*
  The preference is kept on this device until the backend exposes a profile
  preference endpoint. App owns it so Explore, Profile and My Itinerary all
  use the same value immediately.
*/
function getProfilePreferencesKey(user: AuthUser): string {
  return `${PROFILE_PREFERENCES_KEY}:${user.email.trim().toLowerCase()}`;
}

function loadProfilePreferences(
  user: AuthUser | null
): ProfilePreferences {
  const fallback: ProfilePreferences = {
    stepFreeRoutes: user?.accessibility === true,
  };

  if (!user) {
    return fallback;
  }

  try {
    const accountKey = getProfilePreferencesKey(user);
    const stored =
      localStorage.getItem(accountKey) ??
      localStorage.getItem(PROFILE_PREFERENCES_KEY);

    if (!stored) {
      return fallback;
    }

    const parsed = JSON.parse(stored) as Partial<ProfilePreferences>;
    const preferences = {
      stepFreeRoutes: parsed.stepFreeRoutes === true,
    };

    /*
      I migrate the earlier device-wide value to this account so existing
      users keep their selection without exposing it to other accounts.
    */
    if (!localStorage.getItem(accountKey)) {
      localStorage.setItem(accountKey, JSON.stringify(preferences));
      localStorage.removeItem(PROFILE_PREFERENCES_KEY);
    }

    return preferences;
  } catch {
    return fallback;
  }
}

/*
  Returns true when a backend error means that the user needs to log in.
*/
function isAuthenticationError(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false;
  }

  const message = error.message.toLowerCase();

  return (
    message.includes("log in") ||
    message.includes("not authenticated") ||
    message.includes("authentication") ||
    message.includes("access token") ||
    message.includes("refresh token")
  );
}

/*
  Creates readable recommendation wording without pretending that forecast
  data exists when the backend has not returned it.
*/
function getBestTimeLabel(poi: Poi): string {
  if (poi.best_time_label?.trim()) {
    return poi.best_time_label;
  }

  return "Recommendation pending";
}

function getNewYorkHour(): number {
  const hour = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    hour: "numeric",
    hourCycle: "h23",
  }).format(new Date());

  return Number(hour);
}

function getCardCrowdSummary(
  forecast: PoiCrowdForecast,
  isClosedToday: boolean
): string {
  if (forecast.today.length === 0) {
    return isClosedToday ? "Not open today" : "Forecast unavailable";
  }

  const currentHour = getNewYorkHour();
  const currentForecast = forecast.today.find(
    (entry) => entry.hour_of_day === currentHour
  );
  const selectedForecast =
    currentForecast ??
    forecast.today.reduce((quietest, entry) =>
      entry.busyness < quietest.busyness ? entry : quietest
    );
  const percentage = Math.round(selectedForecast.busyness);
  const level =
    percentage <= 35
      ? "Quiet"
      : percentage <= 65
        ? "Moderate"
        : "Busy";

  return currentForecast
    ? `${level} now · ${percentage}%`
    : `${level} period · ${percentage}%`;
}

/*
  I show up to six real readings spread across the available daytime forecast.
  Some periods contain fewer readings, so I preserve the honest API coverage
  instead of inventing percentages just to fill every chart position.
*/
function selectForecastSlots(
  hours: PoiCrowdForecast[ForecastPeriod]
): PoiCrowdForecast[ForecastPeriod] {
  const daytimeHours = hours.filter(
    (entry) => entry.hour_of_day >= 10 && entry.hour_of_day <= 20
  );

  if (daytimeHours.length <= 6) {
    return daytimeHours;
  }

  const finalIndex = daytimeHours.length - 1;
  const selectedIndexes = Array.from({ length: 6 }, (_, index) =>
    Math.round((index * finalIndex) / 5)
  );

  return selectedIndexes.map((index) => daytimeHours[index]);
}

const openingHourDays = [
  ["mon", "Monday"],
  ["tue", "Tuesday"],
  ["wed", "Wednesday"],
  ["thu", "Thursday"],
  ["fri", "Friday"],
  ["sat", "Saturday"],
  ["sun", "Sunday"],
] as const;

type OpeningHourDayKey = (typeof openingHourDays)[number][0];

function getNewYorkOpeningHourDay(): OpeningHourDayKey {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    weekday: "short",
  })
    .format(new Date())
    .toLowerCase() as OpeningHourDayKey;
}

/*
  I only treat an attraction as closed when its structured schedule explicitly
  contains no periods for today. Missing opening-hours data remains unknown.
*/
function isPoiClosedToday(poi: Poi): boolean {
  if (!poi.opening_hours) {
    return false;
  }

  const today = getNewYorkOpeningHourDay();

  if (!Object.hasOwn(poi.opening_hours, today)) {
    return false;
  }

  const periods = poi.opening_hours[today];
  return periods === null || (Array.isArray(periods) && periods.length === 0);
}

function formatOpeningTime(value: string): string {
  const [hourText, minute = "00"] = value.split(":");
  const hour = Number(hourText);

  if (!Number.isInteger(hour) || hour < 0 || hour > 23) {
    return value;
  }

  const displayHour = hour % 12 || 12;
  const displayMinute = minute === "00" ? "" : `:${minute}`;
  return `${displayHour}${displayMinute} ${hour >= 12 ? "PM" : "AM"}`;
}

/*
  I format the structured hours returned by the API instead of printing the
  legacy text field, which can contain damaged dash characters.
*/
function formatOpeningHours(poi: Poi): string[] {
  if (poi.opening_hours) {
    const lines = openingHourDays.map(([key, label]) => {
      const periods = poi.opening_hours?.[key];

      if (!Array.isArray(periods) || periods.length === 0) {
        return `${label}: Closed`;
      }

      const formattedPeriods = periods
        .filter(
          (period): period is [string, string] =>
            Array.isArray(period) &&
            typeof period[0] === "string" &&
            typeof period[1] === "string"
        )
        .map(
          ([start, end]) =>
            `${formatOpeningTime(start)}–${formatOpeningTime(end)}`
        );

      return `${label}: ${formattedPeriods.join(", ") || "Closed"}`;
    });

    return lines;
  }

  if (poi.opening_hours_text?.trim()) {
    return poi.opening_hours_text.split(";").map((line) =>
      line
        .trim()
        .replace(/[^\x20-\x7E]+/g, "–")
        .replace(/–+/g, "–")
    );
  }

  return ["Not currently available"];
}

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const currentPage = getPageFromPath(location.pathname);
  const routePoiSlug = getPoiSlugFromPath(location.pathname);
  const routeItineraryId = getItineraryIdFromPath(location.pathname);
  const isProtectedPage = PROTECTED_PAGES.includes(currentPage);

  /*
    Authentication state.

    The display information is restored from localStorage when the app opens.
    Backend requests still depend on the HttpOnly authentication cookie.
  */
  const [user, setUser] = useState<AuthUser | null>(loadStoredUser);
  /*
    A failed Google sign-in comes back as /?auth_error=<code>. The message is
    read once on first render, before the redirect below drops the query, and
    the login modal starts open to show it.
  */
  const [authError, setAuthError] = useState<string | null>(() =>
    getAuthErrorMessage(window.location.search)
  );
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(authError !== null);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  /*
    False until the backend has said who the cookie belongs to. Protected pages
    wait for it, so /welcome does not flash "please log in" straight after a
    Google redirect.
  */
  const [hasCheckedSession, setHasCheckedSession] = useState(false);
  const [profilePreferences, setProfilePreferences] =
    useState<ProfilePreferences>(() => loadProfilePreferences(user));

  const [aiGeneratedItinerary, setAiGeneratedItinerary] =
    useState<ItineraryResponse | null>(null);

  /*
    POI API state.
  */
  const [pois, setPois] = useState<Poi[]>([]);
  const [isLoadingPois, setIsLoadingPois] = useState(true);
  const [poiError, setPoiError] = useState("");
  const selectedPoi = routePoiSlug
    ? pois.find((poi) => poi.slug === routePoiSlug) ?? null
    : null;
  const isPoiDetailRoute = routePoiSlug !== null;
  const [selectedPoiForecast, setSelectedPoiForecast] =
    useState<PoiCrowdForecast | null>(null);
  const [isLoadingForecasts, setIsLoadingForecasts] = useState(false);
  const [forecastError, setForecastError] = useState("");
  const [forecastPeriod, setForecastPeriod] =
    useState<ForecastPeriod>("today");
  const [photoAttribution, setPhotoAttribution] = useState<{
    slug: string;
    attribution: PhotoAttribution;
  } | null>(null);
  const selectedPoiSlug = selectedPoi?.slug;
  const selectedPoiIsClosedToday = selectedPoi
    ? isPoiClosedToday(selectedPoi)
    : false;
  /*
    Only confirmed labels are listed. A place tagged as having limited
    wheelchair access falls through to the same fallback as a place with no
    OSM data at all, because partial access is not access.
  */
  const selectedPoiAccessibility = confirmedAccessibilityLabels(
    selectedPoi?.accessibility_labels
  );
  const [crowdSummaryBySlug, setCrowdSummaryBySlug] = useState<
    Record<string, string>
  >({});
  const crowdSummaryCacheRef = useRef<Record<string, string>>({});
  const loadingCrowdSlugsRef = useRef(new Set<string>());

  /*
    I keep the address bar canonical so direct links and browser history use
    the same page URLs as navigation inside the app.
  */
  useEffect(() => {
    if (location.pathname === "/" || !isKnownAppPath(location.pathname)) {
      navigate(PAGE_PATHS.explore, { replace: true });
    }
  }, [location.pathname, navigate]);

  /* Drop a Google error from the URL so a refresh does not show it again. */
  useEffect(() => {
    if (!authError) {
      return;
    }

    const url = new URL(window.location.href);
    url.searchParams.delete("auth_error");
    window.history.replaceState(window.history.state, "", url);
  }, [authError]);

  /*
    Card forecasts are loaded lazily and cached by slug. Duplicate cards in
    Featured and All Attractions therefore share one backend request.
  */
  const requestCardCrowdSummary = useCallback(async (slug: string) => {
    if (
      crowdSummaryCacheRef.current[slug] ||
      loadingCrowdSlugsRef.current.has(slug)
    ) {
      return;
    }

    const poi = pois.find((item) => item.slug === slug);
    const isClosedToday = poi ? isPoiClosedToday(poi) : false;

    loadingCrowdSlugsRef.current.add(slug);

    try {
      const forecast = await apiFetch<PoiCrowdForecast>(
        `/api/pois/${encodeURIComponent(slug)}/crowd-forecast`
      );
      const summary = getCardCrowdSummary(forecast, isClosedToday);

      crowdSummaryCacheRef.current[slug] = summary;
      setCrowdSummaryBySlug((current) => ({
        ...current,
        [slug]: summary,
      }));
    } catch (error) {
      console.info(`Card forecast was not loaded for ${slug}:`, error);
      const summary = isClosedToday
        ? "Not open today"
        : "Forecast unavailable";

      crowdSummaryCacheRef.current[slug] = summary;
      setCrowdSummaryBySlug((current) => ({
        ...current,
        [slug]: summary,
      }));
    } finally {
      loadingCrowdSlugsRef.current.delete(slug);
    }
  }, [pois]);

  /*
    Explore search and filter state.
  */
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [accessibleOnly, setAccessibleOnly] = useState(false);

  /*
    Saved POI state.
  */
  const [savedPoiSlugs, setSavedPoiSlugs] = useState<string[]>([]);
  const [savingPoiSlug, setSavingPoiSlug] = useState<string | null>(
    null
  );
  const [savePoiMessage, setSavePoiMessage] = useState("");
  const [savePoiMessageType, setSavePoiMessageType] = useState<
    "success" | "error"
  >("success");
  const [pendingAccessibleSave, setPendingAccessibleSave] =
    useState<Poi | null>(null);

  /*
    Load all POIs when the application starts.
  */
  useEffect(() => {
    let isCancelled = false;

    async function loadPois() {
      try {
        setIsLoadingPois(true);
        setPoiError("");

        const data = await apiFetch<Poi[]>("/api/pois");

        if (!isCancelled) {
          setPois(Array.isArray(data) ? data : []);
        }
      } catch (error) {
        console.error("Failed to load POIs:", error);

        if (!isCancelled) {
          setPoiError(
            error instanceof Error
              ? error.message
              : "Attractions could not be loaded."
          );
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingPois(false);
        }
      }
    }

    loadPois();

    return () => {
      isCancelled = true;
    };
  }, []);

  /*
    The crowd endpoint belongs to one attraction, so I request it only when
    that POI is opened. This avoids sending 198 separate requests on Explore.
  */
  useEffect(() => {
    if (!selectedPoiSlug) {
      return;
    }

    const slug = selectedPoiSlug;
    let isCancelled = false;

    async function loadCrowdForecast() {
      try {
        setIsLoadingForecasts(true);
        setForecastError("");

        const data = await apiFetch<PoiCrowdForecast>(
          `/api/pois/${encodeURIComponent(slug)}/crowd-forecast`
        );

        if (!isCancelled) {
          setSelectedPoiForecast(data);
        }
      } catch (error) {
        console.error("Failed to load the crowd forecast:", error);

        if (!isCancelled) {
          setSelectedPoiForecast(null);
          setForecastError(
            "Hourly crowd forecasts are temporarily unavailable."
          );
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingForecasts(false);
        }
      }
    }

    void loadCrowdForecast();

    return () => {
      isCancelled = true;
    };
  }, [selectedPoiSlug]);

  /*
    Credit the photographer of a Google Places hero photo (required by the
    Google Maps Platform terms). Keyed by slug so a slow response for the
    previous attraction can never be shown under the next one.
  */
  const selectedPoiUsesGooglePhoto = selectedPoi
    ? isGooglePlacesPhoto(selectedPoi.hero_image_url, selectedPoi.slug)
    : false;

  useEffect(() => {
    if (!selectedPoiSlug || !selectedPoiUsesGooglePhoto) {
      return;
    }

    let isCancelled = false;

    void fetchPhotoAttribution(selectedPoiSlug).then((attribution) => {
      if (!isCancelled && attribution) {
        setPhotoAttribution({ slug: selectedPoiSlug, attribution });
      }
    });

    return () => {
      isCancelled = true;
    };
  }, [selectedPoiSlug, selectedPoiUsesGooglePhoto]);

  const selectedPhotoAttribution =
    photoAttribution && photoAttribution.slug === selectedPoiSlug
      ? photoAttribution.attribution
      : null;

  /* Clear local display state after the backend session ends. */
  const handleLocalLogout = useCallback(() => {
    localStorage.removeItem(USER_STORAGE_KEY);
    setUser(null);
    setProfilePreferences({ stepFreeRoutes: false });
    setSavedPoiSlugs([]);
    setPendingAccessibleSave(null);
  }, [
    setPendingAccessibleSave,
    setProfilePreferences,
    setSavedPoiSlugs,
    setUser,
  ]);

  /*
    The API helper emits one shared event when neither authentication cookie
    can recover the session. Returning to Explore unmounts protected pages
    before their parallel requests can repeatedly reopen the login modal.
  */
  useEffect(() => {
    function handleAuthenticationRequired() {
      handleLocalLogout();
      navigate(PAGE_PATHS.explore, { replace: true });
      setAuthMode("login");
      setIsAuthModalOpen(true);
    }

    window.addEventListener(
      AUTHENTICATION_REQUIRED_EVENT,
      handleAuthenticationRequired
    );

    return () => {
      window.removeEventListener(
        AUTHENTICATION_REQUIRED_EVENT,
        handleAuthenticationRequired
      );
    };
  }, [handleLocalLogout, navigate]);

  /*
    On first load, ask the backend who is signed in. This is how a Google
    sign-in reaches the app (it arrives as a redirect, not a JSON response),
    and it also clears a stale localStorage entry once the cookies expire.
  */
  useEffect(() => {
    let isCancelled = false;

    async function checkSession() {
      try {
        const currentUser = await fetchCurrentUser();

        if (isCancelled) {
          return;
        }

        if (currentUser) {
          saveStoredUser(currentUser);
          setUser(currentUser);
          setProfilePreferences(loadProfilePreferences(currentUser));
        } else {
          handleLocalLogout();
        }
      } catch (error) {
        /*
          A server or network problem says nothing about the session, so the
          stored display state is kept.
        */
        console.info("The session could not be checked:", error);
      } finally {
        if (!isCancelled) {
          setHasCheckedSession(true);
        }
      }
    }

    void checkSession();

    return () => {
      isCancelled = true;
    };
  }, [handleLocalLogout]);

  /*
    I update the shared saved-place state when a place is removed from the
    Saved page so the Explore heart changes immediately without a refresh.
  */
  const handleSavedPlaceRemoved = useCallback((slug: string) => {
    setSavedPoiSlugs((currentSavedSlugs) =>
      currentSavedSlugs.filter((savedSlug) => savedSlug !== slug)
    );
  }, []);

  /*
    Load saved attractions only when the frontend considers the user logged in.

    This prevents protected API calls from showing token errors to logged-out
    visitors.
  */
  useEffect(() => {
    let isCancelled = false;

    async function loadSavedPois() {
      if (!user) {
        setSavedPoiSlugs([]);
        return;
      }

      try {
        const savedPois = await apiFetch<Poi[]>(
          "/api/users/me/saved-pois"
        );

        if (!isCancelled) {
          setSavedPoiSlugs(
            Array.isArray(savedPois)
              ? savedPois.map((poi) => poi.slug)
              : []
          );
        }
      } catch (error) {
        console.info("Saved POIs were not loaded:", error);

        if (!isCancelled && isAuthenticationError(error)) {
          /*
            The local display state may remain after the secure cookie expires.
            Clear it so the interface returns to the logged-out state.
          */
          localStorage.removeItem(USER_STORAGE_KEY);
          setUser(null);
          setProfilePreferences({ stepFreeRoutes: false });
          setSavedPoiSlugs([]);
          setPendingAccessibleSave(null);
        }
      }
    }

    loadSavedPois();

    return () => {
      isCancelled = true;
    };
  }, [user]);

  /*
    Search by name, neighbourhood, borough, or POI type.

    Category and accessibility filtering are applied after the text search.
  */
  const normalisedSearchTerm = searchTerm.trim().toLowerCase();

  const filteredPois = pois.filter((poi) => {
    const matchesSearch =
      normalisedSearchTerm === "" ||
      poi.name.toLowerCase().includes(normalisedSearchTerm) ||
      poi.type.toLowerCase().includes(normalisedSearchTerm) ||
      poi.borough.toLowerCase().includes(normalisedSearchTerm) ||
      (poi.neighborhood ?? "")
        .toLowerCase()
        .includes(normalisedSearchTerm);

    const matchesCategory =
      selectedCategory === "all" ||
      poi.type.toLowerCase() === selectedCategory.toLowerCase();

    const matchesAccessibility =
      !accessibleOnly || isWheelchairAccessible(poi);

    return (
      matchesSearch &&
      matchesCategory &&
      matchesAccessibility
    );
  });

  /*
    Category totals follow the current search and accessibility filter.
    This lets each tab show how many matching places it contains.
  */
  const categoryCounts = pois.reduce<Record<string, number>>(
    (counts, poi) => {
      const matchesSearch =
        normalisedSearchTerm === "" ||
        poi.name.toLowerCase().includes(normalisedSearchTerm) ||
        poi.type.toLowerCase().includes(normalisedSearchTerm) ||
        poi.borough.toLowerCase().includes(normalisedSearchTerm) ||
        (poi.neighborhood ?? "")
          .toLowerCase()
          .includes(normalisedSearchTerm);

      const matchesAccessibility =
        !accessibleOnly || isWheelchairAccessible(poi);

      if (!matchesSearch || !matchesAccessibility) {
        return counts;
      }

      const type = poi.type.toLowerCase();
      counts.all = (counts.all ?? 0) + 1;
      counts[type] = (counts[type] ?? 0) + 1;

      return counts;
    },
    { all: 0 }
  );

  const filtersActive =
    normalisedSearchTerm !== "" ||
    selectedCategory !== "all" ||
    accessibleOnly;

  function clearExploreFilters() {
    setSearchTerm("");
    setSelectedCategory("all");
    setAccessibleOnly(false);
  }

  /*
    Recommended attractions are chosen from POIs containing genuine
    best-time data from the backend.
  */
  const featuredPois = [...pois]
    .filter(
      (poi) =>
        Boolean(poi.best_time_label?.trim()) &&
        poi.google_review_star !== null
    )
    .sort((firstPoi, secondPoi) => {
      const ratingDifference =
        (secondPoi.google_review_star ?? 0) -
        (firstPoi.google_review_star ?? 0);

      if (ratingDifference !== 0) {
        return ratingDifference;
      }

      return (
        (secondPoi.google_review_count ?? 0) -
        (firstPoi.google_review_count ?? 0)
      );
    })
    .slice(0, 4);

  /*
    When the profile preference is enabled, I show every attraction with
    confirmed accessibility before the complete attraction list. I do not
    limit this section because the preference is intended to surface all
    suitable options, not only a small featured sample.
  */
  const accessiblePreferredPois = [...pois]
    .filter(isWheelchairAccessible)
    .sort((firstPoi, secondPoi) => {
      const ratingDifference =
        (secondPoi.google_review_star ?? 0) -
        (firstPoi.google_review_star ?? 0);

      if (ratingDifference !== 0) {
        return ratingDifference;
      }

      return (
        (secondPoi.google_review_count ?? 0) -
        (firstPoi.google_review_count ?? 0)
      );
    });

  function openLogin() {
    setAuthMode("login");
    setIsAuthModalOpen(true);
  }

  function openRegister() {
    setAuthMode("register");
    setIsAuthModalOpen(true);
  }

  function closeAuthModal() {
    setIsAuthModalOpen(false);
    setAuthError(null);
  }

  function switchToLogin() {
    setAuthMode("login");
  }

  function handleAuthenticationSuccess(authenticatedUser: AuthUser) {
    setUser(authenticatedUser);
    setProfilePreferences(
      loadProfilePreferences(authenticatedUser)
    );
    setIsAuthModalOpen(false);
    setAuthError(null);
    setSavePoiMessage("");
  }

  /*
    After the welcome page the saved (or unchanged) details become the
    signed-in user, and the accessibility choice becomes this account's
    step-free preference.
  */
  function handleWelcomeDone(updatedUser: AuthUser) {
    const preferences = { stepFreeRoutes: updatedUser.accessibility };

    saveStoredUser(updatedUser);
    setUser(updatedUser);
    setProfilePreferences(preferences);
    localStorage.setItem(
      getProfilePreferencesKey(updatedUser),
      JSON.stringify(preferences)
    );
    navigate(PAGE_PATHS.explore, { replace: true });
  }

  function updateProfilePreferences(preferences: ProfilePreferences) {
    setProfilePreferences(preferences);

    if (user) {
      localStorage.setItem(
        getProfilePreferencesKey(user),
        JSON.stringify(preferences)
      );
    }
  }

  async function handleLogout() {
    try {
      /*
        Logout is requested from the backend so its secure cookies can be
        cleared. Local state is cleared even if the backend is unavailable.
      */
      await apiFetch<ApiMessageResponse>("/api/auth/logout", {
        method: "POST",
      });
    } catch (error) {
      console.info(
        "The backend logout request did not complete:",
        error
      );
    } finally {
      handleLocalLogout();

      if (isProtectedPage) {
        navigate(PAGE_PATHS.explore, { replace: true });
      }
    }
  }

  function goToPage(page: string) {
    if (!Object.hasOwn(PAGE_PATHS, page)) {
      return;
    }

    const nextPage = page as Page;

    /*
      Profile, Saved and My Itinerary are account areas.

      Opening them while logged out displays the login modal rather than a
      technical authentication error.
    */
    if (
      (nextPage === "profile" ||
        nextPage === "saved" ||
        nextPage === "itinerary") &&
      !user
    ) {
      openLogin();
      return;
    }

    navigate(PAGE_PATHS[nextPage]);
    setSavePoiMessage("");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  async function updateSavedPoi(slug: string) {
    if (!user) {
      setSavePoiMessageType("error");
      setSavePoiMessage(
        "You need to log in to save attractions."
      );
      openLogin();
      return;
    }

    const isCurrentlySaved = savedPoiSlugs.includes(slug);

    setSavePoiMessage("");

    try {
      setSavingPoiSlug(slug);

      const response = await apiFetch<ApiMessageResponse>(
        `/api/pois/${slug}/save`,
        {
          method: isCurrentlySaved ? "DELETE" : "POST",
        }
      );

      setSavedPoiSlugs((currentSavedSlugs) => {
        if (isCurrentlySaved) {
          return currentSavedSlugs.filter(
            (savedSlug) => savedSlug !== slug
          );
        }

        if (currentSavedSlugs.includes(slug)) {
          return currentSavedSlugs;
        }

        return [...currentSavedSlugs, slug];
      });

      setSavePoiMessageType("success");
      setSavePoiMessage(
        response.message ||
          (isCurrentlySaved
            ? "Attraction removed from your saved places."
            : "Attraction saved.")
      );
    } catch (error) {
      console.error(
        "Failed to update saved attraction:",
        error
      );

      if (isAuthenticationError(error)) {
        handleLocalLogout();
        setSavePoiMessageType("error");
        setSavePoiMessage(
          "Your session has expired. Please log in again."
        );
        openLogin();
        return;
      }

      setSavePoiMessageType("error");
      setSavePoiMessage(
        error instanceof Error
          ? error.message
          : "The attraction could not be updated."
      );
    } finally {
      setSavingPoiSlug(null);
    }
  }

  function toggleSavePoi(slug: string) {
    const poi = pois.find((item) => item.slug === slug);
    const isCurrentlySaved = savedPoiSlugs.includes(slug);

    if (
      user &&
      poi &&
      !isCurrentlySaved &&
      profilePreferences.stepFreeRoutes &&
      !isWheelchairAccessible(poi)
    ) {
      setPendingAccessibleSave(poi);
      return;
    }

    void updateSavedPoi(slug);
  }

  function renderAttractionCard(poi: Poi) {
    return (
      <AttractionCard
        key={poi.slug}
        slug={poi.slug}
        image={
          poi.hero_image_url ||
          poiPhotoFallback
        }
        name={poi.name}
        crowdLevel={
          crowdSummaryBySlug[poi.slug] ?? "Loading forecast"
        }
        bestTime={getBestTimeLabel(poi)}
        neighborhood={
          poi.neighborhood ||
          poi.borough ||
          "Manhattan"
        }
        rating={poi.google_review_star}
        reviewCount={poi.google_review_count}
        isAccessible={isWheelchairAccessible(poi)}
        isSaved={savedPoiSlugs.includes(poi.slug)}
        isSaving={savingPoiSlug === poi.slug}
        onSaveClick={() => toggleSavePoi(poi.slug)}
        onForecastRequest={requestCardCrowdSummary}
        onClick={() => {
          setSelectedPoiForecast(null);
          setForecastPeriod("today");
          navigate(
            `${PAGE_PATHS.explore}/${encodeURIComponent(poi.slug)}`
          );
          setSavePoiMessage("");

          window.scrollTo({
            top: 0,
            behavior: "smooth",
          });
        }}
      />
    );
  }

  return (
    <div className="app">
      <TopNav
        currentPage={currentPage}
        onPageChange={goToPage}
        user={user}
        onLoginClick={openLogin}
        onRegisterClick={EMAIL_SIGNUP_ENABLED ? openRegister : undefined}
        onLogoutClick={handleLogout}
      />

      <main className="page-container">
        {isProtectedPage && !user && hasCheckedSession && (
          <section className="route-login-card" aria-labelledby="login-required-title">
            <p className="section-eyebrow">Account required</p>
            <h1 id="login-required-title">Please log in to continue</h1>
            <p>
              This page contains your personal Offpeak information and is
              available after you log in.
            </p>
            <div className="route-login-actions">
              <button type="button" onClick={openLogin}>Log in</button>
              <button type="button" onClick={() => goToPage("explore")}>
                Return to Explore
              </button>
            </div>
          </section>
        )}

        {currentPage === "explore" &&
          !isPoiDetailRoute && (
            <>
              <header className="explore-hero">
                <p className="hero-eyebrow">
                  Manhattan Guide
                </p>

                <h1>
                  Explore Manhattan at quieter times
                </h1>

                <p className="hero-subtitle">
                  Find attractions, compare hourly crowd
                  forecasts and plan visits around the times
                  that suit you.
                </p>

                {!user && (
                  <div className="hero-auth-actions">
                    <button
                      type="button"
                      onClick={openLogin}
                    >
                      Log in
                    </button>

                    {EMAIL_SIGNUP_ENABLED && (
                      <button
                        type="button"
                        onClick={openRegister}
                      >
                        Create account
                      </button>
                    )}
                  </div>
                )}

                {user && (
                  <p className="explore-welcome">
                    Welcome back,{" "}
                    <strong>{user.displayName}</strong>.
                  </p>
                )}
              </header>

              <section
                className="explore-filter-shell"
                aria-labelledby="explore-filter-title"
              >
                <h2 id="explore-filter-title" className="sr-only">
                  Search and filter Manhattan attractions
                </h2>

                <SearchBar
                  value={searchTerm}
                  onSearchChange={setSearchTerm}
                />

                <CategoryTabs
                  selectedCategory={selectedCategory}
                  categoryCounts={categoryCounts}
                  onCategoryChange={setSelectedCategory}
                  accessibleOnly={accessibleOnly}
                  onAccessibleOnlyChange={setAccessibleOnly}
                  filtersActive={filtersActive}
                  onClearFilters={clearExploreFilters}
                />
              </section>

              {isLoadingPois && (
                <p className="loading-message">
                  Loading attractions...
                </p>
              )}

              {poiError && (
                <p className="error-message">
                  {poiError}
                </p>
              )}

              {savePoiMessage && (
                <p
                  className={
                    savePoiMessageType === "error"
                      ? "error-message"
                      : "success-message"
                  }
                >
                  {savePoiMessage}
                </p>
              )}

              {!isLoadingPois &&
                !poiError &&
                !filtersActive &&
                profilePreferences.stepFreeRoutes &&
                accessiblePreferredPois.length > 0 && (
                  <section className="featured-section accessible-picks-section">
                    <div className="section-heading-row">
                      <p className="section-eyebrow">
                        Your accessibility preference
                      </p>

                      <h2>Accessible places for you</h2>

                      <p className="section-description">
                        All {accessiblePreferredPois.length} attractions with
                        confirmed wheelchair or step-free access are shown
                        first. The complete attraction list remains available
                        below.
                      </p>
                    </div>

                    <section className="featured-grid">
                      {accessiblePreferredPois.map(renderAttractionCard)}
                    </section>
                  </section>
                )}

              {!isLoadingPois &&
                !poiError &&
                !filtersActive &&
                !profilePreferences.stepFreeRoutes &&
                featuredPois.length > 0 && (
                  <section className="featured-section">
                    <div className="section-heading-row">
                      <p className="section-eyebrow">
                        Data-backed picks
                      </p>

                      <h2>Popular places with quieter times</h2>

                      <p className="section-description">
                        Highly rated attractions with published quieter-time
                        recommendations, ranked by rating and review count.
                      </p>
                    </div>

                    <section className="featured-grid">
                      {featuredPois.map(
                        renderAttractionCard
                      )}
                    </section>

                    <GoogleMapsCredit />
                  </section>
                )}

              {!isLoadingPois && !poiError && (
                <section className="all-attractions-section">
                  <div className="section-heading-row">
                    <p className="section-eyebrow">
                      Browse Manhattan
                    </p>

                    <h2>All attractions</h2>

                    <p className="section-result-count">
                      {filteredPois.length}{" "}
                      {filteredPois.length === 1
                        ? "place"
                        : "places"}
                    </p>
                  </div>

                  {filteredPois.length === 0 ? (
                    <p className="fallback-message">
                      No attractions match the current
                      search and filters.
                    </p>
                  ) : (
                    <>
                      <section className="cards">
                        {filteredPois.map(
                          renderAttractionCard
                        )}
                      </section>

                      <GoogleMapsCredit />
                    </>
                  )}
                </section>
              )}
            </>
          )}

        {currentPage === "explore" &&
          isPoiDetailRoute &&
          isLoadingPois && (
            <p className="fallback-message" role="status">
              Loading attraction details...
            </p>
          )}

        {currentPage === "explore" &&
          isPoiDetailRoute &&
          !isLoadingPois &&
          !poiError &&
          selectedPoi === null && (
            <section className="route-login-card">
              <p className="section-eyebrow">Attraction not found</p>
              <h1>This attraction is unavailable</h1>
              <p>The link may be outdated, or the attraction may have moved.</p>
              <div className="route-login-actions">
                <button type="button" onClick={() => goToPage("explore")}>
                  Return to Explore
                </button>
              </div>
            </section>
          )}

        {currentPage === "explore" &&
          selectedPoi !== null && (
            <section className="poi-detail">
              <button
                type="button"
                className="back-button"
                onClick={() => {
                  goToPage("explore");
                }}
              >
                ← Back to Explore
              </button>

              {savePoiMessage && (
                <p
                  className={
                    savePoiMessageType === "error"
                      ? "error-message"
                      : "success-message"
                  }
                >
                  {savePoiMessage}
                </p>
              )}

              <section className="poi-detail-layout">
                <div className="poi-detail-main">
                  <figure className="poi-detail-hero-figure">
                    <img
                      className="poi-detail-hero"
                      src={
                        selectedPoi.hero_image_url ||
                        poiPhotoFallback
                      }
                      alt={selectedPoi.name}
                      onError={(event) => {
                        if (
                          !event.currentTarget.src.endsWith(
                            "poi-photo-fallback.svg"
                          )
                        ) {
                          event.currentTarget.src = poiPhotoFallback;
                        }
                      }}
                    />

                    {selectedPhotoAttribution && (
                      <PhotoCredit attribution={selectedPhotoAttribution} />
                    )}
                  </figure>

                  <p className="section-eyebrow">
                    {selectedPoi.type}
                  </p>

                  <h1>{selectedPoi.name}</h1>

                  <div className="poi-title-meta">
                    <span>
                      {selectedPoi.neighborhood ||
                        selectedPoi.borough ||
                        "Manhattan"}
                    </span>

                    <span>
                      {selectedPoi.google_review_star
                        ? `★ ${selectedPoi.google_review_star}`
                        : "Rating pending"}
                    </span>

                    <span>
                      {selectedPoi.admission_text ||
                        "Admission details pending"}
                    </span>
                  </div>

                  <p className="poi-summary">
                    {selectedPoi.description ||
                      selectedPoi.summary ||
                      "A full description is not available yet."}
                  </p>

                  <section className="recommendation-panel">
                    <p className="section-eyebrow">
                      Recommended time
                    </p>

                    <h2>
                      {selectedPoi.best_time_label ||
                        "Recommendation pending"}
                    </h2>

                    <p>
                      {selectedPoi.why_this_time ||
                        "Crowd-based timing information has not been published for this attraction yet."}
                    </p>
                  </section>

                  <section className="crowd-chart-panel">
                    <div className="crowd-chart-heading">
                      <div>
                        <p className="section-eyebrow">
                          Crowd information
                        </p>

                        <h2>Hourly crowd forecast</h2>
                      </div>
                    </div>

                    <div
                      className="forecast-period-tabs"
                      role="group"
                      aria-label="Crowd forecast period"
                    >
                      {(["today", "tomorrow", "weekend"] as ForecastPeriod[]).map(
                        (period) => (
                          <button
                            key={period}
                            type="button"
                            className={forecastPeriod === period ? "active" : ""}
                            onClick={() => setForecastPeriod(period)}
                            aria-pressed={forecastPeriod === period}
                          >
                            {period.charAt(0).toUpperCase() + period.slice(1)}
                          </button>
                        )
                      )}
                    </div>

                    {isLoadingForecasts ? (
                      <p className="fallback-message">
                        Loading hourly forecast...
                      </p>
                    ) : (selectedPoiForecast?.[forecastPeriod]?.length ?? 0) > 0 ? (
                      <BusynessChart
                        hours={selectForecastSlots(
                          selectedPoiForecast?.[forecastPeriod] ?? []
                        )}
                        poiName={selectedPoi.name}
                      />
                    ) : (
                      <div className="forecast-status-card" role="status">
                        <span className="forecast-status-icon" aria-hidden="true">
                          i
                        </span>

                        <div>
                          <strong>
                            {forecastPeriod === "today" &&
                            selectedPoiIsClosedToday
                              ? "Not open today"
                              : "Forecast unavailable"}
                          </strong>
                          <p>
                            {forecastPeriod === "today" &&
                            selectedPoiIsClosedToday
                              ? `${selectedPoi.name} is closed today, so an hourly crowd forecast is not shown.`
                              : forecastError ||
                                `No ${forecastPeriod} crowd forecast is available for this attraction.`}
                          </p>
                        </div>
                      </div>
                    )}

                    <p className="chart-note">
                      Forecast percentages are estimates. Lower bars indicate
                      quieter expected visiting periods.
                    </p>
                  </section>

                  <section className="accessibility-panel">
                    <h2>Accessibility</h2>

                    {selectedPoiAccessibility.length > 0 ? (
                      <div className="accessibility-grid">
                        {selectedPoiAccessibility.map((label) => (
                          <p key={label}>
                            <span aria-hidden="true">✓</span>{" "}
                            {formatAccessibilityLabel(label)}
                          </p>
                        ))}
                      </div>
                    ) : selectedPoi.website_url ? (
                      <p className="fallback-message">
                        Check the{" "}
                        <a
                          className="inline-website-link"
                          href={selectedPoi.website_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          official website
                        </a>{" "}
                        for accessibility features.
                      </p>
                    ) : (
                      <p className="fallback-message">
                        Accessibility information is not
                        available for this attraction.
                      </p>
                    )}
                  </section>
                </div>

                <aside className="poi-detail-sidebar">
                  <section className="map-panel">
                    {selectedPoi.map_embed_url ? (
                      <iframe
                        src={selectedPoi.map_embed_url}
                        title={`${selectedPoi.name} map`}
                        loading="lazy"
                      />
                    ) : (
                      <p className="fallback-message">
                        Map preview unavailable.
                      </p>
                    )}

                    {selectedPoi.map_external_url && (
                      <a
                        className="map-link"
                        href={selectedPoi.map_external_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        View on map
                        <span aria-hidden="true">↗</span>
                      </a>
                    )}
                  </section>

                  <button
                    className="sidebar-save-button"
                    type="button"
                    onClick={() =>
                      toggleSavePoi(selectedPoi.slug)
                    }
                    disabled={
                      savingPoiSlug === selectedPoi.slug
                    }
                  >
                    {savingPoiSlug === selectedPoi.slug
                      ? "Updating..."
                      : savedPoiSlugs.includes(
                            selectedPoi.slug
                          )
                        ? "Remove from saved"
                        : user
                          ? "Save for my trip"
                          : "Log in to save"}
                  </button>

                  <section className="detail-card">
                    <h3>Details</h3>

                    <p>
                      <strong>Opening hours</strong>
                    </p>

                    <ul className="opening-hours-list">
                      {formatOpeningHours(selectedPoi).map((line) => {
                        const [day, ...hours] = line.split(": ");

                        return (
                          <li key={line}>
                            {hours.length > 0 ? (
                              <>
                                <span>{day}</span>
                                <strong>{hours.join(": ")}</strong>
                              </>
                            ) : (
                              <span>{line}</span>
                            )}
                          </li>
                        );
                      })}
                    </ul>

                    <p>
                      <strong>Admission</strong>
                      <br />
                      {selectedPoi.admission_text ||
                        "Not currently available"}
                    </p>

                    <p>
                      <strong>
                        Recommended duration
                      </strong>
                      <br />
                      {selectedPoi.recommended_duration_min
                        ? `${selectedPoi.recommended_duration_min} minutes`
                        : "Not currently available"}
                    </p>

                    <p>
                      <strong>Closest subway</strong>
                      <br />
                      {selectedPoi.closest_subway ||
                        "Not currently available"}
                    </p>

                    <p>
                      <strong>Address</strong>
                      <br />
                      {selectedPoi.address ||
                        "Not currently available"}
                    </p>

                    {selectedPoi.website_url && (
                      <a
                        className="detail-website-link"
                        href={selectedPoi.website_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Visit official website ↗
                      </a>
                    )}
                  </section>
                </aside>
              </section>
            </section>
          )}

        {currentPage === "itinerary" &&
          user &&
          (routeItineraryId ? (
            <ItineraryDetail
              itineraryId={routeItineraryId}
              pois={pois}
              preferAccessiblePlaces={profilePreferences.stepFreeRoutes}
              onBackToPlanner={() => navigate(PAGE_PATHS.itinerary)}
            />
          ) : (
            <MyItinerary
              pois={pois}
              onLoginRequired={openLogin}
              preferAccessiblePlaces={profilePreferences.stepFreeRoutes}
              initialItinerary={aiGeneratedItinerary}
              onOpenItinerary={(itineraryId) => {
                /*
                  The AI handoff has been consumed. Leaving it in place would
                  re-seed the planner every time the user came back here.
                */
                setAiGeneratedItinerary(null);
                navigate(`/itinerary/${encodeURIComponent(itineraryId)}`);
              }}
            />
          ))}

        {currentPage === "saved" && user && (
          <SavedItineraries
            pois={pois}
            onSavedPlaceRemoved={handleSavedPlaceRemoved}
            preferAccessiblePlaces={profilePreferences.stepFreeRoutes}
          />
        )}

        {currentPage === "ai" && (
          <AIPlanner
            pois={pois}
            isAuthenticated={Boolean(user)}
            onLoginRequired={openLogin}
            onItineraryGenerated={(itinerary) => {
              setAiGeneratedItinerary(itinerary);
              navigate(PAGE_PATHS.itinerary);
            }}
          />
        )}

        {currentPage === "welcome" && user && (
          <WelcomePage user={user} onDone={handleWelcomeDone} />
        )}

        {currentPage === "profile" && user && (
          <Profile
            user={user}
            onLogout={handleLogout}
            preferences={profilePreferences}
            onPreferencesChange={updateProfilePreferences}
          />
        )}
      </main>

      <footer className="site-footer">
        <strong>Offpeak Manhattan</strong>

        <div>
          <a href="#accessibility">
            Accessibility
          </a>

          <a href="#privacy">Privacy</a>
          <a href="#terms">Terms</a>
          <a href="#support">Support</a>
        </div>

        <span>
          © 2026 Offpeak Manhattan. Editorial discovery.
        </span>
      </footer>

      {isAuthModalOpen && (
        <div
          className="modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeAuthModal();
            }
          }}
        >
          <AuthForm
            authMode={authMode}
            onXClick={closeAuthModal}
            onRegisterClick={openRegister}
            onLoginClick={switchToLogin}
            onAuthSuccess={handleAuthenticationSuccess}
            initialError={authError ?? undefined}
          />
        </div>
      )}

      {pendingAccessibleSave && (
        <div
          className="accessibility-warning-overlay"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setPendingAccessibleSave(null);
            }
          }}
        >
          <section
            className="accessibility-warning-dialog"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="save-accessibility-warning-title"
            aria-describedby="save-accessibility-warning-description"
          >
            <div className="accessibility-warning-icon" aria-hidden="true">
              ♿
            </div>

            <p className="section-eyebrow">Accessibility check</p>

            <h2 id="save-accessibility-warning-title">
              Accessibility information not confirmed
            </h2>

            <p id="save-accessibility-warning-description">
              {`${pendingAccessibleSave.name} does not have confirmed wheelchair-accessibility information. Missing information does not necessarily mean the attraction is inaccessible.`}
            </p>

            <div className="accessibility-warning-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setPendingAccessibleSave(null)}
              >
                Choose another place
              </button>

              <button
                type="button"
                className="primary-button"
                onClick={() => {
                  const slug = pendingAccessibleSave.slug;
                  setPendingAccessibleSave(null);
                  void updateSavedPoi(slug);
                }}
              >
                Save anyway
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default App;
