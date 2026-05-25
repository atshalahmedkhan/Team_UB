"""
Macro market data ingestion pipeline.

Pulls FRED and yfinance series (2015–present), computes derived features,
forward returns, rolling normalization, and bulk-upserts daily documents
into MongoDB ``market_states``.
"""

from __future__ import annotations

import os
import warnings
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv
from pymongo import ASCENDING, UpdateOne

from quant.storage.mongo_client import db

load_dotenv()

START_DATE = "2015-01-01"
ZSCORE_WINDOW = 252
ZSCORE_MIN_PERIODS = 60
ROC_WINDOW = 20
NAN_ROW_THRESHOLD = 0.30

# Populated when series fail to download (surfaced in run_day1).
MISSING_SERIES_WARNINGS: list[str] = []

FRED_SERIES: dict[str, str] = {
    "GS2": "yield_2y",
    "GS5": "yield_5y",
    "GS10": "yield_10y",
    "GS30": "yield_30y",
    "T10Y2Y": "spread_2s10s",
    "T10Y3M": "spread_3m10y",
    "DFII10": "real_yield",
    "BAMLC0A0CM": "ig_spread",
    "BAMLH0A0HYM2": "hy_spread",
    "MLEMPIMP": "move_index",
}

YFINANCE_TICKERS: dict[str, str] = {
    "^VIX": "vix",
    "^VIX3M": "vix3m",
    "^VVIX": "vvix",
    "DX-Y.NYB": "dxy",
    "GC=F": "gold",
    "HG=F": "copper",
    "CL=F": "oil",
    "^GSPC": "sp500",
    "^RUT": "russell2000",
    "^IXIC": "nasdaq",
    "XLK": "xlk_tech",
    "XLU": "xlu_utilities",
    "XLY": "xly_consumer",
}


