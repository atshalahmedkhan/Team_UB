#!/usr/bin/env python3
"""
Validate Quant environment and data prerequisites.

Usage:
    python scripts/check_setup.py
    python scripts/check_setup.py --ticker AAPL
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


def _status(ok: bool, label: str, detail: str = "") -> None:
    mark = "OK" if ok else "FAIL"
    line = f"[{mark}] {label}"
    if detail:
        line += f" — {detail}"
    print(line)


def _check_gemini() -> None:
    import os

    from quant.agents.gemini_agents import (
        _get_client,
        get_auth_mode,
        get_gcp_location,
        get_gcp_project,
        get_gemini_model,
        use_vertexai,
        validate_gemini_auth,
    )

    mode = get_auth_mode()
    if use_vertexai():
        try:
            project = get_gcp_project()
            location = get_gcp_location()
            _status(True, "Gemini auth", f"Vertex AI (project={project}, location={location})")
            validate_gemini_auth()
            _status(True, "Application Default Credentials")
        except RuntimeError as exc:
            _status(False, "Gemini auth (Vertex AI)", str(exc)[:300])
            return
    else:
        try:
            from quant.agents.gemini_agents import _get_api_key

            key = _get_api_key()
            key_name = "GOOGLE_API_KEY"
            if not os.getenv("GOOGLE_API_KEY"):
                key_name = (
                    "GEMINI_API_KEY"
                    if os.getenv("GEMINI_API_KEY")
                    else "GEMINI_AGENTIC_PLATFORM_API_KEY"
                )
            _status(True, f"Gemini auth (AI Studio key: {key_name})", f"{len(key)} chars")
        except RuntimeError as exc:
            _status(False, "Gemini auth (AI Studio)", str(exc)[:300])
            return

    try:
        client = _get_client()
        model = get_gemini_model()
        resp = client.models.generate_content(
            model=model,
            contents="Reply with exactly: ok",
        )
        text = (resp.text or "").strip()
        _status(
            text.lower().startswith("ok"),
            f"Gemini API call ({mode}, model={model})",
            text[:40],
        )
    except Exception as exc:
        detail = str(exc)[:300]
        if "ascii" in detail.lower() and mode == "aistudio":
            detail += " (re-copy GOOGLE_API_KEY from AI Studio; key must be ASCII only)"
        _status(False, "Gemini API call", detail)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Quant setup")
    parser.add_argument("--ticker", default="AAPL", help="Ticker to verify filings for")
    args = parser.parse_args()
    ticker = args.ticker.upper()

    print("=" * 60)
    print("Quant — Setup Check")
    print("=" * 60)

    import os

    from quant.pipeline import MODEL_PATH, check_prerequisites

    _check_gemini()

    # MongoDB
    from quant.storage.mongo_client import db, get_client, refresh_db

    try:
        get_client()
        refresh_db()
        active_db = db
        _status(True, "MongoDB connection")
        if active_db is not None:
            try:
                filings = active_db["filings"].count_documents({"ticker": ticker})
                states = active_db["market_states"].count_documents(
                    {"market_vector": {"$ne": None}, "date": {"$nin": ["today", None]}}
                )
                _status(filings > 0, f"Filings for {ticker}", f"{filings} documents")
                _status(states > 0, "Market state vectors", f"{states} documents")
            except Exception as exc:
                _status(False, "MongoDB queries", str(exc)[:200])
    except RuntimeError as exc:
        _status(False, "MongoDB connection", str(exc)[:200])

    # Optional services
    _status(bool(os.getenv("FRED_API_KEY")), "FRED_API_KEY (macro ingest)")
    elastic_ok = bool(os.getenv("ELASTIC_URL") and os.getenv("ELASTIC_API_KEY"))
    _status(elastic_ok, "Elastic (optional — Mongo fallback used if missing)")

    _status(MODEL_PATH.exists(), "PCA model", str(MODEL_PATH))

    print("\n--- Pipeline readiness ---")
    issues = check_prerequisites(ticker)
    if issues:
        for issue in issues:
            print(f"  • {issue}")
        sys.exit(1)

    print(f"  Ready to run: python scripts/run_analysis.py {ticker}")
    sys.exit(0)


if __name__ == "__main__":
    main()
