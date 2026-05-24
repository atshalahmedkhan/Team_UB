# Hackathon Requirements

Source: [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/) · Deadline **Jun 11, 2026** (2:00pm PDT).

## What you must build

| Requirement | How Quant satisfies it |
|-------------|------------------------|
| Functional **agent** (not chatbot) | Six-agent pipeline with planning, tools, execution |
| **Gemini** + **Agent Builder** | Orchestration host + reasoning backbone |
| **Partner MCP** integration | Elastic (kNN) + MongoDB (documents) |
| Real-world problem | Equity analysts: earnings + macro context |
| Multi-step missions | Extract → model → narrative ∥ fingerprint → analog → grade/synthesize |
| Human oversight | Streamlit audit UI; grader rejection loop |

## Partner track (our submission)

- **Primary:** Elastic — vector analog search (Agent 5)
- **Secondary:** MongoDB — filings, transcripts, market day metadata
- **Theme fit:** Financial Services

Prize buckets are **per partner** — we compete in Elastic and MongoDB categories separately if dual-integrated meaningfully.

## Submission checklist

### Repository (required)

- [ ] Public GitHub repo URL in Devpost
- [ ] **LICENSE** visible in repo About (MIT recommended)
- [ ] README with setup instructions
- [ ] Reproducible dependencies (`requirements.txt`)

### Devpost form

- [ ] Project title + elevator pitch
- [ ] Description + architecture
- [ ] Demo video (recommended 2–3 min)
- [ ] Screenshots / diagram
- [ ] Link to wiki or docs

### Technical proof points for judges

- [ ] Live or recorded EDGAR pull
- [ ] Elastic kNN returning named historical dates
- [ ] MongoDB storing/retrieving prior-quarter filing
- [ ] Agent 6 catching deliberate calculation error
- [ ] Citations linking numbers to filing text

## Judging criteria

| Criterion | Emphasis for Quant |
|-----------|---------------------|
| **Technological implementation** | Agent Builder wiring, MCP usage, sandbox math, vector pipeline |
| **Design** | Streamlit UX, readable report, live agent logs |
| **Potential impact** | Analyst time saved; macro context Bloomberg lacks |
| **Quality of idea** | Micro + macro synthesis is differentiated |

## Out of scope (avoid scope creep)

- Live brokerage execution
- Real-time consensus estimates (use mock or free sources)
- Production compliance (MiFID, etc.) — disclose research prototype

## Links

- [Devpost](https://rapid-agent.devpost.com/)
- [Demo Guide](Demo-Guide.md)
- [Implementation plan](../IMPLEMENTATION_PLAN.md)
