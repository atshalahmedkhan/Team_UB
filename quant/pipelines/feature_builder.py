"""Build ~55-dim feature vector from normalized macro series.

This lightweight implementation selects all keys that end with "_zscore",
orders them alphabetically, and returns their values as a float list. If fewer
than 55 features are present, the output is padded with zeros to 55 dims.
"""

from __future__ import annotations

from typing import Dict, List


TARGET_DIMS = 55


def build_features(normalized: Dict[str, float]) -> List[float]:
    """Convert a normalized dict (e.g. `{col_zscore: val}`) to a fixed-length feature list."""
    keys = sorted([k for k in normalized.keys() if k.endswith("_zscore")])
    vals = []
    for k in keys:
        v = normalized.get(k)
        try:
            vals.append(float(v) if v is not None else 0.0)
        except Exception:
            vals.append(0.0)

    # Pad or trim to TARGET_DIMS
    if len(vals) >= TARGET_DIMS:
        return vals[:TARGET_DIMS]
    vals.extend([0.0] * (TARGET_DIMS - len(vals)))
    return vals
