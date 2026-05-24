# Quant — Implementation Plan

Phased plan to ship a judge-ready demo for the [Rapid Agent Hackathon](https://rapid-agent.devpost.com/). Detailed agent specs live in the [GitHub Wiki](../docs/wiki/Home.md).

## Success criteria (MVP)

| Criterion | Definition of done |
|-----------|-------------------|
| Multi-step agent | Ticker in → plan → tools → structured report out (< 5 min) |
| Beyond chat | Live EDGAR pull, Python sandbox math, Elastic kNN, MongoDB history |
| Partner MCP | Meaningful Elastic + MongoDB integration (not mock-only) |
| Human oversight | Streamlit shows agent logs; grader rejection loop visible in demo |
| Open source | Public repo, MIT `LICENSE`, reproducible `requirements.txt` |

## Phase 0 — Foundation (Day 0)

- [ ] GCP project: Agent Builder app, Gemini API, Cloud Run for sandbox
- [ ] Elastic Cloud deployment + MCP server configured in Agent Builder
- [ ] MongoDB Atlas + MCP server configured
- [ ] `.env.example` with all required keys documented
- [ ] CI: lint + `pytest tests/` on push (optional but recommended)

## Phase 1 — Data pipelines (Day 1)

**Goal:** Historical macro library + filing ingest without agents.

| Task | Owner module | Notes |
|------|--------------|-------|
| SEC EDGAR pull by ticker/CIK | `quant/pipelines/edgar_ingest.py` | User-Agent header required; rate-limit |
| FRED + yfinance macro pull | `quant/pipelines/macro_ingestion.py` | 25+ series; daily cron via Cloud Scheduler |
| Normalize z-score / percentile | `quant/pipelines/normalize.py` | Rolling 252d window |
| MongoDB schemas | `quant/storage/mongo_schema.py` | `filings`, `transcripts`, `market_days` |
| Bootstrap 2015–present | `scripts/bootstrap_historical.py` | One-time; store raw + normalized |

**Exit:** Query MongoDB for AAPL last filing; query `market_days` for any date.

## Phase 2 — Vector layer (Day 2)

**Goal:** Analog search returns sensible dates (e.g. Dec 2018 in high-vol hiking regimes).

| Task | Module | Notes |
|------|--------|-------|
| Feature matrix ~55 dims | `quant/pipelines/feature_builder.py` | Rates, vol, credit, cross-asset, breadth |
| PCA 55 → 15 | `quant/pipelines/pca_encoder.py` | Fit on train period; persist `sklearn` artifact |
| Forward returns 30/60/90d | `quant/pipelines/outcomes.py` | SPX or ticker-specific benchmark |
| Elastic dense_vector index | `quant/storage/elastic_index.py` | `market_state_v1`; k=10 kNN |
| Agent 5 retrieval API | `quant/agents/agent5_analog_search.py` | Top 5 analogs + outcome stats |

**Exit:** CLI: `python -m quant.agents.agent5_analog_search` prints top analogs for today.

## Phase 3 — Micro agents (Day 3)

**Goal:** Agents 1–3 + 6 grader loop in Agent Builder.

| Agent | Module | MCP / tools |
|-------|--------|-------------|
| 1 Extraction | `agent1_extraction.py` | EDGAR HTTP, MongoDB write |
| 2 Quant model | `agent2_quant_model.py` | Cloud Run Python exec |
| 3 Narrative drift | `agent3_narrative_drift.py` | MongoDB read prior quarter |
| 6 Grader | `agent6_grader.py` | Reject → Agent 2 retry; synthesis |

Wire orchestration in `quant/orchestration/agent_builder/` (prompts + tool definitions).

**Exit:** End-to-end micro path for one ticker; Agent 6 catches injected calc error.

## Phase 4 — Macro + synthesis (Day 3–4)

| Agent | Module | Parallel with |
|-------|--------|---------------|
| 4 Fingerprint | `agent4_fingerprint.py` | Agents 1–3 |
| 5 Analog search | `agent5_analog_search.py` | Agent 4 output |
| 6 Synthesis | `agent6_grader.py` | Fuse micro + macro narrative |

**Exit:** Four-section report JSON schema populated.

## Phase 5 — Demo polish (Day 4)

- [ ] `dashboard/app.py` — ticker input, live logs, report sections, footnote links
- [ ] `tests/test_grader_rejection.py` — deliberate Agent 2 error
- [ ] Demo script rehearsed (< 5 min) — see [Demo Guide](wiki/Demo-Guide.md)
- [ ] Devpost: video, repo URL, architecture diagram screenshot

## Report JSON schema (contract)

All agents write/read `quant/schemas/report.py` (Pydantic):

```json
{
  "ticker": "AAPL",
  "generated_at": "ISO-8601",
  "beats_misses": [{ "metric", "actual", "consensus", "verdict", "citation" }],
  "narrative_flags": [{ "materiality", "old_text", "new_text", "impact", "citation" }],
  "macro_context": { "regime_label", "vector_id", "analogs": [...] },
  "synthesis": { "micro_signal", "macro_signal", "combined_verdict", "risks": [...] },
  "audit": { "agent_runs": [...], "rejections": [...] }
}
```

## Risk register

| Risk | Mitigation |
|------|------------|
| EDGAR rate limits | Cache filings in MongoDB; demo uses pre-fetched backup |
| MCP latency | Warm connections; parallel macro path |
| PCA overfit | Hold out 2024 for sanity checks on analogs |
| Hallucinated citations | Agent 6 citation verification against Agent 1 JSON |
| Demo timeout | Pre-index Elastic; cap filing sections for hackathon |

## Milestone timeline

```
Day 1 ████████░░ Data pipelines + MongoDB
Day 2 ████████░░ Elastic kNN + historical vectors
Day 3 ████████░░ Agents 1–6 wired in Agent Builder
Day 4 ██████████ Streamlit demo + Devpost assets
```

## References

- [Hackathon requirements](wiki/Hackathon-Requirements.md)
- [Architecture](wiki/Architecture.md)
- [Agents](wiki/Agents.md)
