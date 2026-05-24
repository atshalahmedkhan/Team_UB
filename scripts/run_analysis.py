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
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from quant.agents.gemini_agents import (  # noqa: E402
    run_analog_search_agent,
    run_extraction_agent,
    run_fingerprint_agent,
    run_narrative_drift_agent,
    run_quant_model_agent,
    run_synthesis_agent,
)

REPORTS_DIR = ROOT / "quant" / "reports"


def run_full_analysis(ticker: str) -> str:
    """
    Execute all six agents in sequence and return the final report.

    Args:
        ticker: Stock symbol (e.g. ``AAPL``).

    Returns:
        str: Four-section markdown report.
    """
    symbol = ticker.upper().strip()
    timings: dict[str, float] = {}

    t0 = time.perf_counter()
    extracted = run_extraction_agent(symbol)
    timings["Agent 1 — Extraction"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    quant_model = run_quant_model_agent(symbol, extracted)
    timings["Agent 2 — Quant model"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    narrative_drift = run_narrative_drift_agent(symbol)
    timings["Agent 3 — Narrative drift"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    fingerprint = run_fingerprint_agent()
    timings["Agent 4 — Market fingerprint"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    analog_result = run_analog_search_agent(fingerprint["vector"], k=10)
    timings["Agent 5 — Analog search"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    report = run_synthesis_agent(
        symbol,
        extracted,
        quant_model,
        narrative_drift,
        fingerprint,
        analog_result,
    )
    timings["Agent 6 — Synthesis"] = time.perf_counter() - t0

    print("\n--- Agent timings ---")
    for name, elapsed in timings.items():
        print(f"  {name}: {elapsed:.1f}s")

    return report


def save_report(ticker: str, report: str) -> Path:
    """
    Write the analysis report to reports/{ticker}_{date}.txt.

    Args:
        ticker: Stock symbol.
        report: Report markdown text.

    Returns:
        Path: Saved file path.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = REPORTS_DIR / f"{ticker.upper()}_{date_str}.txt"
    path.write_text(report, encoding="utf-8")
    return path


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run Quant 6-agent analysis pipeline")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    args = parser.parse_args()

    print("=" * 60)
    print(f"Quant — 6-Agent Analysis: {args.ticker.upper()}")
    print("=" * 60)

    start = time.perf_counter()
    report = run_full_analysis(args.ticker)
    elapsed = time.perf_counter() - start

    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

    out_path = save_report(args.ticker, report)
    print(
        f"\nAnalysis complete in {elapsed:.0f}s. "
        f"Report saved to {out_path}"
    )


if __name__ == "__main__":
    main()
