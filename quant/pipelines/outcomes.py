"""Forward return labels (30/60/90d) for historical market days.

This simple implementation looks for common return fields in the input
and ensures a stable `returns` dict exists. When forward returns are not
present it inserts `None` placeholders to preserve schema compatibility.
"""

from __future__ import annotations

from typing import Dict, Any


def attach_outcomes(market_day: Dict[str, Any]) -> Dict[str, Any]:
    returns = market_day.get("returns") or {}
    out = {
        "d30": returns.get("d30"),
        "d60": returns.get("d60"),
        "d90": returns.get("d90"),
    }
    market_day["returns"] = out
    return market_day
