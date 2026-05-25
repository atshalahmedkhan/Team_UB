"""
Today's market fingerprint — live macro pull, rolling normalization, PCA transform.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from quant.agents.fingerprint_agent import (  # noqa: E402
    MODEL_PATH,
    _to_python_float,
    _vector_to_list,
    assign_regime_label,
)
from quant.pipelines.macro_ingestion import (  # noqa: E402
    ZSCORE_MIN_PERIODS,
    ZSCORE_WINDOW,
    build_macro_dataframe,
)
from quant.storage.mongo_client import db  # noqa: E402

ROLLING_HISTORY_DAYS = 252


def load_pca_artifact() -> dict[str, Any]:
    """
    Load the fitted PCA model artifact from disk.

    Returns:
        dict: Keys ``pca``, ``feature_columns``, ``component_stds``.

    Raises:
        FileNotFoundError: If models/pca_model.pkl does not exist.
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"PCA model not found at {MODEL_PATH}. Run agents.fingerprint_agent first."
        )
    return joblib.load(MODEL_PATH)


def load_historical_raw(days: int = ROLLING_HISTORY_DAYS) -> pd.DataFrame:
    """
    Load the last N trading days of raw macro data from MongoDB.

    Args:
        days: Number of historical days to retrieve.

    Returns:
        pd.DataFrame: Date-indexed raw macro columns.
    """
    if db is None:
        raise RuntimeError("MongoDB is not connected. Set MONGO_URI in .env.")

    cursor = (
        db["market_states"]
        .find(
            {"date": {"$nin": ["today", None]}},
            {"date": 1, "raw": 1},
        )
        .sort("date", -1)
        .limit(days)
    )
    docs = list(cursor)
    if not docs:
        raise ValueError("No historical market_states found in MongoDB.")

    rows: dict[str, dict[str, float]] = {}
    for doc in reversed(docs):
        raw = doc.get("raw") or {}
        rows[doc["date"]] = {
            k: float(v) for k, v in raw.items() if v is not None
        }

    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def normalize_today_row(
    today_raw: pd.Series,
    history_df: pd.DataFrame,
) -> dict[str, Optional[float]]:
    """
    Z-score today's raw values using rolling stats from historical MongoDB data.

    Args:
        today_raw: Latest raw macro values (one row).
        history_df: Historical raw macro DataFrame (date-indexed).

    Returns:
        dict[str, Optional[float]]: Normalized z-score fields for today only.
    """
    combined = history_df.copy()
    today_idx = pd.Timestamp(datetime.now(timezone.utc).date())
    combined.loc[today_idx] = today_raw
    combined = combined.sort_index()

    norm: dict[str, Optional[float]] = {}
    for col in today_raw.index:
        if col not in combined.columns:
            continue
        series = combined[col]
        rolling_mean = series.rolling(ZSCORE_WINDOW, min_periods=ZSCORE_MIN_PERIODS).mean()
        rolling_std = series.rolling(ZSCORE_WINDOW, min_periods=ZSCORE_MIN_PERIODS).std()
        zscore = (series.iloc[-1] - rolling_mean.iloc[-1]) / rolling_std.iloc[-1]
        norm[f"{col}_zscore"] = _to_python_float(zscore)

    return norm


def get_today_raw_row() -> pd.Series:
    """
    Pull today's macro data using the Day 1 macro pipeline.

    Returns:
        pd.Series: Latest row of raw macro variables.
    """
    macro_df = build_macro_dataframe()
    if macro_df.empty:
        raise RuntimeError("Could not build today's macro DataFrame.")
    return macro_df.iloc[-1]


def compute_today_fingerprint() -> dict[str, Any]:
    """
    Build today's 15-dimensional PCA fingerprint without refitting PCA.

    Returns:
        dict: Keys ``vector``, ``regime_label``, ``normalized``, ``raw``.
    """
    artifact = load_pca_artifact()
    pca = artifact["pca"]
    feature_columns: list[str] = artifact["feature_columns"]
    component_stds: np.ndarray = artifact["component_stds"]

    today_raw = get_today_raw_row()
    history_df = load_historical_raw(ROLLING_HISTORY_DAYS)
    normalized = normalize_today_row(today_raw, history_df)

    feature_row = [
        float(normalized.get(col) or 0.0) for col in feature_columns
    ]
    vector = pca.transform(np.array([feature_row]))[0]
    regime = assign_regime_label(vector, component_stds)

    return {
        "vector": _vector_to_list(vector),
        "regime_label": regime,
        "normalized": normalized,
        "raw": {k: _to_python_float(v) for k, v in today_raw.items()},
    }


def save_today_state(fingerprint: dict[str, Any]) -> None:
    """
    Upsert today's market state document in MongoDB (date=\"today\").

    Args:
        fingerprint: Output from ``compute_today_fingerprint``.
    """
    if db is None:
        raise RuntimeError("MongoDB is not connected. Set MONGO_URI in .env.")

    doc = {
        "date": "today",
        "raw": fingerprint["raw"],
        "normalized": fingerprint["normalized"],
        "market_vector": fingerprint["vector"],
        "regime_label": fingerprint["regime_label"],
        "ret_30d": None,
        "ret_60d": None,
        "ret_90d": None,
        "analog_dates": None,
        "stored_at": datetime.now(timezone.utc),
    }
    db["market_states"].update_one({"date": "today"}, {"$set": doc}, upsert=True)
    print("[TODAY] Saved today's fingerprint to MongoDB (date='today')")


def get_today_vector() -> tuple[list[float], str, dict[str, Any]]:
    """
    Compute, persist, and return today's PCA vector and regime label.

    Returns:
        tuple[list[float], str, dict]: Vector, regime_label, full fingerprint dict.
    """
    fingerprint = compute_today_fingerprint()
    save_today_state(fingerprint)
    return fingerprint["vector"], fingerprint["regime_label"], fingerprint


def describe_regime(regime_label: str) -> str:
    """
    Return a plain-English description of the current regime label.

    Args:
        regime_label: PCA-derived regime string.

    Returns:
        str: Human-readable regime summary.
    """
    descriptions = {
        "Risk-off stress": (
            "Markets are in a risk-off stress regime — elevated fear, "
            "widening spreads, or defensive positioning dominate."
        ),
        "Rate shock": (
            "Markets are in a rate-shock regime — yield curve and rate "
            "sensitivity are the primary drivers of cross-asset moves."
        ),
        "Risk-on rally": (
            "Markets are in a risk-on rally regime — volatility is subdued "
            "and risk assets are bid."
        ),
        "Neutral regime": (
            "Markets are in a neutral regime — no single macro factor "
            "dominates the fingerprint."
        ),
    }
    return descriptions.get(
        regime_label,
        f"Current regime: {regime_label}.",
    )


def main() -> None:
    """CLI entry point — print today's fingerprint."""
    print("=" * 60)
    print("Quant — Today's Market Fingerprint")
    print("=" * 60)
    vector, regime, fp = get_today_vector()
    print(f"Regime: {regime}")
    print(f"Vector (15-dim): {vector}")
    print(describe_regime(regime))
    vix = fp["raw"].get("vix")
    y10 = fp["raw"].get("yield_10y")
    spread = fp["raw"].get("spread_2s10s")
    print(f"VIX: {vix} | 10Y: {y10} | 2s10s: {spread}")


if __name__ == "__main__":
    main()