def _end_date() -> str:
    """Return today's date as YYYY-MM-DD."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _fred_api_key() -> Optional[str]:
    """Return FRED API key from environment."""
    return os.getenv("FRED_API_KEY")


def _fetch_fred_via_api(series_id: str, api_key: str) -> pd.Series:
    """
    Fetch a single FRED series via the St. Louis Fed REST API.

    Args:
        series_id: FRED series identifier.
        api_key: FRED API key.

    Returns:
        pd.Series: Date-indexed observations.

    Raises:
        requests.RequestException: On HTTP failures.
        ValueError: If the response contains no observations.
    """
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": START_DATE,
        "observation_end": _end_date(),
    }
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    observations = response.json().get("observations", [])
    if not observations:
        raise ValueError(f"No observations returned for {series_id}")

    dates: list[pd.Timestamp] = []
    values: list[float] = []
    for obs in observations:
        raw_val = obs.get("value", ".")
        if raw_val in (".", "", None):
            continue
        dates.append(pd.Timestamp(obs["date"]))
        values.append(float(raw_val))

    return pd.Series(values, index=dates, name=series_id).sort_index()


def _fetch_fred_via_datareader(series_id: str, api_key: Optional[str]) -> pd.Series:
    """
    Fetch a FRED series using pandas-datareader (preferred when compatible).

    Args:
        series_id: FRED series identifier.
        api_key: Optional FRED API key.

    Returns:
        pd.Series: Date-indexed observations.
    """
    from pandas_datareader import data as pdr

    frame = pdr.DataReader(
        series_id,
        "fred",
        start=START_DATE,
        end=_end_date(),
        api_key=api_key,
    )
    if isinstance(frame, pd.DataFrame):
        return frame.iloc[:, 0]
    return frame


def _pull_fred_series() -> pd.DataFrame:
    """
    Download configured FRED series into a single DataFrame.

    Uses pandas-datareader when available; falls back to the FRED REST API.

    Returns:
        pd.DataFrame: Columns named by internal variable keys.
    """
    frames: list[pd.Series] = []
    api_key = _fred_api_key()
    use_datareader = True

    try:
        from pandas_datareader import data as _pdr  # noqa: F401
    except Exception:  # noqa: BLE001
        use_datareader = False

    for series_id, col_name in FRED_SERIES.items():
        try:
            print(f"  [FRED] {series_id} -> {col_name}")
            series: pd.Series
            if api_key:
                try:
                    if use_datareader:
                        series = _fetch_fred_via_datareader(series_id, api_key)
                    else:
                        raise ImportError("pandas-datareader unavailable")
                except Exception:  # noqa: BLE001
                    series = _fetch_fred_via_api(series_id, api_key)
            elif use_datareader:
                series = _fetch_fred_via_datareader(series_id, api_key)
            else:
                raise ValueError("FRED_API_KEY is not set and pandas-datareader is unavailable")
            series.name = col_name
            frames.append(series)
        except Exception as exc:  # noqa: BLE001 — graceful skip per spec
            msg = f"FRED series {series_id} ({col_name}) unavailable: {exc}"
            print(f"  Warning: {msg}")
            MISSING_SERIES_WARNINGS.append(msg)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, axis=1)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def _pull_yfinance_series() -> pd.DataFrame:
    """
    Download configured yfinance tickers (Close) into a DataFrame.

    Returns:
        pd.DataFrame: Columns named by internal variable keys.
    """
    tickers = list(YFINANCE_TICKERS.keys())
    col_map = YFINANCE_TICKERS

    try:
        print(f"  [yfinance] Downloading {len(tickers)} tickers...")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data = yf.download(
                tickers,
                start=START_DATE,
                end=_end_date(),
                progress=False,
                auto_adjust=True,
                threads=True,
            )
    except Exception as exc:  # noqa: BLE001
        msg = f"yfinance batch download failed: {exc}"
        print(f"  Warning: {msg}")
        MISSING_SERIES_WARNINGS.append(msg)
        return pd.DataFrame()

    frames: list[pd.Series] = []

    if isinstance(data.columns, pd.MultiIndex):
        # Multi-ticker download
        for ticker, col_name in col_map.items():
            try:
                if ticker in data["Close"].columns:
                    series = data["Close"][ticker].copy()
                else:
                    raise KeyError(ticker)
                series.name = col_name
                frames.append(series)
            except Exception as exc:  # noqa: BLE001
                msg = f"yfinance {ticker} ({col_name}) unavailable: {exc}"
                print(f"  Warning: {msg}")
                MISSING_SERIES_WARNINGS.append(msg)
    else:
        # Single ticker edge case
        only_ticker = tickers[0]
        series = data["Close"].copy()
        series.name = col_map[only_ticker]
        frames.append(series)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, axis=1)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def _add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute derived macro variables on an aligned DataFrame.

    Args:
        df: Aligned raw macro DataFrame.

    Returns:
        pd.DataFrame: Input with derived columns appended.
    """
    out = df.copy()

    if "hy_spread" in out.columns and "ig_spread" in out.columns:
        out["hy_ig_spread"] = out["hy_spread"] - out["ig_spread"]

    if "vix3m" in out.columns and "vix" in out.columns:
        out["vix_term_ratio"] = out["vix3m"] / out["vix"]

    if "gold" in out.columns and "copper" in out.columns:
        out["gold_copper"] = out["gold"] / out["copper"]

    if "xlk_tech" in out.columns and "xlu_utilities" in out.columns:
        out["tech_defensive"] = out["xlk_tech"] / out["xlu_utilities"]

    if "sp500" in out.columns:
        ma200 = out["sp500"].rolling(200).mean()
        out["sp500_200d_gap"] = out["sp500"] / ma200 - 1

    if "russell2000" in out.columns and "sp500" in out.columns:
        out["russell_sp"] = out["russell2000"] / out["sp500"]

    return out


def build_macro_dataframe() -> pd.DataFrame:
    """
    Pull, align, and clean macro market data (raw variables only).

    Returns:
        pd.DataFrame: One row per trading day with raw and derived columns.
    """
    print("[MACRO] Building macro DataFrame...")
    fred_df = _pull_fred_series()
    yf_df = _pull_yfinance_series()

    if fred_df.empty and yf_df.empty:
        raise RuntimeError("No macro data could be downloaded.")

    combined = pd.concat([fred_df, yf_df], axis=1)
    combined = combined.sort_index()
    combined = combined.ffill()

    combined = _add_derived_columns(combined)

    # Drop rows where more than 30% of values are missing
    nan_frac = combined.isna().mean(axis=1)
    before = len(combined)
    combined = combined.loc[nan_frac <= NAN_ROW_THRESHOLD]
    dropped = before - len(combined)
    if dropped:
        print(f"  Dropped {dropped} rows with >{NAN_ROW_THRESHOLD:.0%} NaN columns")

    print(f"  Macro DataFrame: {combined.shape[0]} rows × {combined.shape[1]} columns")
    return combined


