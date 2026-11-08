"""Find POIs for a free-text query: by meaning (vector), by words (keyword), or both."""
from dataclasses import dataclass
import re

from sqlalchemy.dialects.postgresql import to_tsquery
from sqlalchemy.orm import Session
from sqlalchemy import any_, select, literal, func

from app.models.poi_model import POIType, POIEmbedding, POI
from app.services.rag.embedder import Embedder
from app.services.rag.evaluation import rrf_fuse

MAX_K = 50


@dataclass(frozen=True)
class SearchHit:
    poi_id: int
    slug: str
    name: str
    score: float


@dataclass(frozen=True)
class SearchFilters:
    types: tuple[POIType, ...] = ()
    indoor_only: bool = False
    wheelchair: bool = False


def search_pois(
    db: Session,
    embedder: Embedder,
    query: str,
    *,
    k: int = 5,
    filters: SearchFilters | None = None,
) -> list[SearchHit]:
    """The k active POIs closest to the query by cosine similarity (练习册 Part 5)."""
    if k < 1 or k > MAX_K:
        raise ValueError(f"k must be between 1 and {MAX_K}")

    if not query or query.strip() == "":
        return []

    query_vector = embedder.embed_query(query)

    #SQL query
    cosine_distance = POIEmbedding.embedding.cosine_distance(query_vector)
    statement = (
        select(POIEmbedding.poi_id, POI.slug, POI.name, cosine_distance.label("distance"))
        .join(POI, POIEmbedding.poi_id == POI.id)
        .where(POI.is_active == True)
        .where(POIEmbedding.model == embedder.model)

    )

    if filters:
        if filters.types:
            statement = statement.where(POI.type.in_(filters.types))

        if filters.indoor_only:
            statement = statement.where(literal("indoor") == any_(POI.tags))

        if filters.wheelchair:
            statement = statement.where(literal("wheelchair") == any_(POI.accessibility_labels))

    statement = statement.order_by(cosine_distance, POIEmbedding.poi_id).limit(k)

    result = []
    for row in db.execute(statement):
        result.append(SearchHit(
            poi_id=row.poi_id,
            slug=row.slug,
            name=row.name,
            score= 1 - row.distance,
        ))

    return result






def keyword_search(db: Session, query: str, *, k: int = 5) -> list[SearchHit]:
    """Postgres full-text search over the embedded documents (练习册 Part 6.3)."""
    words = re.findall(r"[a-z0-9]+", query)
    if not words:
        return []


    ts_query = func.to_tsquery('english', " | ".join(words))
    ts_vector = func.to_tsvector('english', POIEmbedding.document)
    rank = func.ts_rank_cd(ts_vector, ts_query)

    statement = (select(POIEmbedding.poi_id,
                        POI.slug,
                        POI.name,
                        rank.label("rank"))
                        .join(POI, POIEmbedding.poi_id == POI.id)
                        .where(POI.is_active == True)
                        .where(ts_vector.op("@@")(ts_query))
                        .order_by(rank.desc(), POI.id)
                        .limit(k)
                    )

    result = db.execute(statement)
    return [SearchHit(row.poi_id, row.slug, row.name, row.rank) for row in result]


def hybrid_search(
    db: Session,
    embedder: Embedder,
    query: str,
    *,
    k: int = 5,
    candidates: int = 20,
    keyword_weight: float = 1.0,
) -> list[SearchHit]:
    """Fuse the vector and keyword rankings with weighted RRF (练习册 Part 6.4)."""
    vector_result = search_pois(db, embedder, query, k=candidates)
    keyword_result = keyword_search(db, query, k=candidates)
    vector_slug = [hit.slug for hit in vector_result]
    keyword_slug = [hit.slug for hit in keyword_result]

    by_slug = {hit.slug: hit for hit in vector_result + keyword_result}

    slug_ranks = rrf_fuse([vector_slug, keyword_slug], weights = [1.0, keyword_weight])[:k]

    return [SearchHit(by_slug[slug].poi_id, slug, by_slug[slug].name, rank) for slug, rank in slug_ranks]

