import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { ApiError, apiFetch } from "../api";
import { groupStopsByDay } from "../itinerary";
import type {
  AiChatResponse,
  AiConversationResponse,
  AiUiAction,
  ItineraryResponse,
  Poi,
  SavedItinerary,
} from "../types";
import BusynessChart from "./BusynessChart";
import "./AiPlanner.css";

const PROMPT_SUGGESTIONS = [
  {
    title: "Art & architecture",
    detail: "Museums, landmarks, fewer crowds",
    icon: "museum",
    prompt: "Plan a low-crowd day with museums and architecture.",
  },
  {
    title: "Room to explore",
    detail: "Accessible parks & city views",
    icon: "leaf",
    prompt: "Plan an accessible weekend with parks and viewpoints.",
  },
  {
    title: "A slower kind of day",
    detail: "Local markets & neighbourhood walks",
    icon: "coffee",
    prompt: "Plan a relaxed local day with markets and neighbourhood walks.",
  },
];

const OPENING_MESSAGE =
  "Hi! Let's find your kind of Manhattan. What would you love to do? Share your dates, interests or preferred pace, and we'll take it from there.";

function PlannerIcon({ name }: { name: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {name === "museum" ? (
        <><path d="m3 9 9-5 9 5H3ZM5 11v7m5-7v7m4-7v7m5-7v7M3 21h18" /></>
      ) : name === "leaf" ? (
        <><path d="M20 4c-9-1-16 3-15 10 1 7 9 7 12 2 2-3 3-7 3-12ZM4 21l10-11" /></>
      ) : name === "coffee" ? (
        <><path d="M4 9h13v6a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V9Zm13 1h2a3 3 0 0 1 0 6h-2M7 3v2m5-2v2M3 23h16" /></>
      ) : name === "pin" ? (
        <><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z" /><circle cx="12" cy="10" r="2.5" /></>
      ) : name === "reset" ? (
        <><path d="M3 10a9 9 0 1 1 2 8M3 4v6h6" /></>
      ) : (
        <><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z" /></>
      )}
    </svg>
  );
}

const AI_QUOTA_ERROR =
  "You've reached today's AI usage limit. Please try again later.";
const AI_CONNECTION_ERROR =
  "Something went wrong with the connection. Check your network and try again.";
const AI_SERVER_ERROR =
  "The system is busy right now. Please try again shortly.";

type PlannerMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
};

type AIPlannerProps = {
  pois: Poi[];
  isAuthenticated: boolean;
  onLoginRequired: () => void;
  onItineraryGenerated: (itinerary: ItineraryResponse) => void;
};

function formatDate(value: string): string {
  const date = new Date(`${value}T12:00:00`);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(date);
}

function formatTime(value: string): string {
  const [hourText, minuteText] = value.split(":");
  const hour = Number(hourText);
  const minute = Number(minuteText);

  if (!Number.isFinite(hour) || !Number.isFinite(minute)) {
    return value;
  }

  return new Intl.DateTimeFormat("en-GB", {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(2026, 0, 1, hour, minute));
}

function isAuthenticationError(error: unknown): boolean {
  return (
    error instanceof Error &&
    error.message.toLowerCase().includes("log in")
  );
}

function getAiPlannerErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429) {
      return AI_QUOTA_ERROR;
    }

    if (error.kind === "network") {
      return AI_CONNECTION_ERROR;
    }

    if (
      error.kind === "timeout" ||
      (error.status !== undefined && error.status >= 500)
    ) {
      return AI_SERVER_ERROR;
    }
  }

  return error instanceof Error
    ? error.message
    : "The AI Planner could not complete that request.";
}

