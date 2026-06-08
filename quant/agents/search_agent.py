"""
Elastic Cloud indexer and kNN analog search for market_states.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from quant.storage.mongo_client import db  # noqa: E402

INDEX_NAME = "market-states"
VECTOR_DIMS = 15


def get_elastic_client() -> Optional[Any]:
    """
    Create an Elasticsearch client from environment variables.

    Returns:
        Optional[Elasticsearch]: Connected client, or None if credentials missing.
    """
    url = os.getenv("ELASTIC_URL")
    api_key = os.getenv("ELASTIC_API_KEY")
    if not url or not api_key:
        print("Warning: ELASTIC_URL or ELASTIC_API_KEY not set — Elastic disabled.")
        return None

    try:
        from elasticsearch import Elasticsearch

        return Elasticsearch(url, api_key=api_key, request_timeout=60)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: Could not connect to Elastic: {exc}")
        return None


def index_mapping() -> dict[str, Any]:
    """
    Return the Elasticsearch index mapping for market-states.

    Returns:
        dict: Index settings and property mappings.
    """
    return {
        "mappings": {
            "properties": {
                "date": {"type": "keyword"},
                "market_vector": {
                    "type": "dense_vector",
                    "dims": VECTOR_DIMS,
                    "index": True,
                    "similarity": "cosine",
                },
                "ret_30d": {"type": "float"},
                "ret_60d": {"type": "float"},
                "ret_90d": {"type": "float"},
                "regime_label": {"type": "keyword"},
                "raw_vix": {"type": "float"},
                "raw_spread_2s10s": {"type": "float"},
                "raw_yield_10y": {"type": "float"},
            }
        }
    }


def ensure_index(client: Any) -> bool:
    """
    Create the market-states index if it does not exist.

    Args:
        client: Elasticsearch client.

    Returns:
        bool: True if index is ready, False on failure.
    """
    try:
        if not client.indices.exists(index=INDEX_NAME):
            client.indices.create(index=INDEX_NAME, body=index_mapping())
            print(f"  Created index '{INDEX_NAME}'")
        else:
            print(f"  Index '{INDEX_NAME}' already exists")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: Failed to create index: {exc}")
        return False


def _safe_raw_float(raw: Optional[dict[str, Any]], key: str) -> Optional[float]:
    """
    Pull a float from a nested raw dict, returning None if missing.

    Args:
        raw: Raw macro sub-document.
        key: Field name inside raw.

    Returns:
        Optional[float]: Native float or None.
    """
    if not raw:
        return None
    value = raw.get(key)
    if value is None:
        return None
    return float(value)


def document_from_mongo(doc: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a MongoDB market_state document to an Elastic bulk action body.

    Args:
        doc: MongoDB market_states document.

    Returns:
        dict: Elasticsearch document fields.
    """
    raw = doc.get("raw") or {}
    return {
        "date": doc["date"],
        "market_vector": doc["market_vector"],
        "ret_30d": doc.get("ret_30d"),
        "ret_60d": doc.get("ret_60d"),
        "ret_90d": doc.get("ret_90d"),
        "regime_label": doc.get("regime_label"),
        "raw_vix": _safe_raw_float(raw, "vix"),
        "raw_spread_2s10s": _safe_raw_float(raw, "spread_2s10s"),
        "raw_yield_10y": _safe_raw_float(raw, "yield_10y"),
    }


