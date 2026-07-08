"""Embedding generation and vector search."""

from __future__ import annotations

import hashlib
import math
from typing import List, Optional, Sequence, Tuple

import numpy as np

from mediacurator.config_store import Settings
from mediacurator.library.db import Database


def _hash_embed(text: str, dims: int = 384) -> List[float]:
    """Deterministic fallback embedding when no LLM embedding API is configured."""
    vector = np.zeros(dims, dtype=np.float32)
    tokens = text.lower().split()
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for index in range(dims):
            vector[index] += (digest[index % len(digest)] / 255.0) - 0.5
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector.tolist()


async def embed_text(text: str, settings: Settings) -> List[float]:
    if not settings.llm_api_key:
        return _hash_embed(text)
    try:
        from mediacurator.agent.providers import get_embedding_provider

        provider = get_embedding_provider(settings)
        return await provider.embed(text)
    except Exception:
        return _hash_embed(text)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def build_item_embedding_text(row) -> str:
    genres = row["genres"] if isinstance(row["genres"], str) else "[]"
    keywords = row["keywords"] if isinstance(row["keywords"], str) else "[]"
    return "\n".join(
        part
        for part in [
            row["title"],
            str(row["year"] or ""),
            row["summary"] or "",
            genres,
            keywords,
        ]
        if part
    )


async def rebuild_embeddings(db: Database, settings: Settings) -> int:
    count = 0
    for row in db.all_library_items():
        text = await build_item_embedding_text(row)
        vector = await embed_text(text, settings)
        db.set_embedding(int(row["id"]), vector)
        count += 1
    return count


def semantic_search(
    db: Database,
    query_vector: Sequence[float],
    *,
    limit: int = 20,
    media_type: Optional[str] = None,
) -> List[Tuple[int, float]]:
    scores: List[Tuple[int, float]] = []
    items = {int(row["id"]): row for row in db.all_library_items()}
    for item_id, vector in db.get_embeddings():
        if media_type and items.get(item_id, {}).get("media_type") != media_type:
            continue
        score = cosine_similarity(query_vector, vector)
        scores.append((item_id, score))
    scores.sort(key=lambda item: item[1], reverse=True)
    return scores[:limit]
