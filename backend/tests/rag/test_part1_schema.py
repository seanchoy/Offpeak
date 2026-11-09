"""Part 1: the poi_embedding table (练习册 Part 1)."""
from sqlalchemy import delete, select

from tests.rag.support import needs_db, pad


def test_part1_embedding_is_a_768_dim_vector():
    from pgvector.sqlalchemy import Vector

    from app.models.poi_model import POIEmbedding

    column_type = POIEmbedding.__table__.c.embedding.type
    assert isinstance(column_type, Vector)
    assert column_type.dim == 768


def test_part1_poi_id_is_the_primary_key_and_cascades():
    from app.models.poi_model import POIEmbedding

    table = POIEmbedding.__table__
    assert [c.name for c in table.primary_key.columns] == ["poi_id"]
    (fk,) = table.c.poi_id.foreign_keys
    assert fk.target_fullname == "poi.id"
    assert fk.ondelete == "CASCADE"


def test_part1_columns_are_required():
    from app.models.poi_model import POIEmbedding

    c = POIEmbedding.__table__.c
    for name in ("model", "content_hash", "document", "embedding", "embedded_at"):
        assert c[name].nullable is False, f"{name} should be NOT NULL"
    assert c.content_hash.type.length == 64
    assert c.embedded_at.server_default is not None


@needs_db
def test_part1_stores_a_vector_and_measures_cosine_distance(db, add_poi, add_embedding):
    from app.models.poi_model import POIEmbedding

    met = add_poi("the-met")
    add_embedding(met, pad(3, 4))

    stored, same, orthogonal = db.execute(
        select(
            POIEmbedding.embedding,
            POIEmbedding.embedding.cosine_distance(pad(6, 8)),
            POIEmbedding.embedding.cosine_distance(pad(-4, 3)),
        )
    ).one()
    assert list(stored[:3]) == [3.0, 4.0, 0.0]
    assert same < 1e-6        # same direction -> distance 0
    assert abs(orthogonal - 1) < 1e-6   # 90 degrees -> distance 1


@needs_db
def test_part1_deleting_a_poi_deletes_its_embedding(db, add_poi, add_embedding):
    from app.models.poi_model import POI, POIEmbedding

    met = add_poi("the-met")
    add_embedding(met, pad(1))
    db.execute(delete(POI).where(POI.id == met.id))   # plain SQL DELETE: the FK must cascade
    db.commit()
    assert db.scalars(select(POIEmbedding)).all() == []