def bulk_index_market_states(client: Optional[Any] = None) -> dict[str, int]:
    """
    Bulk-index all market_states with non-null market_vector into Elastic.

    Args:
        client: Optional Elasticsearch client; created if omitted.

    Returns:
        dict[str, int]: Keys ``indexed``, ``failed``, ``skipped``.
    """
    if db is None:
        raise RuntimeError("MongoDB is not connected. Set MONGO_URI in .env.")

    es = client or get_elastic_client()
    if es is None:
        return {"indexed": 0, "failed": 0, "skipped": 0}

    if not ensure_index(es):
        return {"indexed": 0, "failed": 0, "skipped": 0}

    cursor = db["market_states"].find(
        {"market_vector": {"$ne": None}, "date": {"$ne": "today"}},
        sort=[("date", 1)],
    )
    docs = list(cursor)
    print(f"[SEARCH] Indexing {len(docs)} documents into Elastic...")

    from elasticsearch.helpers import bulk

    actions = [
        {
            "_index": INDEX_NAME,
            "_id": doc["date"],
            "_source": document_from_mongo(doc),
        }
        for doc in docs
        if doc.get("market_vector") is not None
    ]

    if not actions:
        print("  No documents to index.")
        return {"indexed": 0, "failed": 0, "skipped": 0}

    try:
        success, errors = bulk(es, actions, raise_on_error=False, chunk_size=500)
        failed = len(errors) if isinstance(errors, list) else 0
        print(f"  Indexed: {success} | Failed: {failed}")
        return {"indexed": success, "failed": failed, "skipped": 0}
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: Bulk index failed: {exc}")
        return {"indexed": 0, "failed": len(actions), "skipped": 0}


def _mongo_knn_fallback(query_vector: list[float], k: int) -> list[dict[str, Any]]:
    """Cosine kNN over MongoDB market_states when Elastic is unavailable."""
    from quant.storage.elastic_index import knn_query

    neighbors = knn_query(query_vector, k=k)
    hits: list[dict[str, Any]] = []
    for neighbor in neighbors:
        date = neighbor.get("date")
        doc = db["market_states"].find_one({"date": date}) if db is not None else None
        raw = (doc or {}).get("raw") or {}
        hits.append(
            {
                "date": date,
                "similarity_score": float(neighbor.get("similarity", 0.0)),
                "ret_30d": (doc or {}).get("ret_30d"),
                "ret_60d": (doc or {}).get("ret_60d"),
                "ret_90d": (doc or {}).get("ret_90d"),
                "regime_label": (doc or {}).get("regime_label"),
                "raw_vix": raw.get("vix"),
                "raw_spread_2s10s": raw.get("spread_2s10s"),
            }
        )
    return hits


def search_analogs(
    query_vector: list[float],
    k: int = 10,
    client: Optional[Any] = None,
) -> list[dict[str, Any]]:
    """
    Run kNN cosine search for historical analog market states.

    Uses Elasticsearch when configured; falls back to MongoDB cosine similarity.

    Args:
        query_vector: 15-dimensional PCA fingerprint for today.
        k: Number of nearest neighbors to return.
        client: Optional Elasticsearch client.

    Returns:
        list[dict]: Analog hits with date, similarity_score, returns, regime, raw fields.
    """
    es = client or get_elastic_client()
    if es is not None:
        try:
            response = es.search(
                index=INDEX_NAME,
                knn={
                    "field": "market_vector",
                    "query_vector": query_vector,
                    "k": k,
                    "num_candidates": max(k * 10, 100),
                },
                _source=[
                    "date",
                    "ret_30d",
                    "ret_60d",
                    "ret_90d",
                    "regime_label",
                    "raw_vix",
                    "raw_spread_2s10s",
                ],
            )
            hits: list[dict[str, Any]] = []
            for hit in response.get("hits", {}).get("hits", []):
                source = hit.get("_source", {})
                hits.append(
                    {
                        "date": source.get("date"),
                        "similarity_score": float(hit.get("_score", 0.0)),
                        "ret_30d": source.get("ret_30d"),
                        "ret_60d": source.get("ret_60d"),
                        "ret_90d": source.get("ret_90d"),
                        "regime_label": source.get("regime_label"),
                        "raw_vix": source.get("raw_vix"),
                        "raw_spread_2s10s": source.get("raw_spread_2s10s"),
                    }
                )
            return hits
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: Elastic kNN failed ({exc}) — using MongoDB fallback.")

    if db is None:
        print("Warning: MongoDB unavailable — returning empty analog list.")
        return []

    print("Warning: Elastic unavailable — using MongoDB cosine fallback.")
    return _mongo_knn_fallback(query_vector, k)


def main() -> None:
    """CLI entry point for Elastic bulk indexing."""
    print("=" * 60)
    print("Quant — Day 2 Elastic Market State Indexer")
    print("=" * 60)
    stats = bulk_index_market_states()
    print(f"\nDone. Indexed: {stats['indexed']} | Failed: {stats['failed']}")


if __name__ == "__main__":
    main()
