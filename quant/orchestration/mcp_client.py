"""Optional MCP HTTP clients — use partner MCP endpoints when USE_MCP_TOOLS=true."""

from __future__ import annotations

import os
from typing import Any

import httpx

TIMEOUT = 60.0


def use_mcp_tools() -> bool:
    return os.getenv("USE_MCP_TOOLS", "false").strip().lower() in ("1", "true", "yes", "on")


def elastic_mcp_knn(vector: list[float], k: int = 10) -> list[dict[str, Any]] | None:
    """
    Call Elastic MCP bridge kNN tool. Returns None when MCP is disabled or misconfigured.
    """
    if not use_mcp_tools():
        return None

    base = (os.getenv("ELASTIC_MCP_URL") or "").strip().rstrip("/")
    if not base:
        return None

    url = f"{base}/tools/market_state_knn"
    payload = {"vector": [float(x) for x in vector], "k": k}
    try:
        response = httpx.post(url, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return list(data.get("hits", []))
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: Elastic MCP kNN failed ({exc}) — falling back to direct client.")
        return None


def mongodb_mcp_health() -> bool:
    """Return True if MongoDB MCP /mcp endpoint responds."""
    base = (os.getenv("MONGODB_MCP_URL") or "").strip().rstrip("/")
    if not base:
        return False
    try:
        response = httpx.get(f"{base}/mcp", timeout=10.0, follow_redirects=True)
        return response.status_code < 500
    except Exception:
        return False
