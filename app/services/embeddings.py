from __future__ import annotations

from dataclasses import dataclass

from .models import Chunk


@dataclass
class EmbeddingResult:
    chunk_id: str
    vector: list[float]


class EmbeddingService:
    def embed(self, chunks: list[Chunk]) -> list[EmbeddingResult]:
        # Placeholder for a real embedding model/provider.
        # The pipeline keeps this separate so the embedding backend can change
        # without affecting document structure or chunk generation.
        return [EmbeddingResult(chunk_id=chunk.meta.chunk_id, vector=[]) for chunk in chunks]

