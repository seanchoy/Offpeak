"""Embedding providers. Anything with `model`, `embed_documents` and `embed_query` works."""
from typing import Protocol
from google.genai import types

from app.core.config import settings
from app.core.constants import EMBEDDING_DIM, EMBEDDING_MODEL



class Embedder(Protocol):
    """What the indexer and retriever need from an embedding provider (provided)."""

    model: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def normalize(vector: list[float]) -> list[float]:
    """Scale a vector to length 1; a zero vector is a ValueError (练习册 Part 4.1)."""
    len = sum(x*x for x in vector) ** 0.5
    if len == 0:
        raise ValueError("cannot normalize a zero vector: its length is 0")
    return [x/len for x in vector]



class GeminiEmbedder:
    """Gemini embeddings through google-genai (练习册 Part 4.2).

    `client` is a genai.Client (tests pass a fake with the same `.models.embed_content`).
    """

    def __init__(self, client, model: str = EMBEDDING_MODEL, dim: int = EMBEDDING_DIM):
        self.client = client
        self.model = model
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """One API call for all texts, task type RETRIEVAL_DOCUMENT, normalized vectors."""
        if not texts:
            return []

        return self._embed(texts, "RETRIEVAL_DOCUMENT")



    def embed_query(self, text: str) -> list[float]:
        """One vector for a search query, task type RETRIEVAL_QUERY, normalized."""
        if not text:
            return []

        return self._embed([text], "RETRIEVAL_QUERY")[0]


    def  _embed(self, texts: list[str], task_type: str) -> list[list[float]]:

        response = self.client.models.embed_content(
            model = self.model,
            contents = texts,
            config = types.EmbedContentConfig(task_type = task_type, output_dimensionality=self.dim),
        )

        # normalize
        return [normalize(embedding.values) for embedding in response.embeddings]



def make_gemini_embedder() -> GeminiEmbedder:
    """Build the production embedder from settings (provided)."""
    from google import genai

    return GeminiEmbedder(genai.Client(api_key=settings.GEMINI_API_KEY))