function AIPlanner({
  pois,
  isAuthenticated,
  onLoginRequired,
  onItineraryGenerated,
}: AIPlannerProps) {
  const [prompt, setPrompt] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<PlannerMessage[]>([
    {
      id: 1,
      role: "assistant",
      text: OPENING_MESSAGE,
    },
  ]);
  const [uiAction, setUiAction] = useState<AiUiAction | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [itinerary, setItinerary] = useState<ItineraryResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const itineraryResultRef = useRef<HTMLElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const chatHistoryRef = useRef<HTMLDivElement | null>(null);
  const chatStageRef = useRef<HTMLDivElement | null>(null);

  // As the introduction scrolls away, grow the chat upwards while keeping
  // the composer at the same distance from the bottom of the viewport.
  useLayoutEffect(() => {
    const stage = chatStageRef.current;
    if (!stage) return;

    let frame = 0;
    const updateChatSize = () => {
      const nav = document.querySelector<HTMLElement>(".top-nav");
      const navHeight = nav && getComputedStyle(nav).position === "sticky"
        ? nav.getBoundingClientRect().height
        : 0;
      const topLimit = navHeight + 20;
      const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
      const availableHeight = Math.max(0, viewportHeight - topLimit - 24);
      const top = Math.max(topLimit, stage.getBoundingClientRect().top);
      // A small initial card remains usable on short screens; once the intro
      // clears, the card expands to the available viewport height.
      const height = Math.max(Math.min(320, availableHeight), viewportHeight - top - 24);

      stage.style.setProperty("--planner-chat-top", `${topLimit}px`);
      stage.style.setProperty("--planner-chat-height", `${height}px`);
    };
    const scheduleUpdate = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(updateChatSize);
    };

    updateChatSize();
    window.addEventListener("scroll", scheduleUpdate, { passive: true });
    window.addEventListener("resize", scheduleUpdate);
    window.visualViewport?.addEventListener("resize", scheduleUpdate);
    const observer = typeof ResizeObserver !== "undefined"
      ? new ResizeObserver(scheduleUpdate)
      : null;
    if (stage.parentElement) observer?.observe(stage.parentElement);

    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("scroll", scheduleUpdate);
      window.removeEventListener("resize", scheduleUpdate);
      window.visualViewport?.removeEventListener("resize", scheduleUpdate);
      observer?.disconnect();
    };
  }, []);

  useEffect(() => {
    const stage = chatStageRef.current;
    const history = chatHistoryRef.current;
    if (!stage || !history) return;

    // Downward gestures expand the outer panel first, even when the pointer
    // is over its scrollable conversation. Only the remainder scrolls chat.
    const expandBeforeScrollingChat = (distance: number) => {
      const topLimit = parseFloat(getComputedStyle(stage).getPropertyValue("--planner-chat-top")) || 20;
      const remaining = Math.max(0, stage.getBoundingClientRect().top - topLimit);
      if (distance <= 0 || remaining < 1) return false;

      const pageDistance = Math.min(distance, remaining);
      window.scrollBy({ top: pageDistance, behavior: "instant" });
      if (distance > pageDistance) history.scrollTop += distance - pageDistance;
      return true;
    };

    const onWheel = (event: WheelEvent) => {
      if (event.ctrlKey || event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;
      const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? window.innerHeight : 1;
      if (expandBeforeScrollingChat(event.deltaY * unit)) event.preventDefault();
    };

    let touchY: number | null = null;
    const onTouchStart = (event: TouchEvent) => {
      touchY = event.touches.length === 1 ? event.touches[0].clientY : null;
    };
    const onTouchMove = (event: TouchEvent) => {
      if (touchY === null || event.touches.length !== 1) return;
      const nextY = event.touches[0].clientY;
      const distance = touchY - nextY;
      touchY = nextY;
      if (expandBeforeScrollingChat(distance) && event.cancelable) event.preventDefault();
    };

    history.addEventListener("wheel", onWheel, { passive: false });
    history.addEventListener("touchstart", onTouchStart, { passive: true });
    history.addEventListener("touchmove", onTouchMove, { passive: false });
    return () => {
      history.removeEventListener("wheel", onWheel);
      history.removeEventListener("touchstart", onTouchStart);
      history.removeEventListener("touchmove", onTouchMove);
    };
  }, []);

  const itineraryDays = useMemo(
    () => (itinerary ? groupStopsByDay(itinerary.stops) : []),
    [itinerary]
  );
  const hasUserSentMessage = messages.some(
    (message) => message.role === "user"
  );

  /*
    Once the backend returns an itinerary, I move the viewport and keyboard
    focus to the result so it is not hidden below the conversation.
  */
  useEffect(() => {
    if (!itinerary) {
      return;
    }

    const animationFrame = window.requestAnimationFrame(() => {
      const result = itineraryResultRef.current;

      result?.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto"
          : "smooth",
        block: "start",
      });
      result?.focus({ preventScroll: true });
    });

    return () => window.cancelAnimationFrame(animationFrame);
  }, [itinerary]);

  /*
    The conversation is a fixed-height scroller, so anything new is appended
    out of sight. After every turn I pin the scroller to the bottom, which puts
    the end of the newest bubble directly above the composer: a reply is read
    without scrolling, and a sent message is visibly sent.

    This runs on isSending too, so the "Planning your next step..." bubble is
    also brought into view rather than appearing below the fold of the scroller.

    Scrolling unconditionally is safe here because messages only ever arrive as
    a direct result of the user acting -- there is no background stream that
    could yank the view away while they are reading back.
  */
  useEffect(() => {
    const history = chatHistoryRef.current;

    if (!history) {
      return;
    }

    // Wait for the new bubble to be laid out, so scrollHeight includes it.
    const animationFrame = window.requestAnimationFrame(() => {
      const newest = history.querySelector(".ai-chat-history")?.lastElementChild;

      /*
        One exception to bottoming out: a reply taller than the scroller would
        land the user at its last line, having to scroll up to read it from the
        start. In that case the top of the bubble is aligned instead, so reading
        still begins at the beginning. Replies are normally a few lines, so this
        is the rare path -- everything that fits still ends against the composer.
      */
      const targetTop =
        newest && newest.getBoundingClientRect().height > history.clientHeight
          ? history.scrollTop +
            (newest.getBoundingClientRect().top -
              history.getBoundingClientRect().top)
          : history.scrollHeight;

      history.scrollTo({
        top: targetTop,
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto"
          : "smooth",
      });
    });

    return () => window.cancelAnimationFrame(animationFrame);
  }, [messages, isSending]);

  /*
    Keeps the prompt box a single compact line until the user actually
    types something longer, instead of always showing a tall empty box.
  */
  useEffect(() => {
    const textarea = textareaRef.current;

    if (!textarea) {
      return;
    }

    function resizePrompt() {
      if (!textarea) return;
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 140)}px`;
    }

    resizePrompt();
    window.addEventListener("resize", resizePrompt);
    return () => window.removeEventListener("resize", resizePrompt);
  }, [prompt]);

  function requireLogin(): boolean {
    if (isAuthenticated) {
      return false;
    }

    setErrorMessage("Please log in to use the AI Planner.");
    onLoginRequired();
    return true;
  }

  async function getConversationId(): Promise<string> {
    if (conversationId) {
      return conversationId;
    }

    const created = await apiFetch<AiConversationResponse>(
      "/api/ai/conversations",
      { method: "POST" }
    );

    setConversationId(created.conversation_id);
    return created.conversation_id;
  }

  async function sendPlannerMessage(
    value: string | string[],
    displayText: string
  ) {
    if (requireLogin()) {
      return;
    }

    setErrorMessage("");
    setSuccessMessage("");
    setIsSending(true);
    setMessages((current) => [
      ...current,
      { id: Date.now(), role: "user", text: displayText },
    ]);

    try {
      const activeConversationId = await getConversationId();

      /*
        The backend route currently contains the spelling "converstions".
        I use that exact source route until the backend renames it.
      */
      const response = await apiFetch<AiChatResponse>(
        `/api/ai/converstions/${activeConversationId}/messages`,
        {
          method: "POST",
          body: JSON.stringify({ prompt: value }),
          // Gemini may need longer than a standard API request to reply.
          signal: AbortSignal.timeout(90_000),
        }
      );

      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: response.message,
        },
      ]);
      setUiAction(response.ui_action);
      setSelectedOptions([]);

      if (response.itinerary) {
        setItinerary(response.itinerary);
        setSuccessMessage(
          "Your itinerary is ready. Review it here, then open it in My Itinerary."
        );
      }
    } catch (error) {
      const message = getAiPlannerErrorMessage(error);

      if (message === "Please log in to continue.") {
        onLoginRequired();
      }

      setErrorMessage(message);
    } finally {
      setIsSending(false);
    }
  }

  async function submitPlannerRequest() {
    if (isSending) {
      return;
    }

    const trimmedPrompt = prompt.trim();

    if (!trimmedPrompt) {
      setErrorMessage(
        "Describe the kind of Manhattan trip you would like to plan."
      );
      return;
    }

    setPrompt("");
    await sendPlannerMessage(trimmedPrompt, trimmedPrompt);
  }

  function toggleOption(value: string) {
    setSelectedOptions((current) =>
      current.includes(value)
        ? current.filter((option) => option !== value)
        : [...current, value]
    );
  }

  async function submitOptions() {
    if (selectedOptions.length === 0) {
      setErrorMessage("Select at least one option before continuing.");
      return;
    }

    const labels =
      uiAction?.options
        .filter((option) => selectedOptions.includes(option.value))
        .map((option) => option.label) ?? selectedOptions;

    await sendPlannerMessage(selectedOptions, labels.join(", "));
  }

  function startNewConversation() {
    setConversationId(null);
    setPrompt("");
    setMessages([
      {
        id: Date.now(),
        role: "assistant",
        text: OPENING_MESSAGE,
      },
    ]);
    setUiAction(null);
    setSelectedOptions([]);
    setItinerary(null);
    setErrorMessage("");
    setSuccessMessage("");
  }

  async function saveItinerary() {
    if (!itinerary || requireLogin()) {
      return;
    }

    setErrorMessage("");
    setSuccessMessage("");
    setIsSaving(true);

    try {
      const saved = await apiFetch<SavedItinerary>("/api/itinerary", {
        method: "POST",
        body: JSON.stringify(itinerary),
      });

      setSuccessMessage(`Itinerary "${saved.trip_name}" was saved.`);
    } catch (error) {
      if (isAuthenticationError(error)) {
        setErrorMessage("Please log in to save this itinerary.");
        onLoginRequired();
        return;
      }

      setErrorMessage(
        error instanceof Error
          ? error.message
          : "The itinerary could not be saved."
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="ai-planner-page" aria-labelledby="ai-planner-title">
      <header className="ai-planner-hero">
        <div>
          <p className="section-eyebrow"><span /> A little less rush. A little more New York.</p>
          <h1 id="ai-planner-title">Your Manhattan.<br /><span>Your kind of day.</span></h1>
          <p className="ai-planner-intro">
            Tell us what you love. We’ll help you plan around the crowds,
            at your own pace.
          </p>
        </div>
        <div className="ai-planner-location">
          <PlannerIcon name="pin" />
          <span>MANHATTAN, NYC<small>Big city. Personal plans.</small></span>
        </div>
      </header>

      <div className="ai-chat-stage" ref={chatStageRef}>
        <section className="ai-planner-card ai-chat-card" aria-labelledby="ai-chat-title">
          <div className="ai-planner-card-heading">
            <div className="ai-planner-identity">
              <span className="ai-planner-avatar"><PlannerIcon name="sparkle" /></span>
              <div>
                <h2 id="ai-chat-title">Chat with Offpeak</h2>
                <p>Your personal trip planner</p>
              </div>
            </div>

            {hasUserSentMessage && (
              <button
                type="button"
                className="ai-new-conversation"
                onClick={startNewConversation}
                disabled={isSending}
              >
                <PlannerIcon name="reset" />
                Start again
              </button>
            )}
          </div>

          <div className="ai-chat-body" ref={chatHistoryRef}>
            <div
              className="ai-chat-history"
              role="log"
              aria-label="Conversation with Offpeak"
              aria-live="polite"
            >
              {messages.map((message) => (
                <article
                  key={message.id}
                  className={`ai-chat-message ${message.role}`}
                >
                  <strong>
                    {message.role === "assistant" && <PlannerIcon name="sparkle" />}
                    {message.role === "assistant" ? "Offpeak" : "You"}
                  </strong>
                  <p>{message.text}</p>
                </article>
              ))}

              {isSending && (
                <article className="ai-chat-message assistant ai-chat-loading">
                  <strong>Offpeak</strong>
                  <p>
                    <span className="ai-typing-dots" aria-hidden="true"><i /><i /><i /></span>
                    Planning your next step…
                  </p>
                </article>
              )}
            </div>

            {uiAction?.component === "poi_type_selector" && (
              <fieldset className="ai-option-selector">
                <legend>Select all that interest you</legend>

                <div>
                  {uiAction.options.map((option) => (
                    <label key={option.value}>
                      <input
                        type="checkbox"
                        checked={selectedOptions.includes(option.value)}
                        onChange={() => toggleOption(option.value)}
                        disabled={isSending}
                      />
                      <span>{option.label}</span>
                    </label>
                  ))}

                  <button
                    type="button"
                    className="ai-option-selector-continue"
                    onClick={() => void submitOptions()}
                    disabled={isSending || selectedOptions.length === 0}
                  >
                    Continue
                  </button>
                </div>
              </fieldset>
            )}

            {!hasUserSentMessage && (
              <div className="ai-planner-inspiration">
                <p>Not sure where to start? Try a little inspiration.</p>
                <div className="ai-planner-suggestions" aria-label="Prompt suggestions">
                  {PROMPT_SUGGESTIONS.map((suggestion) => (
                    <button
                      key={suggestion.title}
                      type="button"
                      onClick={() => {
                        setPrompt(suggestion.prompt);
                        setErrorMessage("");
                        textareaRef.current?.focus();
                      }}
                      disabled={isSending}
                    >
                      <span className="ai-suggestion-icon"><PlannerIcon name={suggestion.icon} /></span>
                      <strong>{suggestion.title}</strong>
                      <span>{suggestion.detail}</span>
                      <span className="ai-suggestion-arrow" aria-hidden="true">↗</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {errorMessage && (
              <p className="error-message" role="alert">
                {errorMessage}
              </p>
            )}

            {successMessage && (
              <p className="success-message" role="status">
                {successMessage}
              </p>
            )}
          </div>

          <div className="ai-composer-area">
            <label htmlFor="ai-planner-prompt" className="sr-only">
              Reply to the AI trip planner
            </label>

            <div className="ai-composer">
              <textarea
                id="ai-planner-prompt"
                ref={textareaRef}
                rows={1}
                maxLength={600}
                placeholder="A museum morning, a quiet walk… what’s your kind of day?"
                aria-describedby="ai-composer-help ai-character-count"
                value={prompt}
                onChange={(event) => {
                  setPrompt(event.target.value);
                  setErrorMessage("");
                }}
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter" &&
                    !event.shiftKey &&
                    !event.nativeEvent.isComposing &&
                    event.nativeEvent.keyCode !== 229
                  ) {
                    event.preventDefault();
                    void submitPlannerRequest();
                  }
                }}
                disabled={isSending}
              />

              <button
                type="button"
                className="ai-composer-send"
                onClick={() => void submitPlannerRequest()}
                disabled={isSending || !prompt.trim()}
                aria-label={isSending ? "Sending" : "Send to AI Planner"}
              >
                <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
                  <path d="M12 19V5" />
                  <path d="m5 12 7-7 7 7" />
                </svg>
              </button>
            </div>

            <div className="ai-composer-meta">
              <span id="ai-composer-help">Enter to send <span aria-hidden="true">·</span> Shift + Enter for a new line</span>
              <span id="ai-character-count" className="ai-character-count">{prompt.length} / 600</span>
            </div>
          </div>
        </section>
      </div>

      {itinerary && (
        <section
          ref={itineraryResultRef}
          className="ai-itinerary-result"
          tabIndex={-1}
        >
          <header>
            <div>
              <p className="section-eyebrow">Generated itinerary</p>
              <h2>{itinerary.trip_name}</h2>
              <p>
                {itinerary.start_date} to {itinerary.end_date}
              </p>
            </div>

            <div className="ai-itinerary-actions">
              <button
                type="button"
                onClick={() => onItineraryGenerated(itinerary)}
                disabled={itinerary.stops.length === 0}
              >
                Open in My Itinerary
              </button>

              <button
                type="button"
                className="secondary-button"
                onClick={() => void saveItinerary()}
                disabled={isSaving || itinerary.stops.length === 0}
              >
                {isSaving ? "Saving..." : "Save itinerary"}
              </button>
            </div>
          </header>

          {itinerary.warning?.trim() && (
            <p className="fallback-message">
              <strong>Scheduling note:</strong> {itinerary.warning}
            </p>
          )}

          {itinerary.stops.length === 0 ? (
            <p className="fallback-message">
              The AI completed the request but did not return any scheduled
              stops. Add more trip details and ask it to try again.
            </p>
          ) : (
            <div className="ai-itinerary-days">
              {itineraryDays.map((day) => (
                <section key={`${day.dayNumber}-${day.visitDate}`}>
                  <h3>
                    Day {day.dayNumber} · {formatDate(day.visitDate)}
                  </h3>

                  {day.stops.map((stop) => {
                    const poi = pois.find((item) => item.slug === stop.slug);
                    const whyThisTime =
                      stop.why_this_time?.trim() ||
                      poi?.why_this_time?.trim();

                    return (
                      <article
                        key={`${stop.slug}-${stop.position}`}
                        className="ai-itinerary-stop"
                      >
                        <div className="ai-itinerary-stop-heading">
                          <div>
                            <span>
                              {formatTime(stop.slot_start)}–
                              {formatTime(stop.slot_end)}
                            </span>
                            <h4>{stop.poi_name}</h4>
                            <p>
                              {stop.neighborhood}, {stop.borough}
                            </p>
                          </div>
                          <strong>{stop.crowd_level} crowds</strong>
                        </div>

                        <p>
                          <strong>Why this time:</strong>{" "}
                          {whyThisTime ||
                            "A detailed recommendation explanation is not available for this stop."}
                        </p>

                        {stop.busyness_for_day?.length > 0 ? (
                          <BusynessChart
                            hours={stop.busyness_for_day}
                            poiName={stop.poi_name}
                          />
                        ) : (
                          <p className="fallback-message">
                            Hourly crowd data is not available for this stop.
                          </p>
                        )}
                      </article>
                    );
                  })}
                </section>
              ))}
            </div>
          )}
        </section>
      )}
    </section>
  );
}

export default AIPlanner;
