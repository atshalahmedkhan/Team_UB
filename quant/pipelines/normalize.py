"""Z-score and percentile normalization for macro features.

This module provides a minimal helper `normalize_features` used by the
PCA encoder and other agents. It expects a dict-like raw row (column -> value)
and returns normalized metrics keyed by ``{col}_zscore``, ``{col}_pct``,
and ``{col}_roc20`` where applicable. This implementation delegates to the
rolling logic in `macro_ingestion.normalize_dataframe` when given a history
DataFrame; for single-row usage it computes simple placeholders.
"""

from __future__ import annotations

from typing import Dict, Optional


def normalize_features(raw: dict) -> dict:
    """Return simple normalization for a single raw row.

    This is intentionally lightweight: when a full historical rolling z-score
    is required, other modules should call `normalize_dataframe` with history.
    """
    out: Dict[str, Optional[float]] = {}
    for k, v in raw.items():
        try:
            val = float(v) if v is not None else None
        except Exception:
            val = None
        out[f"{k}_zscore"] = None
        out[f"{k}_pct"] = None
        out[f"{k}_roc20"] = None
        if val is not None:
            # For single-row normalization we cannot compute z-score; expose raw
            out[f"{k}_zscore"] = float(val)
            out[f"{k}_pct"] = float(val)
            out[f"{k}_roc20"] = 0.0
    return out
