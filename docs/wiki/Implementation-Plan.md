# Implementation Plan

> Canonical copy also lives at [`docs/IMPLEMENTATION_PLAN.md`](https://github.com/atshalahmedkhan/Team_UB/blob/main/docs/IMPLEMENTATION_PLAN.md) for PR review alongside code.

## Success criteria (MVP)

| Criterion | Definition of done |
|-----------|-------------------|
| Multi-step agent | Ticker in → plan → tools → structured report out (< 5 min) |
| Beyond chat | Live EDGAR pull, Python sandbox math, Elastic kNN, MongoDB history |
| Partner MCP | Meaningful Elastic + MongoDB integration (not mock-only) |
| Human oversight | Streamlit shows agent logs; grader rejection loop visible in demo |
| Open source | Public repo, MIT `LICENSE`, reproducible `requirements.txt` |

## Phase 1 — Data pipelines (Day 1)

- SEC EDGAR pull by ticker (`quant/pipelines/edgar_ingest.py`)
- FRED + yfinance macro pull (`macro_ingestion.py`)
- MongoDB schemas + bootstrap script
- Z-score / percentile normalization

**Exit:** Query filings and `market_days` for any date.

## Phase 2 — Vector layer (Day 2)

- Feature matrix (~55 dims) → PCA → 15-dim vector
- Forward returns 30/60/90d on each historical day
- Elastic `market_state_v1` index + kNN
- Agent 5 CLI returns sensible analogs (sanity: Dec 2018 in high-vol hiking)

**Exit:** kNN returns top analogs with outcome stats.

## Phase 3 — Micro agents (Day 3)

- Agents 1–3 in Agent Builder
- Agent 2 Cloud Run sandbox with self-correction
- Agent 6 grader rejection loop

**Exit:** Micro path for one ticker; injected calc error caught.

## Phase 4 — Macro + synthesis (Day 3–4)

- Agents 4–5 parallel to micro
- Agent 6 fuses layers into four-section report JSON

## Phase 5 — Demo polish (Day 4)

- Streamlit dashboard, footnotes, demo error injection
- Devpost video + submission

## Risk register

| Risk | Mitigation |
|------|------------|
| EDGAR rate limits | MongoDB cache + backup filing for demo |
| MCP latency | Pre-warm; pre-index Elastic |
| Hallucinated citations | Agent 6 verifies against Agent 1 JSON |

Full detail: [IMPLEMENTATION_PLAN.md on GitHub](https://github.com/atshalahmedkhan/Team_UB/blob/main/docs/IMPLEMENTATION_PLAN.md)
