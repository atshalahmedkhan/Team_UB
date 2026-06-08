# Quant

Agentic earnings intelligence + market analog search for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/).

> Given this earnings result **and** today's macro environment — what has historically happened next?

Quant combines a **micro layer** (SEC filings, valuation, narrative drift) with a **macro layer** (market regime vectors + historical analog search), then synthesizes both into an auditable report. Built with **Google Cloud Agent Builder**, **Gemini**, **Elastic MCP** (kNN), and **MongoDB MCP** (documents).

## Quick start (Next.js + FastAPI)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Vertex AI vars, MONGO_URI, FRONTEND_ORIGIN

# Vertex AI (uses GCP trial credits)
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

python scripts/check_setup.py
python scripts/bootstrap_historical.py --tickers AAPL
```

**Terminal 1 — API**

```bash
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — Frontend**

```bash
cd frontend
cp .env.local.example .env.local
npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and run analysis for `AAPL`.

CLI alternative: `python scripts/run_analysis.py AAPL`

Legacy Streamlit UI: `streamlit run dashboard/app.py`

## Production deploy

| Component | Platform | Command / config |
|-----------|----------|------------------|
| API | Cloud Run | `FRONTEND_ORIGIN=https://your-app.vercel.app ./scripts/deploy_api.sh` |
| Frontend | Vercel | Root dir `frontend/`, set `NEXT_PUBLIC_API_URL` to Cloud Run URL |

Cloud Run service account needs **Vertex AI User**. Store `MONGO_URI` in Secret Manager as `mongo-uri`.

## Documentation

| Resource | Description |
|----------|-------------|
| [GitHub Wiki](https://github.com/atshalahmedkhan/Team_UB/wiki) | Architecture, agents, data model, demo guide |
| [Implementation plan](docs/IMPLEMENTATION_PLAN.md) | Phased build plan and milestones |
| [Frontend README](frontend/README.md) | Next.js local dev and Vercel setup |
| [Wiki source](docs/wiki/) | Markdown synced to GitHub Wiki (`scripts/sync-wiki.sh`) |

## Repository layout

```
Team_UB/
├── api/             # FastAPI server (SSE analysis stream)
├── frontend/        # Next.js App Router UI
├── quant/           # Agents, pipelines, storage clients
├── dashboard/       # Streamlit UI (legacy)
├── docs/            # Wiki source + implementation plan
├── scripts/         # Bootstrap, deploy, wiki sync
├── tests/
├── requirements.txt
└── LICENSE
```

## Hackathon

- **Track:** Financial Services · Elastic + MongoDB partner MCP
- **Deadline:** Jun 11, 2026 · [Devpost submission](https://rapid-agent.devpost.com/)
- **License:** MIT — see [LICENSE](LICENSE)

## Team

Team_UB — building agents for real-world challenges.
