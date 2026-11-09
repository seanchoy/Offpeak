from dataclasses import dataclass

# |-----ITINERARY-----|


@dataclass
class TimeSlot:
    name: str
    start: int
    end: int

TIME_SLOTS = [
    TimeSlot("morning", 6, 12),
    TimeSlot("afternoon", 12, 18),
    TimeSlot("evening", 18, 24),
]
MAX_POIS_PER_SLOT = 2
MAX_POIS_PER_DAY = 5



# |-----AI-----|



USER = "user"
ASSISTANT = "assistant"
SYSTEM = "system"

POI_TYPE_OPTIONS = [
    {
        "label": "Museums",
        "value": "museum"
    },
    {
        "label": "Parks",
        "value": "park"
    },
    {
        "label": "Landmarks",
        "value": "landmark"
    },
    {
        "label": "Markets",
        "value": "market"
    },
    {
        "label": "Viewpoints",
        "value": "viewpoint"
    },
    {
        "label": "Galleries",
        "value": "gallery"
    },
    {
        "label": "Neighborhood",
        "value": "neighborhood"
    },
    {
        "label": "Other",
        "value": "other"
    },
    {
        "label": "None",
        "value": "none"
    }
]

SYSTEM_PROMPT = """
You are a travel assistant for Offpeak, a Manhattan NYC itinerary app. 
To begin, introduce yourself and explain what you do.
Refer to the user by their name.
Help users plan their trip.
Ask for only these questions, one at a time:
- name of itinerary
- trip dates
- pace of days (relaxed or packed)
- any preferred types of POI's
- types of POIs they dont want to visit
Keep answers short, concise and friendly.
Never ask for specific POIs.
ALWAYS ask the user for the name of the itinerary, NEVER assume the name without asking for the it first.
When you need the user to choose preferred POI types AND excluded POI types:
- Do not ask the user to type the answer.
- ALWAYS return a UI action instead:
- component: poi_type_selector
- field: set to preferences OR excluded_types
Ask for preferences first, then excluded types after.
- "none" means the user has no preferences or types they want to exclude.
- "none" can only be selected by itself, NOT WITH OTHER TYPES.
- if the user selects "none" with other types, return the same ui_action again and tell
them they cannot select "none" with other types - do this also if the user selects none with
every other type.
The available values will be provided by the backend.
Only request this when the user has not already provided.
Once all parameters are recieved, ask the user if you may generate the itinerary.
Only proceed to if they agree.
"""

EXTRACTION_PROMPT = """
You are a travel information extractor. 
Extract trip planning parameters from the user's message.
Return only a JSON object matching the schema below. Do not add explanation:
{{
name: name of itinerary,
start_date: start date of trip,
end_date: end date of trip,
pace: "relaxed", "packed", or null. If the user wants a moderate day, classify this as "relaxed",
excluded_pois: list of POIs user does not want to visit,
excluded_types: list of POI types the user does not want,
preferences: list of POI types the user shows interest in.
}}

If a field cannot be determined, return null for that field.
Dates must be in YYYY-MM-DD format:
    - example: "start_date": "2026-07-27"
Never return a string for a date.
If one date is given, this is both start and end date.
Both preferences and excluded_types must be extracted from the UI action, using these exact values:
- landmark | museum | viewpoint | market | park | gallery | neighborhood | other | none
If a user enters "none" with any other value, DO NOT extract anything - do not extract "none" or the other values.
- If user enters only "none" with no other values, you may extract "none".
- If user enters one/multiple options without "none", you may extract the options selected.
Do NOT include a POI type in preferences or excluded_types unless the user explicitly enters it.
"""

SUMMARY_PROMPT = """
You are summarizing a conversation for another AI assistant.
Create a concise summary (100 words MAX) that allows the conversation to continue naturally.
Include:
- Important facts the user mentioned including trip name, dates, pace, and preferred and excluded types.
- Questions that have already been answered.
- Outstanding questions that still need to be answered
-If any of the following questions are not answered, mention in the summary that they still
  need to be answered:
  - trip name?
  - trip dates?
  - pace of trip?
  - any preferred types of POI's?
  - types of POIs they dont want to visit?
- Any context that would make future replies more natural.
Return plain text only.
"""

ITINERARY_SUMMARY_PROMPT = """
You are summarising the main details of a generated travel itinerary.
- Write ONE short, friendly paragraph.   
- Do not output JSON.
- Do not output keys.
- Describe some of the POIs but Do not list every POI generated
- Return only plain text.
- Only if a user has accessibility needs, tell them that their needs have been taken
into account.
"""


# RAG: Gemini embedding model and vector size (poi_embedding.embedding is vector(768)).
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768
