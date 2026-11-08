"""Keep poi_embedding in sync with the poi table, embedding only what changed."""
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.poi_model import POI, POIEmbedding
from app.services.rag.documents import build_poi_document, content_hash
from app.services.rag.embedder import Embedder

# Gemini rejects more than 100 texts in one batchEmbedContents request.
MAX_BATCH_SIZE = 100


@dataclass(frozen=True)
class SyncReport:
    embedded: int
    skipped: int
    deleted: int


def sync_poi_embeddings(
    db: Session, embedder: Embedder, batch_size: int = MAX_BATCH_SIZE
) -> SyncReport:
    """Embed new or changed active POIs, skip unchanged ones, drop the rest (练习册 Part 3)."""

    if batch_size > MAX_BATCH_SIZE or batch_size < 1:
        raise ValueError(f"batch_size must be between 1 and {MAX_BATCH_SIZE}")

    statement_poi = select(POI).where(POI.is_active == True).order_by(POI.id)
    statement_poi_embedding = select(POIEmbedding)
    pois = db.scalars(statement_poi).all()
    poi_embeddings = db.scalars(statement_poi_embedding).all()

    poi_embeddings_by_poi_id = {}
    for poi_embedding in poi_embeddings:
        poi_embeddings_by_poi_id[poi_embedding.poi_id] = poi_embedding

    skipped = 0
    embedded = 0
    to_embed = []
    for poi in pois:
        poi_text = build_poi_document(poi)
        poi_hash = content_hash(poi_text)
        if poi.id in poi_embeddings_by_poi_id and poi_embeddings_by_poi_id[poi.id].content_hash == poi_hash and poi_embeddings_by_poi_id[poi.id].model == embedder.model:
            skipped += 1
        else:
            to_embed.append((poi, poi_text, poi_hash))

    for start in range(0, len(to_embed), batch_size):
        batch = to_embed[start:start + batch_size]
        texts = [poi_text for _, poi_text, _ in batch]

        vectors = embedder.embed_documents(texts)
        if len(vectors) != len(texts):
            raise ValueError(f"expected {len(texts)} vectors, got {len(vectors)}")

        for (poi, poi_text, poi_hash), vector in zip(batch, vectors):
            statement = insert(POIEmbedding).values(poi_id = poi.id,
                                                    model = embedder.model,
                                                    content_hash = poi_hash,
                                                    document = poi_text,
                                                    embedding = vector)
            statement = statement.on_conflict_do_update(index_elements = [POIEmbedding.poi_id], set_ = {"model": embedder.model,
                                                                                                        "content_hash": poi_hash,
                                                                                                        "document": poi_text,
                                                                                                        "embedding": vector,
                                                                                                        "embedded_at": func.now()})
            db.execute(statement)
        db.commit()
        embedded += len(batch)

    deleted = 0
    active_id = {poi.id for poi in pois}
    stale_id = set(poi_embeddings_by_poi_id) - active_id
    if stale_id:
        db.execute(delete(POIEmbedding).where(POIEmbedding.poi_id.in_(stale_id)))
        db.commit()
    deleted += len(stale_id)


    return SyncReport(embedded, skipped, deleted)







