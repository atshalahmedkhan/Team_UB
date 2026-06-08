# Quant Frontend (Next.js)

Dark-terminal UI for the six-agent Quant analysis pipeline.

## Local development

**Terminal 1 — API**

```bash
cd ..   # repository root
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — Frontend**

```bash
cp .env.local.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | FastAPI base URL (default `http://localhost:8000`) |

## Production (Vercel)

1. Import this `frontend/` directory as a Vercel project.
2. Set `NEXT_PUBLIC_API_URL` to your Cloud Run API URL.
3. Set `FRONTEND_ORIGIN` on the API to your Vercel domain (comma-separated if multiple).

Deploy API: see `../scripts/deploy_api.sh`.
