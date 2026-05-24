"""
Tests for macro market data ingestion pipeline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.pipelines.macro_ingestion import (
    build_macro_dataframe,
    compute_future_returns,
    normalize_dataframe,
    store_to_mongo,
)


def test_dataframe_shape() -> None:
    """Macro DataFrame should have sufficient history and breadth."""
    df = build_macro_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 2000
    assert df.shape[1] > 15


def test_no_lookahead() -> None:
    """Rolling z-scores must use only past data (NaN until min_periods=60)."""
    raw_df = build_macro_dataframe()
    norm_df = normalize_dataframe(raw_df)
    zscore_cols = [c for c in norm_df.columns if c.endswith("_zscore")]
    assert zscore_cols
    # With min_periods=60, the first valid z-score is at row index 59 (60th row).
    first_59_rows = norm_df[zscore_cols].iloc[:59]
    assert first_59_rows.isna().all().all()


def test_future_returns() -> None:
    """Last 30 rows should have NaN ret_30d (no future prices yet)."""
    raw_df = build_macro_dataframe()
    df = compute_future_returns(raw_df)
    assert "ret_30d" in df.columns
    last_30 = df["ret_30d"].iloc[-30:]
    assert last_30.isna().all()


def test_store_idempotent(requires_mongo) -> None:
    """Running store_to_mongo twice must not duplicate documents."""
    raw_df = build_macro_dataframe()
    raw_df = compute_future_returns(raw_df)
    norm_df = normalize_dataframe(raw_df)

    store_to_mongo(raw_df, norm_df)
    count_after_first = requires_mongo["market_states"].count_documents({})

    store_to_mongo(raw_df, norm_df)
    count_after_second = requires_mongo["market_states"].count_documents({})

    assert count_after_second == count_after_first


def test_date_index(requires_mongo) -> None:
    """All stored market state dates must be unique."""
    raw_df = build_macro_dataframe()
    raw_df = compute_future_returns(raw_df)
    norm_df = normalize_dataframe(raw_df)
    store_to_mongo(raw_df, norm_df)

    pipeline = [
        {"$group": {"_id": "$date", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
    ]
    duplicates = list(requires_mongo["market_states"].aggregate(pipeline))
    assert duplicates == []
