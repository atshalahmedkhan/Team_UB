# Tech Stack

## Core platform

| Component | Technology | Role |
|-----------|------------|------|
| Orchestration | Google Cloud Agent Builder | Multi-agent workflows, tool routing |
| LLM | Gemini | Reasoning, NLP, planning |
| Compute | Cloud Run | Isolated Python sandbox (Agent 2) |
| Scheduler | Cloud Scheduler | Daily macro ingestion |
| Secrets | GCP Secret Manager | API keys in production |

## Partner MCP

| Partner | Integration |
|---------|-------------|
| **Elastic** | `dense_vector` index `market_state_v1`; kNN in Agent 5 |
| **MongoDB** | Atlas cluster; filings, transcripts, `market_days`, reports |

Register both MCP servers in Agent Builder project settings. Agents invoke tools through the MCP protocol (not ad-hoc SDK calls in prompts).

## Data sources (free tier friendly)

| Source | Data | Used by |
|--------|------|---------|
| SEC EDGAR | 10-Q/10-K, submissions JSON | Agent 1 |
| FRED | Rates, credit spreads | Macro pipeline |
| yfinance | VIX, equities | Macro pipeline |
| Mock / CSV | Analyst consensus (hackathon) | Agent 2 |

## Application code

| Layer | Path |
|-------|------|
| Agents | `quant/agents/` |
| Pipelines | `quant/pipelines/` |
| Storage clients | `quant/storage/` |
| Schemas | `quant/schemas/` |
| Orchestration config | `quant/orchestration/agent_builder/` |
| UI | `dashboard/app.py` |

## Python dependencies (planned)

- `google-cloud-aiplatform` / Agent Builder SDK
- `pymongo`, `elasticsearch`
- `pandas`, `numpy`, `scikit-learn`
- `yfinance`, `pandas-datareader`
- `streamlit`, `pydantic`, `httpx`
- `pytest` (dev)

See root `requirements.txt`.

## Environments

| Env | Purpose |
|-----|---------|
| Local | Streamlit + direct pipeline scripts |
| GCP | Agent Builder, Cloud Run, Scheduler |
| Atlas | MongoDB MCP target |
| Elastic Cloud | Search MCP target |

Copy `.env.example` → `.env` for local development.
