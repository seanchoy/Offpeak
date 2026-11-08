"""Part 4: normalize and GeminiEmbedder (练习册 Part 4). Gemini is replaced by a fake client."""
import math
from types import SimpleNamespace

import pytest

from app.services.rag.embedder import GeminiEmbedder, normalize


class FakeModels:
    """Stands in for genai.Client().models: records calls, returns (3, 4, 0, ...) per text."""

    def __init__(self):
        self.calls = []

    def embed_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        vector = [3.0, 4.0] + [0.0] * 766
        return SimpleNamespace(embeddings=[SimpleNamespace(values=vector) for _ in contents])


def config_value(config, name):
    return config[name] if isinstance(config, dict) else getattr(config, name)


@pytest.fixture
def client():
    return SimpleNamespace(models=FakeModels())


def test_part4_normalize_scales_to_length_one():
    assert normalize([3.0, 4.0]) == pytest.approx([0.6, 0.8])
    assert math.hypot(*normalize([1.0, 2.0, 2.0])) == pytest.approx(1.0)


def test_part4_normalize_rejects_the_zero_vector():
    with pytest.raises(ValueError):
        normalize([0.0, 0.0, 0.0])


def test_part4_documents_use_retrieval_document_and_768_dims(client):
    embedder = GeminiEmbedder(client)

    vectors = embedder.embed_documents(["The Met", "MoMA"])

    (call,) = client.models.calls
    assert call["model"] == "gemini-embedding-001"
    assert list(call["contents"]) == ["The Met", "MoMA"]
    assert config_value(call["config"], "task_type") == "RETRIEVAL_DOCUMENT"
    assert config_value(call["config"], "output_dimensionality") == 768
    assert len(vectors) == 2
    assert vectors[0][:2] == pytest.approx([0.6, 0.8])   # normalized


def test_part4_query_uses_retrieval_query_and_returns_one_vector(client):
    vector = GeminiEmbedder(client).embed_query("quiet art museum")

    (call,) = client.models.calls
    assert list(call["contents"]) == ["quiet art museum"]
    assert config_value(call["config"], "task_type") == "RETRIEVAL_QUERY"
    assert len(vector) == 768
    assert vector[:2] == pytest.approx([0.6, 0.8])


def test_part4_no_texts_means_no_api_call(client):
    assert GeminiEmbedder(client).embed_documents([]) == []
    assert client.models.calls == []


def test_part4_model_name_is_exposed_for_the_indexer(client):
    assert GeminiEmbedder(client).model == "gemini-embedding-001"
    assert GeminiEmbedder(client, model="other-model").model == "other-model"
