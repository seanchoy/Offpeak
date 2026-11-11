"""The search_pois tool: what Gemini is told about it, how its arguments are checked,
and what it gets back (练习册 Part 1–3)."""
from dataclasses import dataclass

from google.genai import types
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.poi_model import POI, POIType
from app.services.rag.embedder import Embedder
from app.services.rag.retriever import SearchFilters, search_pois

SEARCH_POIS = "search_pois"
DEFAULT_K = 5
MAX_TOOL_K = 8
SUMMARY_CHARS = 240


def search_pois_declaration() -> types.FunctionDeclaration:
    """The tool's name, purpose and parameters, as Gemini will see them (练习册 Part 1)."""
    # TODO 1.1: return types.FunctionDeclaration(name=SEARCH_POIS, description=..., parameters=...)
    # TODO 1.2: parameters: query (STRING, required), k (INTEGER), types (ARRAY of STRING,
    #           enum from POIType), indoor_only (BOOLEAN), wheelchair (BOOLEAN); each with a description
    # TODO 1.3: the description says when to call it, and that only its results may be recommended

    return types.FunctionDeclaration(
        name = SEARCH_POIS,
        description=(
            "Search Offpeak's own catalogue of Manhattan attractions by meaning. "
            "Call it whenever the visitor asks for recommendations, ideas, or places that "
            "match a mood or activity (for example 'somewhere quiet to watch birds'). "
            "Recommend only attractions that this tool returns. "
            "Do not call it to collect trip details such as dates, pace or the trip name."
        ),
        parameters = types.Schema(
            type = "OBJECT",
            properties={
                "query": types.Schema(type = "STRING", description= "what user is looking for"),
                "k" : types.Schema(type = "INTEGER", description= "how many pois user is requesting"),
                "types" : types.Schema(type = "ARRAY",
                                       items = types.Schema(type = "STRING", enum=[t.value for t in POIType], description= "what type of poi" ),
                                       description= "Only these attraction types. Leave it out unless the visitor names a type."),
                "indoor_only" : types.Schema(type = "BOOLEAN", description= "poi user requests is whether in door or not"),
                "wheelchair" : types.Schema(type = "BOOLEAN", description= "if user requires wheelchair access"),
            },
            required=["query"]
        ),

    )



class ToolArgumentError(ValueError):
    """The model called the tool with arguments we cannot use."""


@dataclass(frozen=True)
class SearchRequest:
    query: str
    k: int
    filters: SearchFilters


def parse_search_args(args: dict, *, wheelchair_user: bool = False) -> SearchRequest:
    """Turn the model's arguments into a safe search request (练习册 Part 2)."""
    # check query
    query = args.get("query") or ""
    if not query or not isinstance(query, str) or query.strip() == "" :
        raise ToolArgumentError("query must be a non-empty string.")
    else:
        query = query.strip()


    # check k
    k = args.get("k", DEFAULT_K)
    if isinstance(k, bool) or not isinstance(k, (int, float)) or int(k) != k :
        k = DEFAULT_K
    else:
        k = int(k)
        k = min(max(k, 1), MAX_TOOL_K)

    # check types
    types_verified = []
    types = args.get("types") or []


    # 可以是列表 也可以是单个字符串
    if isinstance(types, str):
        type_clean = types.strip().lower()
        if type_clean in POIType and POIType(type_clean) not in types_verified:
            types_verified.append(POIType(type_clean))
    elif isinstance(types, list):
        for t in types:
            type_clean = t.strip().lower()
            if type_clean in POIType and POIType(type_clean) not in types_verified:
                types_verified.append(POIType(type_clean))

    return SearchRequest(
        query = query,
        k = k,
        filters = SearchFilters(
            types = tuple(types_verified),
            indoor_only = args.get("indoor_only") is True,
            wheelchair = wheelchair_user or args.get("wheelchair") is True,
        )
    )





def shorten(text: str | None, limit: int = SUMMARY_CHARS) -> str:
    """At most `limit` characters, cut at a word boundary, with '…' when cut (练习册 Part 3)."""
    if text is None:
        return ""

    text = " ".join(text.split())

    if len(text) <= limit:
        return text
    else:
        text = text[:limit-1]
        text = text.rstrip(" ,.;:")
        index = text.rfind(" ")
        if index != -1:
            text = text[:index] + "\u2026"
        else:
            text = text[:limit-1] + "\u2026"
        return text





def run_search_tool(db: Session, embedder: Embedder, args: dict, *, wheelchair_user: bool = False) -> dict:
    """Run search_pois for the model and describe the results in a small dict (练习册 Part 3)."""
    response = {}
    try:
        request = parse_search_args(args, wheelchair_user=wheelchair_user)
    except ToolArgumentError as e:
        response["error"] = str(e)
        return response

    search_results = search_pois(db, embedder, request.query,
                                 k = request.k,
                                 filters = request.filters)



    response["query"] = request.query
    response["filters"] = {
            "types" : [t.value for t in request.filters.types],
            "indoor_only" : request.filters.indoor_only,
            "wheelchair" : request.filters.wheelchair,
        }

    if search_results == []:
        response["results"] = []
        response["note"] = "No attractions matched this search. Tell the visitor instead of guessing."
        return response

    ids = [result.poi_id for result in search_results]
    pois = {
        poi.id: poi
        for poi in db.scalars(select(POI).where(POI.id.in_(ids)))
    }


    results = [
        {"slug": result.slug,
         "name": result.name,
         "type": pois[result.poi_id].type,
         "neighborhood": pois[result.poi_id].neighborhood,
         "summary": shorten(pois[result.poi_id].summary),
         "score": round(result.score,3) }
        for result in search_results
    ]
    response["results"] = results
    return response



