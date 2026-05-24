"""
PCA fingerprint encoder for market_states.

Fits a 15-component PCA on normalized z-score features, persists the model,
and writes market_vector + regime_label back to MongoDB.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.decomposition import PCA

QUANT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = QUANT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from quant.pipelines.macro_ingestion import normalize_dataframe  # noqa: E402
from quant.storage.mongo_client import db  # noqa: E402

MODEL_PATH = QUANT_ROOT / "models" / "pca_model.pkl"
N_COMPONENTS = 15
NAN_ROW_THRESHOLD = 0.20
REGIME_STD_MULTIPLIER = 1.5


def _to_python_float(value: Any) -> Optional[float]:
    """
    Convert a scalar to a native Python float or None.

    Args:
        value: Numeric or missing value.

    Returns:
        Optional[float]: Native float, or None if missing.
    """
    if value is None:
        return None
    try:
        if pd.isna(value) or (isinstance(value, float) and np.isnan(value)):
            return None
    except (TypeError, ValueError):
        pass
    return float(value)


def _vector_to_list(vector: np.ndarray) -> list[float]:
    """
    Convert a PCA vector to a MongoDB-safe list of Python floats.

    Args:
        vector: 1-D numpy array of PCA components.

    Returns:
        list[float]: Fifteen native floats.
    """
    return [float(x) for x in vector.tolist()]


def load_market_states_without_vector() -> list[dict[str, Any]]:
    """
    Load market_states documents that have not yet been PCA-encoded.

    Returns:
        list[dict]: MongoDB documents with ``date != "today"`` and null market_vector.
    """
    if db is None:
        raise RuntimeError("MongoDB is not connected. Set MONGO_URI in .env.")

    cursor = db["market_states"].find(
        {
            "market_vector": None,
            "date": {"$ne": "today"},
        },
        sort=[("date", 1)],
    )
    return list(cursor)


def _zscore_row_from_doc(doc: dict[str, Any]) -> dict[str, float]:
    """
    Extract non-null z-score features from a market_state document.

    Args:
        doc: MongoDB market_states document.

    Returns:
        dict[str, float]: Column name → z-score value (may be empty).
    """
    normalized = doc.get("normalized") or {}
    return {
        k: float(v)
        for k, v in normalized.items()
        if k.endswith("_zscore") and v is not None
    }


def backfill_normalized_zscores(dates: list[str]) -> int:
    """
    Recompute normalized z-scores from raw data for dates with null z-scores.

    Early history rows often have z-score keys present but values None until the
    252-day rolling window fills. This rebuilds them from the full raw series.

    Args:
        dates: Date strings to backfill.

    Returns:
        int: Number of MongoDB documents updated.
    """
    if not dates or db is None:
        return 0

    cursor = db["market_states"].find(
        {"date": {"$nin": ["today", None]}},
        {"date": 1, "raw": 1},
    ).sort("date", 1)

    raw_rows: dict[str, dict[str, float]] = {}
    for doc in cursor:
        raw = doc.get("raw") or {}
        raw_rows[str(doc["date"])] = {
            k: float(v) for k, v in raw.items() if v is not None
        }

    if not raw_rows:
        return 0

    raw_df = pd.DataFrame.from_dict(raw_rows, orient="index")
    raw_df.index = pd.to_datetime(raw_df.index)
    raw_df = raw_df.sort_index()
    norm_df = normalize_dataframe(raw_df)

    collection = db["market_states"]
    updated = 0
    for date_str in dates:
        ts = pd.Timestamp(date_str)
        if ts not in norm_df.index:
            continue
        norm_row = norm_df.loc[ts]
        normalized = {
            str(k): _to_python_float(v) for k, v in norm_row.items()
        }
        collection.update_one({"date": date_str}, {"$set": {"normalized": normalized}})
        updated += 1

    if updated:
        print(f"  Backfilled normalized z-scores for {updated} early-history dates")
    return updated


def build_zscore_matrix(
    documents: list[dict[str, Any]],
    feature_columns: Optional[list[str]] = None,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Build a feature matrix from normalized z-score columns in MongoDB documents.

    Args:
        documents: Market state documents with a ``normalized`` dict.
        feature_columns: Optional fixed column order (for incremental encoding).

    Returns:
        tuple[pd.DataFrame, list[str]]: Feature matrix (rows=dates) and column names.
    """
    rows: list[dict[str, float]] = []
    dates: list[str] = []
    needs_backfill: list[str] = []

    for doc in documents:
        zscore_row = _zscore_row_from_doc(doc)
        date_str = str(doc["date"])
        if zscore_row:
            rows.append(zscore_row)
            dates.append(date_str)
        elif doc.get("raw"):
            needs_backfill.append(date_str)

    if needs_backfill:
        backfill_normalized_zscores(needs_backfill)
        for date_str in needs_backfill:
            refreshed = db["market_states"].find_one({"date": date_str}) if db is not None else None
            if refreshed:
                zscore_row = _zscore_row_from_doc(refreshed)
                if zscore_row:
                    rows.append(zscore_row)
                    dates.append(date_str)
                else:
                    # Warm-up period: rolling z-scores are undefined — use zeros
                    norm = refreshed.get("normalized") or {}
                    zscore_keys = [k for k in norm if k.endswith("_zscore")]
                    if zscore_keys:
                        rows.append({k: 0.0 for k in zscore_keys})
                        dates.append(date_str)
                    elif feature_columns:
                        rows.append({k: 0.0 for k in feature_columns})
                        dates.append(date_str)

    if not rows:
        raise ValueError(
            "No z-score columns found in market_states documents. "
            "Run Day 1 macro ingestion (run_day1.py) first."
        )

    df = pd.DataFrame(rows, index=dates)
    df = df.sort_index()
    cols = feature_columns or sorted(df.columns.tolist())
    for col in cols:
        if col not in df.columns:
            df[col] = 0.0
    df = df[cols]
    return df, cols


