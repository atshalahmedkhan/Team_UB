# Agent Builder + MCP Setup

Phase 1 wiring for the [Rapid Agent Hackathon](https://rapid-agent.devpost.com/).

## Prerequisites (already done locally)

- GCP project `quant-hackathon` with Vertex AI enabled
- MongoDB Atlas + `MONGO_URI` in `.env`
- Elastic Cloud + `ELASTIC_URL` / `ELASTIC_API_KEY` in `.env`
- Market vectors indexed: `python -m quant.agents.search_agent`

## Step 1 — Deploy MCP servers to Cloud Run

### MongoDB MCP (official partner server)

```powershell
.\scripts\deploy_mongodb_mcp.ps1
```

Copy the printed `MONGODB_MCP_URL` into `.env`:

```env
MONGODB_MCP_URL=https://quant-mongodb-mcp-xxxxx.us-central1.run.app/mcp
```

### Elastic MCP bridge (Quant kNN tool)

```powershell
.\scripts\deploy_elastic_mcp.ps1
```

Copy the printed `ELASTIC_MCP_URL` into `.env`:

```env
ELASTIC_MCP_URL=https://quant-elastic-mcp-xxxxx.us-central1.run.app
USE_MCP_TOOLS=true
```

## Step 2 — Register in GCP Agent Builder

1. Open [Vertex AI → Agent Builder](https://console.cloud.google.com/vertex-ai/agents)
2. Project: **quant-hackathon**
3. **Tools** → **Register MCP server**

| Server | URL | Notes |
|--------|-----|-------|
| MongoDB | `{MONGODB_MCP_URL}` | Streamable HTTP, path `/mcp` |
| Elastic | `{ELASTIC_MCP_URL}/tools` | Custom HTTP tools; primary: `market_state_knn` |

Config references: `quant/orchestration/agent_builder/mcp/`

## Step 3 — Create the Quant agent app

Use manifest: `quant/orchestration/agent_builder/app.yaml`

Create six agents matching:

| Agent | MCP tools |
|-------|-----------|
| 1 Extraction | MongoDB find/update |
| 2 Quant model | Gemini only |
| 3 Narrative drift | MongoDB find |
| 4 Fingerprint | MongoDB find |
| 5 Analog search | **Elastic `market_state_knn`** |
| 6 Grader | Gemini only |

## Step 4 — Verify

```powershell
.\.venv\Scripts\python.exe scripts\check_setup.py
```

With `USE_MCP_TOOLS=true` you should see MongoDB MCP + Elastic MCP checks.

Run analysis:

```powershell
.\.venv\Scripts\python.exe scripts\run_analysis.py NVDA
```

Agent 5 log should show: `Elastic MCP kNN returned 10 analogs`

## Demo screenshot checklist for judges

- [ ] Agent Builder console showing 2 registered MCP servers
- [ ] Six agents in workflow
- [ ] UI agent stepper completing for NVDA
- [ ] Report section 3 citing analog dates from Elastic

## Security notes

- MongoDB MCP deploy uses `MDB_MCP_READ_ONLY=true`
- For production, use `--no-allow-unauthenticated` + Cloud Run IAM
- Store connection strings in Secret Manager, not git
