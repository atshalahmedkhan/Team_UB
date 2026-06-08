#!/usr/bin/env python3
"""
Quant analysis orchestrator — runs all 6 Gemini agents for a ticker.

Usage:
    python scripts/run_analysis.py AAPL
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from quant.pipeline import check_prerequisites, run_full_analysis, save_report  # noqa: E402


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run Quant 6-agent analysis pipeline")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    args = parser.parse_args()

    symbol = args.ticker.upper()
    print("=" * 60)
    print(f"Quant — 6-Agent Analysis: {symbol}")
    print("=" * 60)

    issues = check_prerequisites(symbol)
    if issues:
        print("\nCannot run analysis — fix these first:\n")
        for issue in issues:
            print(f"  • {issue}")
        sys.exit(1)

    start = time.perf_counter()
    report, timings = run_full_analysis(symbol)
    elapsed = time.perf_counter() - start

    print("\n--- Agent timings ---")
    for name, sec in timings.items():
        print(f"  {name}: {sec:.1f}s")

    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

    out_path = save_report(symbol, report)
    print(
        f"\nAnalysis complete in {elapsed:.0f}s. "
        f"Report saved to {out_path}"
    )


if __name__ == "__main__":
    main()
