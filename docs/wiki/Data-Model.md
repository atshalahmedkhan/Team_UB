# Data Model

Storage split: **MongoDB** for documents and rich context; **Elastic** for vector similarity search.

## MongoDB collections

### `filings`

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `ticker` | string | e.g. AAPL |
| `cik` | string | zero-padded CIK |
| `form` | string | 10-Q, 10-K |
| `filed_at` | date | SEC filed date |
| `accession` | string | EDGAR accession |
| `raw_html` | string | Optional; large |
| `structured` | object | Agent 1 output |
| `created_at` | datetime | |

**Index:** `{ ticker: 1, filed_at: -1 }`

### `transcripts`

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | |
| `quarter` | string | e.g. 2025-Q1 |
| `text` | string | Full transcript |
| `embedding_id` | string | Optional reference |
| `created_at` | datetime | |

### `market_days`

One document per trading day (historical library).

| Field | Type | Description |
|-------|------|-------------|
| `date` | date | Trading date |
| `features_raw` | object | ~55 normalized features |
| `vector` | array[15] | PCA output |
| `regime_label` | string | Human summary |
| `returns` | object | `{ d30, d60, d90 }` SPX or benchmark |
| `metadata` | object | Top feature contributors |

**Index:** `{ date: 1 }` unique

### `reports`

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | |
| `run_id` | string | Orchestration id |
| `report` | object | Final JSON schema |
| `agent_runs` | array | Logs for dashboard |
| `created_at` | datetime | |

## Elastic index: `market_state_v1`

```json
{
  "mappings": {
    "properties": {
      "date": { "type": "date" },
      "ticker_benchmark": { "type": "keyword" },
      "regime_label": { "type": "text" },
      "vector": {
        "type": "dense_vector",
        "dims": 15,
        "index": true,
        "similarity": "cosine"
      }
    }
  }
}
```

**kNN query (conceptual):**

```json
{
  "knn": {
    "field": "vector",
    "query_vector": [/* 15 floats */],
    "k": 10,
    "num_candidates": 100
  }
}
```

MongoDB stores outcome narratives; Elastic returns similar **dates** only.

## Pydantic schemas

Canonical types in `quant/schemas/`:

- `extraction.py` — `ExtractionResult`, `LineItem`
- `model.py` — `ModelResult`, `MetricVerdict`
- `narrative.py` — `NarrativeFlag`
- `macro.py` — `MarketFingerprint`, `Analog`, `AnalogSet`
- `report.py` — `FinalReport`

Agents should only exchange validated schema instances (JSON serializable).

## Data retention (hackathon)

| Dataset | Retention |
|---------|-----------|
| Macro history | 2015–present (~2,500 days) |
| Filings demo | 2–3 tickers × 4 quarters |
| Reports | Last 30 runs |

## Bootstrap order

1. `macro_ingestion` → `market_days`
2. `pca_encoder` fit → backfill `vector`
3. `elastic_index.bulk_load` from `market_days`
4. `edgar_ingest` for demo tickers (AAPL, NVDA)
