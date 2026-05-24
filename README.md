# Quant

Agentic earnings intelligence + market analog search for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/).

> Given this earnings result **and** today's macro environment — what has historically happened next?

Quant combines a **micro layer** (SEC filings, valuation, narrative drift) with a **macro layer** (market regime vectors + historical analog search), then synthesizes both into an auditable report. Built with **Google Cloud Agent Builder**, **Gemini**, **Elastic MCP** (kNN), and **MongoDB MCP** (documents).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add GCP, Elastic, MongoDB credentials
streamlit run dashboard/app.py
```

## Documentation

| Resource | Description |
|----------|-------------|
| [GitHub Wiki](https://github.com/atshalahmedkhan/Team_UB/wiki) | Architecture, agents, data model, demo guide |
| [Implementation plan](docs/IMPLEMENTATION_PLAN.md) | Phased build plan and milestones |
| [Wiki source](docs/wiki/) | Markdown synced to GitHub Wiki (`scripts/sync-wiki.sh`) |

## Repository layout

```
Team_UB/
├── quant/           # Agents, pipelines, storage clients
├── dashboard/       # Streamlit report UI
├── docs/            # Wiki source + implementation plan
├── scripts/         # Wiki sync, data bootstrap
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
