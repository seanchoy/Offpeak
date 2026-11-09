"""Helpers shared by the exercise 05 tests (pad, FakeEmbedder, needs_db)."""
import hashlib
import os

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
DIM = 768

needs_db = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="needs TEST_DATABASE_URL (a disposable Postgres with pgvector)"
)


def pad(*values: float) -> list[float]:
    """A 768-dim vector whose first few numbers are `values` and the rest 0."""
    return list(values) + [0.0] * (DIM - len(values))


class FakeEmbedder:
    """Records every call. Documents get a stable one-hot vector; queries come from `queries`."""

    def __init__(self, model="fake-embed-v1", queries=None, fail_on_call=None):
        self.model = model
        self.queries = queries or {}
        self.fail_on_call = fail_on_call
        self.document_calls: list[list[str]] = []
        self.query_calls: list[str] = []

    def embed_documents(self, texts):
        self.document_calls.append(list(texts))
        if self.fail_on_call == len(self.document_calls):
            raise RuntimeError("embedding API unavailable (fake)")
        return [self._one_hot(t) for t in texts]

    def embed_query(self, text):
        self.query_calls.append(text)
        return pad(*self.queries[text])

    @staticmethod
    def _one_hot(text):
        vector = [0.0] * DIM
        vector[int(hashlib.sha256(text.encode()).hexdigest(), 16) % DIM] = 1.0
        return vector
