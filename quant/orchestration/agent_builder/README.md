# Agent Builder configuration

Hackathon MCP wiring for Quant (project `quant-hackathon`).

| File | Purpose |
|------|---------|
| `app.yaml` | Six-agent workflow + MCP server bindings |
| `mcp/mongodb.json` | MongoDB Atlas MCP registration metadata |
| `mcp/elastic.json` | Elastic kNN bridge registration metadata |
| `agents/*.yaml` | Per-agent tool bindings |

## Deploy MCP servers

```powershell
.\scripts\deploy_mongodb_mcp.ps1
.\scripts\deploy_elastic_mcp.ps1
```

Then set `MONGODB_MCP_URL`, `ELASTIC_MCP_URL`, and `USE_MCP_TOOLS=true` in `.env`.

Full guide: [Agent-Builder-Setup.md](../../docs/wiki/Agent-Builder-Setup.md)