def load_all_documents_for_fit() -> list[dict[str, Any]]:
    """
    Load historical market_states used to fit PCA (excludes date=\"today\").

    Returns:
        list[dict]: All non-today market state documents sorted by date.
    """
    if db is None:
        raise RuntimeError("MongoDB is not connected. Set MONGO_URI in .env.")
    return list(
        db["market_states"]
        .find({"date": {"$ne": "today"}})
        .sort("date", 1)
    )


def load_pca_artifact() -> Optional[dict[str, Any]]:
    """
    Load a saved PCA artifact if present.

    Returns:
        Optional[dict]: Artifact with pca, feature_columns, component_stds; or None.
    """
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def clean_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows with >20% NaN and fill remaining NaN with zero.

    Args:
        df: Raw z-score feature matrix.

    Returns:
        pd.DataFrame: Cleaned matrix ready for PCA.
    """
    nan_frac = df.isna().mean(axis=1)
    cleaned = df.loc[nan_frac <= NAN_ROW_THRESHOLD].copy()
    dropped = len(df) - len(cleaned)
    if dropped:
        print(f"  Dropped {dropped} rows with >{NAN_ROW_THRESHOLD:.0%} NaN")
    return cleaned.fillna(0.0)


def assign_regime_label(
    components: np.ndarray,
    component_stds: np.ndarray,
) -> str:
    """
    Assign a regime label from PCA component loadings.

    Args:
        components: 1-D array of PCA component values for one day.
        component_stds: Standard deviation of each component across history.

    Returns:
        str: One of Risk-off stress, Rate shock, Risk-on rally, Neutral regime.
    """
    threshold = REGIME_STD_MULTIPLIER
    c0 = components[0]
    c1 = components[1] if len(components) > 1 else 0.0
    std0 = component_stds[0] if component_stds[0] > 0 else 1.0
    std1 = component_stds[1] if len(component_stds) > 1 and component_stds[1] > 0 else 1.0

    if c0 > threshold * std0:
        return "Risk-off stress"
    if c1 > threshold * std1:
        return "Rate shock"
    if c0 < -threshold * std0:
        return "Risk-on rally"
    return "Neutral regime"


def _encode_documents(
    docs: list[dict[str, Any]],
    pca: PCA,
    feature_columns: list[str],
    component_stds: np.ndarray,
) -> int:
    """
    Transform and persist PCA vectors for a list of documents.

    Args:
        docs: Documents to encode (re-fetched after z-score backfill).
        pca: Fitted sklearn PCA model.
        feature_columns: Ordered z-score column names.
        component_stds: Per-component std devs for regime labeling.

    Returns:
        int: Number of documents updated in MongoDB.
    """
    if not docs:
        return 0

    matrix, _ = build_zscore_matrix(docs, feature_columns=feature_columns)
    matrix = clean_feature_matrix(matrix)
    transformed = pca.transform(matrix.values)

    collection = db["market_states"]
    encoded = 0
    for i, date_str in enumerate(matrix.index):
        vector = transformed[i]
        regime = assign_regime_label(vector, component_stds)
        collection.update_one(
            {"date": date_str},
            {
                "$set": {
                    "market_vector": _vector_to_list(vector),
                    "regime_label": regime,
                }
            },
        )
        encoded += 1
        if encoded % 100 == 0:
            print(f"  Encoded {encoded} documents...")

    return encoded


def fit_and_encode(
    documents: Optional[list[dict[str, Any]]] = None,
) -> dict[str, int]:
    """
    Fit PCA, save the model, and update all unencoded market_states in MongoDB.

    Uses incremental mode when a saved model exists and only a subset of dates
    lack ``market_vector``. Fits on full history when no model is present.

    Args:
        documents: Optional pre-loaded documents; fetched from MongoDB if omitted.

    Returns:
        dict[str, int]: Stats with keys ``encoded``, ``skipped``, ``model_saved``.
    """
    if db is None:
        raise RuntimeError("MongoDB is not connected. Set MONGO_URI in .env.")

    print("[FINGERPRINT] Loading market_states without market_vector...")
    pending = documents if documents is not None else load_market_states_without_vector()
    if not pending:
        print("  No documents to encode (all vectors present).")
        return {"encoded": 0, "skipped": 0, "model_saved": 0}

    print(f"  Found {len(pending)} documents to encode")
    artifact = load_pca_artifact()

    if artifact is not None:
        print("  Using saved PCA model (incremental encode)")
        pca = artifact["pca"]
        feature_columns: list[str] = artifact["feature_columns"]
        component_stds: np.ndarray = artifact["component_stds"]
        encoded = _encode_documents(pending, pca, feature_columns, component_stds)
        print(f"[FINGERPRINT] Encoded {encoded} documents (incremental).")
        return {"encoded": encoded, "skipped": len(pending) - encoded, "model_saved": 0}

    print("  No saved model — fitting PCA on full history")
    all_docs = load_all_documents_for_fit()
    matrix, feature_columns = build_zscore_matrix(all_docs)
    matrix = clean_feature_matrix(matrix)

    print(f"  Fitting PCA with n_components={N_COMPONENTS} on {len(matrix)} rows...")
    pca = PCA(n_components=N_COMPONENTS)
    transformed = pca.fit_transform(matrix.values)
    component_stds = np.std(transformed, axis=0)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pca": pca,
            "feature_columns": feature_columns,
            "component_stds": component_stds,
        },
        MODEL_PATH,
    )
    print(f"  Saved PCA model -> {MODEL_PATH}")

    pending_dates = {str(d["date"]) for d in pending}
    to_write = [d for d in all_docs if str(d["date"]) in pending_dates]
    encoded = _encode_documents(to_write, pca, feature_columns, component_stds)
    print(f"[FINGERPRINT] Encoded {encoded} documents.")
    return {"encoded": encoded, "skipped": len(pending) - encoded, "model_saved": 1}


def main() -> None:
    """CLI entry point for PCA encoding."""
    print("=" * 60)
    print("Quant — Day 2 PCA Fingerprint Encoder")
    print("=" * 60)
    stats = fit_and_encode()
    print(f"\nDone. Encoded: {stats['encoded']} | Model saved: {stats['model_saved']}")


if __name__ == "__main__":
    main()
