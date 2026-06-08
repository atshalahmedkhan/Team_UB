#!/usr/bin/env python3
"""Bootstrap historical data for Phase 1.

This script runs the macro ingestion pipeline, PCA fingerprint encoding,
and EDGAR filing ingest into MongoDB.

Usage:
    cp .env.example .env
    # edit .env to add MONGO_URI and optionally FRED_API_KEY
    python scripts/bootstrap_historical.py --tickers AAPL,NVDA

    # If macro data is already in MongoDB, encode vectors only:
    python scripts/bootstrap_historical.py --only-fingerprint
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from quant.agents.fingerprint_agent import fit_and_encode  # noqa: E402
from quant.pipelines.edgar_ingest import ingest_multiple  # noqa: E402
from quant.pipelines.macro_ingestion import run_macro_pipeline  # noqa: E402
from quant.storage.mongo_client import get_client  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bootstrap historical macro + filings")
    p.add_argument("--tickers", default="AAPL,NVDA,MSFT", help="Comma list of tickers to ingest")
    p.add_argument("--skip-edgar", action="store_true", help="Skip EDGAR ingestion")
    p.add_argument("--skip-macro", action="store_true", help="Skip macro ingestion")
    p.add_argument(
        "--skip-fingerprint",
        action="store_true",
        help="Skip PCA fingerprint encoding (market_vector)",
    )
    p.add_argument(
        "--only-fingerprint",
        action="store_true",
        help="Only run PCA fingerprint encoding (skip macro and EDGAR)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # If nothing to run, exit successfully (dry-run/test mode).
    if (
        args.skip_macro
        and args.skip_edgar
        and not args.only_fingerprint
    ):
        print("No pipelines requested (both --skip-macro and --skip-edgar provided). Exiting.")
        return

    # Ensure Mongo client is available when running any pipeline that needs it
    try:
        get_client()
    except Exception as exc:  # pragma: no cover - runtime environment
        print(f"ERROR: Could not connect to MongoDB: {exc}")
        sys.exit(1)

    run_fingerprint = (
        args.only_fingerprint
        or (not args.skip_fingerprint and not args.skip_macro)
    )

    if not args.skip_macro and not args.only_fingerprint:
        print("\n--- Running macro ingestion pipeline ---")
        stats = run_macro_pipeline()
        print(f"Macro pipeline completed: {stats}")

    if run_fingerprint:
        print("\n--- Running PCA fingerprint encoder ---")
        fp_stats = fit_and_encode()
        print(f"Fingerprint encoding completed: {fp_stats}")

    if not args.skip_edgar and not args.only_fingerprint:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        print("\n--- Running EDGAR ingestion for tickers: {} ---".format(",".join(tickers)))
        results = ingest_multiple(tickers)
        print(f"EDGAR ingestion results: {results}")

    print("\nBootstrap complete.")


if __name__ == "__main__":
    main()
