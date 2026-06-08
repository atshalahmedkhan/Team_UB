"""
Tests for SEC EDGAR filing ingestion pipeline.
"""

from __future__ import annotations

from datetime import datetime
from bson import ObjectId

from quant.pipelines.edgar_ingest import get_cik, ingest_ticker

REQUIRED_FIELDS = {
    "ticker",
    "cik",
    "form",
    "filing_date",
    "accession",
    "accession_clean",
    "raw_text",
    "word_count",
    "ingested_at",
    "status",
}


def test_get_cik() -> None:
    """AAPL should resolve to CIK 0000320193."""
    assert get_cik("AAPL") == "0000320193"


def test_ingest_returns_id(requires_mongo) -> None:
    """ingest_ticker should return a MongoDB ObjectId."""
    doc_id = ingest_ticker("AAPL")
    assert isinstance(doc_id, ObjectId)


def test_idempotent(requires_mongo) -> None:
    """Running ingest twice should not duplicate filings."""
    db = requires_mongo
    first_id = ingest_ticker("AAPL")
    count_after_first = db["filings"].count_documents({"ticker": "AAPL"})
    second_id = ingest_ticker("AAPL")
    count_after_second = db["filings"].count_documents({"ticker": "AAPL"})
    assert first_id == second_id
    assert count_after_first == count_after_second


def test_schema(requires_mongo) -> None:
    """Stored filing documents must include all required fields."""
    doc_id = ingest_ticker("AAPL")
    doc = requires_mongo["filings"].find_one({"_id": doc_id})
    assert doc is not None
    assert REQUIRED_FIELDS.issubset(doc.keys())
    assert doc["ticker"] == "AAPL"
    assert doc["cik"] == "0000320193"
    assert doc["form"] in ("10-Q", "10-K")
    assert doc["status"] == "raw"
    assert isinstance(doc["word_count"], int)
    assert isinstance(doc["ingested_at"], datetime)
    assert len(doc["raw_text"]) > 0
