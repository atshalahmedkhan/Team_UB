"""Elastic dense_vector index for market_state_v1.

Provides a lightweight MongoDB fallback for kNN when an Elastic cluster is
not configured. The fallback computes cosine similarity between the query
vector and stored `market_vector` fields on `market_states` documents.
"""

from __future__ import annotations

from typing import List, Dict, Any
import math

from quant.storage.mongo_client import db

INDEX_NAME = "market_state_v1"
VECTOR_DIMS = 15


def _cosine(a: List[float], b: List[float]) -> float:
    da = sum(x * x for x in a)
    db = sum(y * y for y in b)
    if da == 0 or db == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    return float(dot / (math.sqrt(da) * math.sqrt(db)))


def knn_query(vector: List[float], k: int = 10) -> List[Dict[str, Any]]:
    """Return top-k analogs from MongoDB `market_states` by cosine similarity.

    Returns a list of dicts with keys: `date`, `similarity`, `market_vector`.
    """
    if db is None:
        raise RuntimeError("MongoDB is not connected. Set MONGO_URI in .env.")

    cursor = db["market_states"].find({"market_vector": {"$ne": None}}, {"date": 1, "market_vector": 1})
    scored: List[Dict[str, Any]] = []
    for doc in cursor:
        mv = doc.get("market_vector") or []
        try:
            score = _cosine(vector, mv)
        except Exception:
            score = 0.0
        scored.append({"date": doc.get("date"), "similarity": score, "market_vector": mv})

    scored.sort(key=lambda d: d["similarity"], reverse=True)
    return scored[:k]
