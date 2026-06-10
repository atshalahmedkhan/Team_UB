"""Elastic MCP bridge — exposes market-state kNN as HTTP tools for Agent Builder."""

from __future__ import annotations

import os
from typing import Any

from elasticsearch import Elasticsearch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

INDEX_NAME = os.getenv("ELASTIC_INDEX", "market-states")
VECTOR_DIMS = 15

app = FastAPI(title="Quant Elastic MCP Bridge", version="1.0.0")


class KnnRequest(BaseModel):
    vector: list[float] = Field(..., min_length=VECTOR_DIMS, max_length=VECTOR_DIMS)
    k: int = Field(default=10, ge=1, le=50)


def _client() -> Elasticsearch:
    url = os.getenv("ELASTIC_URL", "").strip()
    api_key = os.getenv("ELASTIC_API_KEY", "").strip()
    if not url or not api_key:
        raise HTTPException(status_code=500, detail="ELASTIC_URL and ELASTIC_API_KEY required")
    return Elasticsearch(url, api_key=api_key, request_timeout=60)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "quant-elastic-mcp-bridge"}


@app.get("/tools")
def list_tools() -> dict[str, Any]:
    """Tool catalog for Agent Builder / MCP registration."""
    return {
        "tools": [
            {
                "name": "market_state_knn",
                "description": (
                    "Find top-k historical market regime days similar to a 15-dim PCA vector."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "vector": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": VECTOR_DIMS,
                            "maxItems": VECTOR_DIMS,
                        },
                        "k": {"type": "integer", "default": 10},
                    },
                    "required": ["vector"],
                },
            }
        ]
    }


@app.post("/tools/market_state_knn")
def market_state_knn(request: KnnRequest) -> dict[str, Any]:
    """Run dense_vector kNN on the market-states Elastic index."""
    es = _client()
    k = request.k
    try:
        response = es.search(
            index=INDEX_NAME,
            knn={
                "field": "market_vector",
                "query_vector": [float(x) for x in request.vector],
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
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Elastic kNN failed: {exc}") from exc

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

    return {"index": INDEX_NAME, "k": k, "hits": hits, "count": len(hits)}


# Streamable HTTP MCP clients often probe /mcp — redirect to tool catalog.
@app.get("/mcp")
def mcp_info() -> dict[str, str]:
    return {
        "message": "Quant Elastic MCP bridge",
        "tools_endpoint": "/tools",
        "knn_endpoint": "/tools/market_state_knn",
    }
