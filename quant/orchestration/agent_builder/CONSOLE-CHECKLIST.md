# MCP Console Checklist (do this FIRST)

Project: **quant-hackathon** · Region: **us-central1**

## Step 1 — Open the right page

NOT the Samples gallery.

Go to: https://console.cloud.google.com/vertex-ai/agents?project=quant-hackathon

Left sidebar → **Tools** (or **MCP servers**)

## Step 2 — Register Elastic MCP

Click **Add MCP server** / **Register MCP server**

| Field | Value |
|-------|--------|
| Name | `quant-elastic-mcp` |
| Description | `Elastic kNN analog search on market regime vectors` |
| Region | `us-central1` |
| MCP server URL | `https://quant-elastic-mcp-656584077204.us-central1.run.app/tools` |

If **Import tools** fails → paste JSON from `mcp/elastic-toolspec.json`

Click **Next** → **Save**

## Step 3 — Register MongoDB MCP

Click **Add MCP server** again

| Field | Value |
|-------|--------|
| Name | `quant-mongodb-mcp` |
| Description | `MongoDB Atlas — SEC filings and market_states` |
| Region | `us-central1` |
| MCP server URL | `https://quant-mongodb-mcp-656584077204.us-central1.run.app/mcp` |

If **Import tools** fails → paste JSON from `mcp/mongodb-toolspec.json`

Click **Next** → **Save**

## Step 4 — Screenshot

Capture the **Tools** list showing BOTH servers. Save for Devpost.

## Step 5 — (Optional) Create agent app

Sidebar → **Create agent** (NOT Samples)

Name: `Quant Earnings Intelligence`
Model: `gemini-2.5-flash-lite`

Bind tools per agent — see agent YAML files in `agents/`.

## Step 6 — Verify locally (already works)

```powershell
.\.venv\Scripts\python.exe scripts\run_analysis.py NVDA
```

Expect: `[Agent 5] Elastic MCP kNN returned 10 analogs`
