"""
SEC EDGAR earnings filing ingestion pipeline.

Fetches the most recent 10-Q (or 10-K fallback) for a ticker and stores
raw filing text in MongoDB.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import requests
from bson import ObjectId
from pymongo.collection import Collection

from quant.storage.mongo_client import db

SEC_USER_AGENT = "Quant-Hackathon team@quant.ai"
SEC_HEADERS = {
    "User-Agent": SEC_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
}
SEC_RATE_LIMIT_SEC = 0.5
MAX_RAW_TEXT_CHARS = 500_000
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EFTS_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"


def _sec_get(url: str, **kwargs: Any) -> requests.Response:
    """
    Perform a rate-limited GET request to SEC endpoints.

    Args:
        url: Request URL.
        **kwargs: Additional arguments passed to ``requests.get``.

    Returns:
        requests.Response: HTTP response.

    Raises:
        requests.RequestException: On network or HTTP errors.
    """
    time.sleep(SEC_RATE_LIMIT_SEC)
    response = requests.get(url, headers=SEC_HEADERS, timeout=60, **kwargs)
    response.raise_for_status()
    return response


def _filings_collection() -> Collection:
    """Return the MongoDB ``filings`` collection."""
    if db is None:
        raise RuntimeError("MongoDB is not connected. Set MONGO_URI in .env.")
    return db["filings"]


def get_cik(ticker: str) -> str:
    """
    Resolve a stock ticker to a zero-padded 10-digit SEC CIK.

    Args:
        ticker: Stock symbol (e.g. ``"AAPL"``).

    Returns:
        str: CIK formatted as 10 digits with leading zeros.

    Raises:
        ValueError: If the ticker is not found in SEC company tickers.
        requests.RequestException: On network failures.
    """
    symbol = ticker.upper().strip()
    response = _sec_get(COMPANY_TICKERS_URL)
    data = response.json()

    for entry in data.values():
        if str(entry.get("ticker", "")).upper() == symbol:
            return str(entry["cik_str"]).zfill(10)

    raise ValueError(f"Ticker '{ticker}' not found in SEC company tickers.")


def _format_accession(accession: str) -> tuple[str, str]:
    """
    Normalize accession number to dashed and clean forms.

    Args:
        accession: Accession with or without dashes.

    Returns:
        tuple[str, str]: (dashed accession, clean accession without dashes).
    """
    clean = accession.replace("-", "").strip()
    if len(clean) != 18:
        return accession, clean
    dashed = f"{clean[:10]}-{clean[10:12]}-{clean[12:]}"
    return dashed, clean


def _pick_latest_filing(submissions: dict[str, Any]) -> dict[str, str]:
    """
    Select the most recent 10-Q, falling back to 10-K.

    Args:
        submissions: Parsed SEC submissions JSON for a CIK.

    Returns:
        dict: Keys ``form``, ``filing_date``, ``accession``, ``accession_clean``,
        ``primary_document``.

    Raises:
        ValueError: If no 10-Q or 10-K filing is found.
    """
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    candidates: list[tuple[str, str, str, str]] = []
    for form, filing_date, accession, primary in zip(forms, dates, accessions, primary_docs):
        if form in ("10-Q", "10-K"):
            candidates.append((filing_date, form, accession, primary))

    if not candidates:
        raise ValueError("No 10-Q or 10-K filings found for this CIK.")

    candidates.sort(key=lambda row: row[0], reverse=True)

    for preferred in ("10-Q", "10-K"):
        for filing_date, form, accession, primary in candidates:
            if form == preferred:
                dashed, clean = _format_accession(accession)
                return {
                    "form": form,
                    "filing_date": filing_date,
                    "accession": dashed,
                    "accession_clean": clean,
                    "primary_document": primary,
                }

    raise ValueError("No 10-Q or 10-K filings found for this CIK.")


def _fetch_filing_text(
    cik: str,
    accession_clean: str,
    primary_document: str,
    accession_dashed: str,
) -> str:
    """
    Pull primary filing document text via SEC Archives and EFTS fallback.

    Args:
        cik: Zero-padded 10-digit CIK.
        accession_clean: Accession without dashes.
        primary_document: Primary document filename from submissions.
        accession_dashed: Accession with dashes (for EFTS query).

    Returns:
        str: Filing text (HTML stripped when possible).

    Raises:
        requests.RequestException: If all fetch strategies fail.
        ValueError: If no document content could be retrieved.
    """
    cik_numeric = str(int(cik))
    archives_url = (
        f"https://www.sec.gov/Archives/edgar/data/{cik_numeric}/"
        f"{accession_clean}/{primary_document}"
    )

    try:
        response = _sec_get(archives_url)
        text = response.text
        if text.strip():
            return _strip_html(text)
    except requests.RequestException as archives_err:
        print(f"  Warning: Archives fetch failed ({archives_err}), trying EFTS...")

    # EFTS full-text search API fallback
    time.sleep(SEC_RATE_LIMIT_SEC)
    efts_params = {"q": f'accession_no:"{accession_dashed}"', "dateRange": "custom"}
    efts_response = requests.get(
        EFTS_SEARCH_URL,
        headers=SEC_HEADERS,
        params=efts_params,
        timeout=60,
    )
    efts_response.raise_for_status()
    hits = efts_response.json().get("hits", {}).get("hits", [])
    if hits:
        source = hits[0].get("_source", {})
        for key in ("file_description", "display_names", "period_ending"):
            pass
        # EFTS index does not return full body; retry archives index.htm
        index_url = (
            f"https://www.sec.gov/Archives/edgar/data/{cik_numeric}/"
            f"{accession_clean}/{accession_clean}-index.htm"
        )
        index_resp = _sec_get(index_url)
        doc_match = re.search(
            r'href="([^"]+' + re.escape(primary_document) + r')"', index_resp.text, re.I
        )
        if doc_match:
            retry_url = (
                f"https://www.sec.gov/Archives/edgar/data/{cik_numeric}/"
                f"{accession_clean}/{doc_match.group(1).split('/')[-1]}"
            )
            retry_resp = _sec_get(retry_url)
            return _strip_html(retry_resp.text)

    raise ValueError(
        f"Could not retrieve filing text for accession {accession_dashed}."
    )


def _strip_html(html: str) -> str:
    """
    Remove HTML tags and collapse whitespace.

    Args:
        html: Raw HTML or text content.

    Returns:
        str: Plain text suitable for storage.
    """
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def ingest_ticker(ticker: str) -> ObjectId:
    """
    Ingest the latest 10-Q/10-K filing for a ticker into MongoDB.

    Args:
        ticker: Stock symbol (e.g. ``"AAPL"``).

    Returns:
        ObjectId: MongoDB document ``_id`` (existing or newly inserted).

    Raises:
        ValueError: If ticker/CIK/filing cannot be resolved.
        requests.RequestException: On SEC network errors.
    """
    symbol = ticker.upper().strip()
    print(f"[EDGAR] Ingesting {symbol}...")

    cik = get_cik(symbol)
    print(f"  CIK: {cik}")

    submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    submissions_resp = _sec_get(submissions_url)
    filing = _pick_latest_filing(submissions_resp.json())

    print(
        f"  Form: {filing['form']} | Date: {filing['filing_date']} | "
        f"Accession: {filing['accession']}"
    )

    collection = _filings_collection()
    existing = collection.find_one({"accession": filing["accession"]})
    if existing:
        print(f"  Skipping — accession {filing['accession']} already stored.")
        return existing["_id"]

    raw_text = _fetch_filing_text(
        cik,
        filing["accession_clean"],
        filing["primary_document"],
        filing["accession"],
    )
    raw_text = raw_text[:MAX_RAW_TEXT_CHARS]
    word_count = len(raw_text.split())

    document = {
        "ticker": symbol,
        "cik": cik,
        "form": filing["form"],
        "filing_date": filing["filing_date"],
        "accession": filing["accession"],
        "accession_clean": filing["accession_clean"],
        "raw_text": raw_text,
        "word_count": word_count,
        "ingested_at": datetime.now(timezone.utc),
        "status": "raw",
    }

    result = collection.insert_one(document)
    print(f"  Stored filing ({word_count:,} words) -> _id={result.inserted_id}")
    return result.inserted_id


def ingest_multiple(tickers: list[str]) -> dict[str, ObjectId]:
    """
    Ingest filings for multiple tickers.

    Args:
        tickers: List of stock symbols.

    Returns:
        dict[str, ObjectId]: Mapping of uppercase ticker to MongoDB ``_id``.
    """
    results: dict[str, ObjectId] = {}
    for ticker in tickers:
        try:
            results[ticker.upper()] = ingest_ticker(ticker)
        except (ValueError, requests.RequestException) as exc:
            print(f"[EDGAR] Failed for {ticker}: {exc}")
    return results
