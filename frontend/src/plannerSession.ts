import type { AiUiAction, ItineraryResponse } from "./types";

export type PlannerMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
  /*
    Show cards for the attractions this reply names. Off for the opening
    message, and for a reply that came with an itinerary, which is already
    shown in full below the chat.
  */
  showPlaces?: boolean;
};

export type PlannerSession = {
  conversationId: string | null;
  messages: PlannerMessage[];
  uiAction: AiUiAction | null;
  itinerary: ItineraryResponse | null;
  // The saved copy of `itinerary`, once the visitor has saved it.
  savedItineraryId?: string | null;
};

/*
  The planner conversation is kept in sessionStorage: it survives a refresh
  and leaving the page within the same tab, and ends when the tab is closed.
  The backend already stores the conversation under its id, so restoring the
  id lets the next message carry on where the visitor left off.
*/
const PLANNER_SESSION_KEY = "offpeak.planner.session";

function isPlannerMessage(value: unknown): value is PlannerMessage {
  const message = value as PlannerMessage | null;
  return (
    typeof message === "object" &&
    message !== null &&
    typeof message.id === "number" &&
    (message.role === "user" || message.role === "assistant") &&
    typeof message.text === "string"
  );
}

export function loadPlannerSession(): PlannerSession | null {
  try {
    const raw = sessionStorage.getItem(PLANNER_SESSION_KEY);
    if (!raw) return null;

    const data = JSON.parse(raw) as Partial<PlannerSession> | null;
    const messages = Array.isArray(data?.messages)
      ? data.messages.filter(isPlannerMessage)
      : [];
    if (messages.length === 0) return null;

    return {
      conversationId: typeof data?.conversationId === "string" ? data.conversationId : null,
      messages,
      uiAction: data?.uiAction ?? null,
      itinerary: data?.itinerary ?? null,
      savedItineraryId:
        typeof data?.savedItineraryId === "string" ? data.savedItineraryId : null,
    };
  } catch {
    // Unreadable or blocked storage: start a fresh conversation.
    return null;
  }
}

export function savePlannerSession(session: PlannerSession): void {
  try {
    sessionStorage.setItem(PLANNER_SESSION_KEY, JSON.stringify(session));
  } catch {
    // Storage full or blocked: the conversation still works, it just won't survive a refresh.
  }
}

export function clearPlannerSession(): void {
  try {
    sessionStorage.removeItem(PLANNER_SESSION_KEY);
  } catch {
    // Nothing to clear.
  }
}
