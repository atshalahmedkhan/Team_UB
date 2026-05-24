# Quant Wiki

**Quant** is a six-agent earnings intelligence system for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/) (Financial Services · **Elastic** + **MongoDB** partner tracks).

## What it does

Given an earnings release and today's macro regime, Quant:

1. Pulls and cross-references SEC filings and transcripts (micro layer).
2. Updates valuation metrics and flags narrative drift vs prior quarter.
3. Encodes today's market as a vector and finds historical analog days (macro layer).
4. Synthesizes micro + macro into an auditable report with source citations.

> *"Did the company beat earnings? Yes. Will the stock go up? That depends on what the market looked like the last time this happened."*

## Wiki pages

| Page | Contents |
|------|----------|
| [Architecture](Architecture) | Six agents, data flow, orchestration |
| [Agents](Agents) | Per-agent responsibilities, I/O, loops |
| [Data Model](Data-Model) | MongoDB collections, Elastic index, schemas |
| [Implementation Plan](Implementation-Plan) | Phased build plan, milestones, risks |
| [Hackathon Requirements](Hackathon-Requirements) | Submission checklist, judging criteria |
| [Demo Guide](Demo-Guide) | Judge-facing demo script |
| [Tech Stack](Tech-Stack) | GCP, Gemini, MCP partners, external APIs |

## Repository

- **Code:** [github.com/atshalahmedkhan/Team_UB](https://github.com/atshalahmedkhan/Team_UB)
- **Wiki source:** `docs/wiki/` in the repo (sync with `scripts/sync-wiki.sh`)

## Quick links

- [README](https://github.com/atshalahmedkhan/Team_UB#readme) — setup and layout
- [Devpost](https://rapid-agent.devpost.com/)
