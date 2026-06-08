#!/usr/bin/env python3
"""
Quant Day 1 runner — EDGAR + macro ingestion pipelines.

Usage:
    cp .env.example .env   # set MONGO_URI and FRED_API_KEY
    python scripts/run_day1.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure repository root is on sys.path when run as a script.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

DEFAULT_TICKERS = ["AAPL", "NVDA", "MSFT", "META", "GOOGL"]


def main() -> None:
    """Run EDGAR and macro pipelines with summary statistics."""
    print("=" * 60)
    print("Quant — Day 1 Data Ingestion")
    print("=" * 60)

    from quant.pipelines.edgar_ingest import ingest_multiple
    from quant.pipelines.macro_ingestion import (
        MISSING_SERIES_WARNINGS,
        build_macro_dataframe,
        compute_future_returns,
        normalize_dataframe,
        store_to_mongo,
    )
    from quant.storage.mongo_client import db, get_client

    get_client()
    if db is None:
        print("ERROR: MongoDB not configured. Set MONGO_URI in .env")
        sys.exit(1)

    # --- EDGAR ---
    print("\n--- EDGAR Filing Ingestion ---")
    filings_before = db["filings"].count_documents({})
    ingest_multiple(DEFAULT_TICKERS)
    filings_after = db["filings"].count_documents({})
    filings_stored = filings_after - filings_before
    print(f"\nFilings in MongoDB: {filings_after} (+{filings_stored} new this run)")

    # --- Macro ---
    print("\n--- Macro Market State Ingestion ---")
    raw_df = build_macro_dataframe()
    raw_df = compute_future_returns(raw_df)
    norm_df = normalize_dataframe(raw_df)
    store_to_mongo(raw_df, norm_df)

    market_col = db["market_states"]
    total_states = market_col.count_documents({})
    earliest = market_col.find_one(sort=[("date", 1)])
    latest = market_col.find_one(sort=[("date", -1)])

    # --- Summary ---
    print("\n" + "=" * 60)
    print("Day 1 Summary")
    print("=" * 60)
    print(f"Filings stored (this run):     {filings_stored}")
    print(f"Filings total in MongoDB:      {filings_after}")
    print(f"Market state documents:        {total_states}")

    if earliest and latest:
        print(
            f"Market state date range:       {earliest['date']} -> {latest['date']}"
        )
    else:
        print("Market state date range:       (no documents)")

    if MISSING_SERIES_WARNINGS:
        print("\nMissing / skipped data series:")
        for warning in MISSING_SERIES_WARNINGS:
            print(f"  - {warning}")
    else:
        print("\nMissing data series:           none")

    print("\nDay 1 complete.")


if __name__ == "__main__":
    main()
