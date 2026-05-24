"""MongoDB collection names and index definitions."""

COLLECTION_FILINGS = "filings"
COLLECTION_TRANSCRIPTS = "transcripts"
COLLECTION_MARKET_DAYS = "market_days"
COLLECTION_REPORTS = "reports"

INDEXES = {
    COLLECTION_FILINGS: [("ticker", 1), ("filed_at", -1)],
    COLLECTION_MARKET_DAYS: [("date", 1)],
}
