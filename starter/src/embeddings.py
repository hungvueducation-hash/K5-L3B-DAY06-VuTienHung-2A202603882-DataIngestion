"""Local embedding model (sentence-transformers) — no API key required.

Chosen model: sentence-transformers/all-MiniLM-L6-v2, 384 dimensions.
Reasoning: corpus and benchmark questions are English, the model is small
enough to run on CPU within the lab's time budget, and cost is $0 (no API).
Query and document texts are embedded with the same model/call, so they are
directly comparable under cosine similarity.
"""
from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Local sentence-transformers adapter. Raises if the model fails to load."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self.dimensions = self._model.get_embedding_dimension()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vectors]

    def embed_query(self, question: str) -> list[float]:
        vector = self._model.encode([question], normalize_embeddings=True, show_progress_bar=False)[0]
        return vector.tolist()
