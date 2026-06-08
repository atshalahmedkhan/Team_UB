"""Shared analysis pipeline — used by CLI, dashboard, and API entry points."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from quant.agents.gemini_agents import (
    run_analog_search_agent,
    run_extraction_agent,
    run_fingerprint_agent,
    run_narrative_drift_agent,
    run_quant_model_agent,
    run_synthesis_agent,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "quant" / "reports"
MODEL_PATH = REPO_ROOT / "quant" / "models" / "pca_model.pkl"

ProgressCallback = Callable[[str, str, Optional[float]], None]


def check_prerequisites(ticker: str) -> list[str]:
    """
    Return a list of blocking issues that must be resolved before analysis.

    Args:
        ticker: Stock symbol to analyze.

    Returns:
        list[str]: Human-readable error messages; empty when ready.
    """
    from quant.agents.gemini_agents import validate_gemini_auth
    from quant.storage.mongo_client import db, get_client, refresh_db

    issues: list[str] = []

    try:
        validate_gemini_auth()
    except RuntimeError as exc:
        issues.append(str(exc))

    active_db = db
    if active_db is None:
        try:
            get_client()
            active_db = refresh_db()
        except RuntimeError as exc:
            issues.append(str(exc))

    if active_db is not None:
        try:
            filings = active_db["filings"].count_documents({"ticker": ticker.upper()})
            if filings == 0:
                issues.append(
                    f"No SEC filings for {ticker.upper()} in MongoDB. "
                    "Run: python scripts/bootstrap_historical.py --tickers "
                    f"{ticker.upper()}"
                )

            states = active_db["market_states"].count_documents(
                {"market_vector": {"$ne": None}, "date": {"$nin": ["today", None]}}
            )
            if states == 0:
                issues.append(
                    "No market_state vectors in MongoDB. "
                    "Run: python scripts/bootstrap_historical.py && "
                    "python -m quant.agents.fingerprint_agent"
                )
        except Exception as exc:
            issues.append(f"MongoDB query failed: {exc}")

    if not MODEL_PATH.exists():
        issues.append(
            f"PCA model missing at {MODEL_PATH}. "
            "Run: python -m quant.agents.fingerprint_agent"
        )

    return issues


def _notify(
    on_progress: Optional[ProgressCallback],
    event: str,
    agent: str,
    elapsed: Optional[float] = None,
) -> None:
    if on_progress is not None:
        on_progress(event, agent, elapsed)


def run_full_analysis(
    ticker: str,
    on_progress: Optional[ProgressCallback] = None,
) -> tuple[str, dict[str, float]]:
    """
    Execute all six agents in sequence and return the final report.

    Args:
        ticker: Stock symbol (e.g. ``AAPL``).
        on_progress: Optional callback ``(event, agent_name, elapsed_sec)``.
            Events: ``agent_start``, ``agent_done``.

    Returns:
        tuple[str, dict[str, float]]: Markdown report and per-agent timings (seconds).
    """
    symbol = ticker.upper().strip()
    timings: dict[str, float] = {}

    agent_name = "Agent 1 — Extraction"
    _notify(on_progress, "agent_start", agent_name)
    t0 = time.perf_counter()
    extracted = run_extraction_agent(symbol)
    timings[agent_name] = time.perf_counter() - t0
    _notify(on_progress, "agent_done", agent_name, timings[agent_name])

    agent_name = "Agent 2 — Quant model"
    _notify(on_progress, "agent_start", agent_name)
    t0 = time.perf_counter()
    quant_model = run_quant_model_agent(symbol, extracted)
    timings[agent_name] = time.perf_counter() - t0
    _notify(on_progress, "agent_done", agent_name, timings[agent_name])

    agent_name = "Agent 3 — Narrative drift"
    _notify(on_progress, "agent_start", agent_name)
    t0 = time.perf_counter()
    narrative_drift = run_narrative_drift_agent(symbol)
    timings[agent_name] = time.perf_counter() - t0
    _notify(on_progress, "agent_done", agent_name, timings[agent_name])

    agent_name = "Agent 4 — Market fingerprint"
    _notify(on_progress, "agent_start", agent_name)
    t0 = time.perf_counter()
    fingerprint = run_fingerprint_agent()
    timings[agent_name] = time.perf_counter() - t0
    _notify(on_progress, "agent_done", agent_name, timings[agent_name])

    agent_name = "Agent 5 — Analog search"
    _notify(on_progress, "agent_start", agent_name)
    t0 = time.perf_counter()
    analog_result = run_analog_search_agent(fingerprint["vector"], k=10)
    timings[agent_name] = time.perf_counter() - t0
    _notify(on_progress, "agent_done", agent_name, timings[agent_name])

    agent_name = "Agent 6 — Synthesis"
    _notify(on_progress, "agent_start", agent_name)
    t0 = time.perf_counter()
    report = run_synthesis_agent(
        symbol,
        extracted,
        quant_model,
        narrative_drift,
        fingerprint,
        analog_result,
    )
    timings[agent_name] = time.perf_counter() - t0
    _notify(on_progress, "agent_done", agent_name, timings[agent_name])

    return report, timings


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
