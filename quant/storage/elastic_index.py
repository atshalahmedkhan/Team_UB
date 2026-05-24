"""Elastic dense_vector index for market_state_v1."""

INDEX_NAME = "market_state_v1"
VECTOR_DIMS = 15


def knn_query(vector: list[float], k: int = 10) -> list[dict]:
    raise NotImplementedError
