import json

from app.core.constants import ASSISTANT, USER
from app.core.exceptions import LLMUnresponsiveError
from app.repositories.ai_repository import (
    get_last_message,
    load_chat_history,
    load_chat_summary,
    save_message,
    update_summary,
)
from app.repositories.trip_repository import update_trip
from app.schemas.ai import ChatResponse
from app.services.ai.providers.gemini import GeminiProvider
from app.services.poi_service import get_all_pois
from app.services.trip_service import fuzzy_search, get_trip_details

provider = GeminiProvider()

# Shown instead of a 500 when Gemini cannot answer; not saved to the history.
UNAVAILABLE_RESPONSE = ChatResponse(
    message="I'm having trouble responding right now. Please try again in a moment.",
    ui_action=None,
    itinerary=None,
    save_to_history=False,
)

def chat(conversation_id, prompt, db, user):
    """
    Process a user message through the conversational trip-planning workflow.

    Saves the user's message, extracts trip preferences using the configured
    LLM provider, updates the trip, generates a response, and maintains the
    conversation history and summary.

    Args:
        conversation_id: Identifier of the current conversation.
        prompt: User's message.
        db: Database session.
        user: Authenticated user identifier.

    Returns:
        A ChatResponse containing the generated response and any UI action.
    """
    save_message(prompt, USER, conversation_id, db)

    trip_details = get_trip_details(conversation_id, db)
    last_message = get_last_message(conversation_id, db, user)

    extraction_prompt = json.dumps(prompt) if isinstance(prompt, list) else prompt
    extracted = provider.extract_trip_parameters(extraction_prompt, last_message, trip_details)
   
    pois = get_all_pois(db)
    excluded_pois = fuzzy_search(extracted.excluded_pois, pois)

    update_trip(conversation_id, extracted, excluded_pois, db, user)

    trip_details = get_trip_details(conversation_id, db)
    history = load_chat_history(conversation_id, db, user)
    summary = load_chat_summary(conversation_id, db, user)

    try:
        chat_response = provider.generate_chat_response(history, summary, trip_details, conversation_id, db, user)
    except LLMUnresponsiveError as e:
        print(f"Gemini failed during chat generation: {e}")
        return UNAVAILABLE_RESPONSE

    if chat_response.save_to_history:
        save_message(chat_response.message, ASSISTANT, conversation_id, db)
        if chat_response.ui_action:
            save_message(f"This selection is for {chat_response.ui_action.field}.", ASSISTANT, conversation_id, db)
        
    if len(history) >= 10:
        update_summary(conversation_id, history, db, user)

    return chat_response
