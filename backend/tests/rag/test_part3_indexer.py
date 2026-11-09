"""Part 3: sync_poi_embeddings, the incremental pipeline (练习册 Part 3)."""
import pytest
from sqlalchemy import select

from tests.rag.support import FakeEmbedder, needs_db

pytestmark = needs_db


def rows(db):
    from app.models.poi_model import POIEmbedding

    return {r.poi_id: r for r in db.scalars(select(POIEmbedding))}


def test_part3_first_run_embeds_every_active_poi(db, add_poi):
    from app.services.rag.documents import build_poi_document, content_hash
    from app.services.rag.indexer import SyncReport, sync_poi_embeddings

    met = add_poi("the-met")
    add_poi("moma")
    add_poi("closed-gallery", is_active=False)
    embedder = FakeEmbedder()

    report = sync_poi_embeddings(db, embedder)

    assert report == SyncReport(embedded=2, skipped=0, deleted=0)
    stored = rows(db)
    assert len(stored) == 2
    row = stored[met.id]
    assert row.document == build_poi_document(met)
    assert row.content_hash == content_hash(row.document)
    assert row.model == "fake-embed-v1"
    assert row.embedded_at is not None


def test_part3_second_run_calls_nothing(db, add_poi):
    from app.services.rag.indexer import SyncReport, sync_poi_embeddings

    add_poi("the-met")
    add_poi("moma")
    sync_poi_embeddings(db, FakeEmbedder())

    embedder = FakeEmbedder()
    report = sync_poi_embeddings(db, embedder)

    assert report == SyncReport(embedded=0, skipped=2, deleted=0)
    assert embedder.document_calls == []


def test_part3_only_the_changed_poi_is_embedded_again(db, add_poi):
    from app.services.rag.documents import build_poi_document
    from app.services.rag.indexer import SyncReport, sync_poi_embeddings

    met = add_poi("the-met")
    add_poi("moma")
    sync_poi_embeddings(db, FakeEmbedder())

    met.summary = "Now with a rooftop garden."
    db.commit()
    embedder = FakeEmbedder()
    report = sync_poi_embeddings(db, embedder)

    assert report == SyncReport(embedded=1, skipped=1, deleted=0)
    assert embedder.document_calls == [[build_poi_document(met)]]
    stored = rows(db)
    assert len(stored) == 2
    assert "rooftop garden" in stored[met.id].document


def test_part3_a_new_model_embeds_everything_again(db, add_poi):
    from app.services.rag.indexer import SyncReport, sync_poi_embeddings

    add_poi("the-met")
    add_poi("moma")
    sync_poi_embeddings(db, FakeEmbedder(model="model-a"))

    report = sync_poi_embeddings(db, FakeEmbedder(model="model-b"))

    assert report == SyncReport(embedded=2, skipped=0, deleted=0)
    assert {r.model for r in rows(db).values()} == {"model-b"}


def test_part3_batches_respect_batch_size(db, add_poi):
    from app.services.rag.indexer import sync_poi_embeddings

    for i in range(5):
        add_poi(f"poi-{i}")
    embedder = FakeEmbedder()

    sync_poi_embeddings(db, embedder, batch_size=2)

    assert [len(call) for call in embedder.document_calls] == [2, 2, 1]
    stored = rows(db)
    assert len(stored) == 5
    for row in stored.values():   # each POI keeps the vector made from its own document
        assert list(row.embedding) == FakeEmbedder._one_hot(row.document)


@pytest.mark.parametrize("batch_size", [0, 101])
def test_part3_rejects_batch_sizes_gemini_cannot_take(db, batch_size):
    from app.services.rag.indexer import sync_poi_embeddings

    with pytest.raises(ValueError):
        sync_poi_embeddings(db, FakeEmbedder(), batch_size=batch_size)


def test_part3_deactivated_poi_loses_its_embedding(db, add_poi):
    from app.services.rag.indexer import SyncReport, sync_poi_embeddings

    met = add_poi("the-met")
    moma = add_poi("moma")
    sync_poi_embeddings(db, FakeEmbedder())

    moma.is_active = False
    db.commit()
    report = sync_poi_embeddings(db, FakeEmbedder())

    assert report == SyncReport(embedded=0, skipped=1, deleted=1)
    assert set(rows(db)) == {met.id}


def test_part3_a_failed_batch_keeps_earlier_batches_and_rerun_resumes(db, add_poi):
    from app.services.rag.indexer import SyncReport, sync_poi_embeddings

    for i in range(5):
        add_poi(f"poi-{i}")

    with pytest.raises(RuntimeError):
        sync_poi_embeddings(db, FakeEmbedder(fail_on_call=2), batch_size=2)
    db.rollback()
    assert len(rows(db)) == 2   # batch 1 was committed before batch 2 failed

    embedder = FakeEmbedder()
    report = sync_poi_embeddings(db, embedder, batch_size=2)
    assert report == SyncReport(embedded=3, skipped=2, deleted=0)
    assert [len(call) for call in embedder.document_calls] == [2, 1]


def test_part3_wrong_number_of_vectors_is_an_error(db, add_poi):
    from app.services.rag.indexer import sync_poi_embeddings

    class DropsOne(FakeEmbedder):
        def embed_documents(self, texts):
            return super().embed_documents(texts)[:-1]

    add_poi("the-met")
    add_poi("moma")
    with pytest.raises(ValueError):
        sync_poi_embeddings(db, DropsOne())
    db.rollback()
    assert rows(db) == {}
