# Architecture

Quant is a **six-agent**, **two-layer** system orchestrated by **Google Cloud Agent Builder** with **Gemini** reasoning and partner **MCP** tools (Elastic, MongoDB).

## High-level flow

```
[Trigger: ticker or EDGAR earnings alert]
              │
    ┌─────────┴─────────┐
    ▼                   ▼
 MICRO LAYER         MACRO LAYER
 Agents 1→2→3        Agents 4→5
    │                   │
    └─────────┬─────────┘
              ▼
        Agent 6 — Grader + Synthesis
              ▼
        Human audit (Streamlit)
              ▼
        Final report (JSON + UI)
```

## Layers

### Micro layer

Answers: *What did the company report, how does it compare, and what changed in management's story?*

| Step | Agent | Output |
|------|-------|--------|
| Extract | 1 | Structured financial JSON + citations |
| Model | 2 | Beat/Miss table, ratios, sensitivity |
| Narrative | 3 | Ranked semantic drift flags |

Runs mostly **sequentially** (2 depends on 1; 3 depends on MongoDB prior quarter).

### Macro layer

Answers: *What does today's market regime look like, and what happened after similar regimes?*

| Step | Agent | Output |
|------|-------|--------|
| Fingerprint | 4 | 15-dim vector + regime label |
| Analog search | 5 | Top-k similar days + 30/60/90d distributions |

Runs **in parallel** with micro layer once triggered.

### Synthesis layer

**Agent 6** validates micro outputs (math vs extraction, citation checks), fuses macro analog distributions, and produces the final four-section report. Implements an **adversarial rejection loop** back to Agent 2 on mismatch.

## Orchestration

| Concern | Choice |
|---------|--------|
| Host | Google Cloud Agent Builder |
| LLM | Gemini (tool use, planning, NLP) |
| Parallelism | Macro branch independent of micro branch until synthesis |
| Code execution | Cloud Run sandbox (Agent 2 only) |
| Scheduling | Cloud Scheduler → daily `macro_ingestion` |
| UI | Streamlit reads final report JSON + agent run logs |

## MCP integration

| Partner | Use in Quant |
|---------|----------------|
| **Elastic** | Dense vector index; kNN on 15-dim market states (Agent 5) |
| **MongoDB** | Filings, transcripts, prior-quarter snapshots, analog metadata (Agents 1, 3, 5) |

Agents do not call Elastic/MongoDB directly from arbitrary code — tools are exposed via **MCP servers** registered in Agent Builder so judges can see partner integration.

## Security & compliance

- SEC EDGAR: required `User-Agent` with contact email
- No investment advice: report presents **historical distributions**, not predictions
- Secrets in GCP Secret Manager / local `.env` (never committed)
- Sandbox: no network from Agent 2 container except allowlisted APIs if needed

## Related pages

- [Agents](Agents.md) — per-agent detail
- [Data Model](Data-Model.md) — storage layout
- [Tech Stack](Tech-Stack.md) — services list