def compute_future_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Attach forward S&P 500 returns (no look-ahead in features).

    Args:
        df: Macro DataFrame containing ``sp500``.

    Returns:
        pd.DataFrame: Copy of ``df`` with ``ret_30d``, ``ret_60d``, ``ret_90d``.
    """
    out = df.copy()
    if "sp500" not in out.columns:
        print("  Warning: sp500 missing — forward returns will be NaN")
        out["ret_30d"] = np.nan
        out["ret_60d"] = np.nan
        out["ret_90d"] = np.nan
        return out

    price = out["sp500"]
    out["ret_30d"] = price.shift(-30) / price - 1
    out["ret_60d"] = price.shift(-60) / price - 1
    out["ret_90d"] = price.shift(-90) / price - 1
    return out


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute rolling z-score, expanding percentile, and 20-day ROC per raw column.

    Args:
        df: DataFrame with raw macro columns (and optional return columns).

    Returns:
        pd.DataFrame: Normalized columns only (``*_zscore``, ``*_pct``, ``*_roc20``).
    """
    return_cols = {"ret_30d", "ret_60d", "ret_90d"}
    raw_cols = [c for c in df.columns if c not in return_cols]

    norm = pd.DataFrame(index=df.index)

    for col in raw_cols:
        series = df[col]
        rolling_mean = series.rolling(ZSCORE_WINDOW, min_periods=ZSCORE_MIN_PERIODS).mean()
        rolling_std = series.rolling(ZSCORE_WINDOW, min_periods=ZSCORE_MIN_PERIODS).std()
        norm[f"{col}_zscore"] = (series - rolling_mean) / rolling_std
        norm[f"{col}_pct"] = series.expanding().rank(pct=True)
        shifted = series.shift(ROC_WINDOW)
        norm[f"{col}_roc20"] = (series / shifted) - 1

    return norm


def _to_python_float(value: Any) -> Optional[float]:
    """
    Convert a scalar to a Python float or None for MongoDB.

    Args:
        value: Numeric or missing value.

    Returns:
        Optional[float]: Native float, or None if missing.
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return float(value)


def _series_to_dict(series: pd.Series) -> dict[str, Optional[float]]:
    """
    Convert a pandas Series to a MongoDB-safe dict of floats.

    Args:
        series: Row of values.

    Returns:
        dict[str, Optional[float]]: Column → float or None.
    """
    return {str(k): _to_python_float(v) for k, v in series.items()}


def store_to_mongo(raw_df: pd.DataFrame, norm_df: pd.DataFrame) -> dict[str, int]:
    """
    Bulk upsert daily market state documents into MongoDB.

    Args:
        raw_df: Raw macro variables (may include forward return columns).
        norm_df: Normalized feature columns.

    Returns:
        dict[str, int]: Bulk write stats with keys ``upserted`` and ``modified``.
    """
    if db is None:
        raise RuntimeError("MongoDB is not connected. Set MONGO_URI in .env.")

    collection = db["market_states"]
    collection.create_index([("date", ASCENDING)], unique=True)

    return_cols = ["ret_30d", "ret_60d", "ret_90d"]
    raw_cols = [c for c in raw_df.columns if c not in return_cols]

    operations: list[UpdateOne] = []
    stored_at = datetime.now(timezone.utc)

    for idx in raw_df.index:
        date_str = pd.Timestamp(idx).strftime("%Y-%m-%d")
        raw_row = raw_df.loc[idx, raw_cols]
        norm_row = norm_df.loc[idx] if idx in norm_df.index else pd.Series(dtype=float)

        ret_fields = {
            col: _to_python_float(raw_df.loc[idx, col]) if col in raw_df.columns else None
            for col in return_cols
        }

        doc = {
            "date": date_str,
            "raw": _series_to_dict(raw_row),
            "normalized": _series_to_dict(norm_row),
            "ret_30d": ret_fields["ret_30d"],
            "ret_60d": ret_fields["ret_60d"],
            "ret_90d": ret_fields["ret_90d"],
            "market_vector": None,
            "regime_label": None,
            "analog_dates": None,
            "stored_at": stored_at,
        }

        operations.append(
            UpdateOne({"date": date_str}, {"$set": doc}, upsert=True)
        )

    print(f"[MACRO] Upserting {len(operations)} market state documents...")
    result = collection.bulk_write(operations, ordered=False)

    stats = {
        "upserted": result.upserted_count,
        "modified": result.modified_count,
    }
    print(f"  Upserted: {stats['upserted']} | Modified: {stats['modified']}")
    return stats


def run_macro_pipeline() -> dict[str, int]:
    """
    Execute the full macro ingestion pipeline end-to-end.

    Returns:
        dict[str, int]: MongoDB bulk write statistics from ``store_to_mongo``.
    """
    raw_df = build_macro_dataframe()
    raw_df = compute_future_returns(raw_df)
    norm_df = normalize_dataframe(raw_df)
    return store_to_mongo(raw_df, norm_df)
