# Team_UB
Building agents for real-word challenges.


# Quant — Agentic Earnings Intelligence + Market Analog Search

> *"Did the company beat earnings? Yes. Will the stock go up? That depends on what the market looked like the last time this happened."*

---

## What Is This?

**Quant** is a 6-agent AI system that answers the question no existing tool can:

> Given this earnings result AND this macro environment — what has historically happened next?

It combines two layers that have never been unified before:

- **Micro layer** — autonomously reads a company's 10-Q/10-K and earnings call transcript, updates a valuation model, and detects narrative drift in management language.
- **Macro layer** — encodes today's entire market regime as a mathematical vector and searches 10 years of market history for the most statistically similar moments — returning not a prediction, but a **distribution of real outcomes**.

The synthesis is the insight. An earnings beat in December 2018 meant nothing — the macro regime crushed it. An earnings miss in March 2020 recovered violently. **Context is everything. Quant provides it.**

---

## The Problem

Every earnings season, equity analysts face two separate bottlenecks:

**Bottleneck 1 — The filing firehose**
A single quarterly release (10-Q/10-K + call transcript) spans hundreds of pages. Reading, modeling, and comparing management's new narrative against the prior quarter takes 3–5 hours per company — manually, serially, error-prone.

**Bottleneck 2 — The missing macro context**
Even after the analyst processes the filing, they have no systematic way to answer: *"In market environments like today's, how have similar earnings outcomes actually played out?"* Bloomberg can't do this. It's keyword search from 1995. Analysts eyeball charts and guess.

A standard generative AI chatbot solves neither. Earnings analysis is a live multi-step pipeline requiring real-time data retrieval, code execution, contextual memory, and adversarial self-correction. That demands an agentic architecture.

---

## Architecture — 6 Agents, 2 Layers, 1 Unified Report

```
[Trigger: SEC EDGAR Alert — 4:01 PM on Earnings Release]
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
  ┌───────────────┐             ┌───────────────┐
  │  MICRO LAYER  │             │  MACRO LAYER  │
  │               │             │               │
  │  Agent 1      │             │  Agent 4      │
  │  Extraction   │             │  Market       │
  │               │             │  Fingerprint  │
  └──────┬────────┘             └──────┬────────┘
         │                             │
         ▼                             ▼
  ┌───────────────┐             ┌───────────────┐
  │  Agent 2      │             │  Agent 5      │
  │  Quant Model  │             │  Analog       │
  │               │             │  Search       │
  └──────┬────────┘             └──────┬────────┘
         │                             │
         ▼                             │
  ┌───────────────┐                    │
  │  Agent 3      │                    │
  │  Narrative    │                    │
  │  Drift Critic │                    │
  └──────┬────────┘                    │
         │                             │
         └──────────────┬──────────────┘
                        │
                        ▼
               ┌─────────────────┐
               │    Agent 6      │
               │  Adversarial    │
               │  Grader +       │
               │  Synthesis      │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │  Human Audit    │
               │  & Sign-off     │
               └────────┬────────┘
                        │
                        ▼
               [ Final Report — 7:00 AM ]
```

---

## The Six Agents

### Agent 1 — Extraction Agent
**Triggers at 4:01 PM on earnings release day**

- Hits the SEC EDGAR API to pull the raw 10-Q/10-K filing and earnings call transcript
- Targets high-signal sections: Consolidated Statement of Operations, Balance Sheet, Cash Flow Statement, MD&A
- **Agentic loop:** Cross-references figures across tables. If a segment revenue number in a footnote conflicts with the front-page highlight, the agent flags it as an anomaly rather than silently accepting either value
- **Output:** Structured JSON of all financial line items, each tagged with exact source paragraph and page number

---

### Agent 2 — Quantitative Model Agent
**Runs in an isolated Python execution sandbox**

- Ingests Agent 1's structured JSON and connects to the firm's valuation model
- Computes key valuation ratios: P/E, EV/EBITDA, Free Cash Flow Yield, Gross/Operating Margin deltas vs prior quarter and analyst consensus
- Runs sensitivity analysis: *"What happens to intrinsic value if EBITDA margins compress 150 bps next quarter?"*
- **Agentic loop:** Writes, executes, and self-tests Python code. If financial statements don't balance or a formula errors, the agent rewrites and re-runs until verified
- **Output:** Updated model + structured table of metric changes flagged as Beat / Miss / In-Line

---

### Agent 3 — Narrative Drift Critic
**NLP-based semantic comparison**

- Retrieves last quarter's 10-Q/10-K and earnings transcript from MongoDB
- Performs a **semantic diff** — not keyword matching — to detect shifts in tone, risk language, and forward guidance
- Example catches:
  - *"Supply chain constraints remain manageable"* → *"Geopolitical disruptions may impact shipping lanes"*
  - Removal of a previously stated revenue target with no replacement
  - New legal boilerplate added to risk factors
- Analyzes the Q&A transcript to flag where management deflected analyst questions on margins or growth
- **Agentic loop:** Iterates across document sections, scoring each change by materiality
- **Output:** Ranked list of narrative changes — old vs new language, materiality score, thesis-impact classification (Positive / Neutral / Negative / Watch)

---

### Agent 4 — Market Fingerprint Agent
**Runs in parallel with Agents 1–3**

Pulls 25+ macro variables across five dimensions:

| Category | Variables |
|---|---|
| Rates & curve | 2Y, 5Y, 10Y, 30Y yields · 2s10s spread · 3m10y spread · real yield (TIPS) |
| Volatility | VIX level · VIX3M/VIX ratio · VVIX · realized vs implied vol gap · MOVE index |
| Credit | IG spreads · HY spreads · HY-IG spread · CCC spreads |
| Cross-asset | DXY trend · gold/copper ratio · equity/bond 60d correlation |
| Equity internals | % S&P above 200d MA · defensive vs cyclical ratio · distance from 200d MA |

Normalizes each variable to a rolling z-score and percentile rank, computes first derivatives (rate of change), then compresses via PCA to a **15-dimensional orthogonal vector** representing today's market regime.

- **Output:** 15-dim market state vector + regime label (e.g., "Fed hiking · credit widening · low breadth")

---

### Agent 5 — Analog Search Agent
**Queries Elastic and MongoDB**

- Sends today's 15-dim vector to Elastic's kNN index — finds the 10 most statistically similar historical trading days across the last 10 years (~2,500 data points)
- Fetches full context for each analog from MongoDB: what conditions looked like, and what the market did in the subsequent 30, 60, and 90 days
- Clusters the 10 analogs into bullish-resolution and bearish-resolution groups
- **Output:** Top 5 analog dates with similarity scores, 30/60/90d outcome distribution, regime narrative

Example output:
```
Analog #1 — December 24, 2018 (similarity: 94%)
  Regime: Fed hiking into slowing growth, IG spreads widening
  30d: -9%  |  60d: +14%  |  90d: +19%  (Powell pivot)

Analog #2 — October 11, 2022 (similarity: 91%)
  Regime: Aggressive hiking cycle, vol elevated, breadth collapsing
  30d: +4%  |  60d: +10%  |  90d: +14%

Outcome distribution across 10 analogs:
  30d: median -1%, range [-12%, +8%]
  60d: median +7%, range [-3%, +18%]
```

---

### Agent 6 — Adversarial Grader + Synthesis
**The internal auditor. The novel synthesis. The wow moment.**

**Quality control:**
- Cross-checks Agent 2's calculations against Agent 1's raw extracted figures. Any mismatch causes a **rejection** — the grader sends the task back to Agent 2 with a specific error description and re-run instruction
- Verifies every narrative flag from Agent 3 has a verifiable source citation in the actual filing

**Synthesis — the unique insight:**
Fuses both layers into a single coherent signal. Examples:
- *"AAPL beat EPS by 4.2% [micro: bullish] but current macro regime resembles Dec 2018 and Oct 2022 — environments where similar earnings beats in large-cap tech averaged +1.1% at 30d but -9.4% at 90d as macro headwinds dominated [macro: bearish override]"*
- *"NVDA missed revenue consensus by 1.8% [micro: bearish] but macro regime resembles March 2023 — a risk-on inflection where tech recovered strongly over 90d regardless of near-term misses [macro: bullish override]"*

**Output:** Final validated, synthesized 4-section report

---

## Final Report — Delivered at 7:00 AM

Every morning, the portfolio manager opens their dashboard to find a fully referenced report on every portfolio company that reported the night before.

### Section 1 — Beats & Misses
Actuals vs analyst consensus across every major line item. Every number has a clickable footnote linking directly to its source paragraph in the SEC filing.

### Section 2 — Thesis Flag Changes
Narrative drift findings ranked by materiality score. Old language vs new language shown side by side. Each flag classified: Positive / Neutral / Negative / Watch.

### Section 3 — Macro Regime Context
Top 3 historical analog dates, similarity scores, full outcome distributions at 30/60/90 days, regime label explaining why this moment resembles those historical periods. Not a prediction — a distribution of real precedents.

### Section 4 — Actionable Portfolio Risks
Combined micro + macro signals translated into specific watchlist items with suggested monitoring triggers.

---

## Why This Is Genuinely Novel

| Capability | Bloomberg Terminal | Standard AI chatbot | Quant |
|---|---|---|---|
| Filing analysis | Manual search | Summarizes pasted text | Autonomously pulls and cross-references live from EDGAR |
| Math verification | Manual | Hallucination-prone | Python sandbox with self-correction loop |
| Narrative drift | Manual comparison | No memory | Semantic diff across quarters with materiality scoring |
| Macro context | Manual chart eyeballing | None | Vector search across 10 years of encoded market states |
| Combined signal | Not possible | Not possible | Micro earnings result + macro regime → unified distribution |
| Auditability | N/A | No source tracing | Every claim linked to exact source paragraph |

---

## Tech Stack

| Component | Tool | Role |
|---|---|---|
| Orchestration | Google Cloud Agent Builder | Hosts and coordinates all 6 agents |
| LLM backbone | Gemini | Powers reasoning across all agents |
| Vector search | **Elastic (MCP partner)** | kNN search across 15-dim market state embeddings |
| Document storage | **MongoDB (MCP partner)** | Historical snapshots, filings, transcript storage |
| Macro data | FRED API + yfinance + CBOE | Free, comprehensive market data |
| Earnings data | SEC EDGAR API | Free, official source |
| Code execution | Cloud Run (Python sandbox) | Agent 2 math and modeling |
| Scheduling | Cloud Scheduler | Triggers daily macro pipeline |
| Dashboard | Streamlit | Report delivery and demo UI |

**Partner track:** Elastic (primary MCP) + MongoDB (secondary MCP)

---

## Data Sources (All Free for Hackathon)

```python
import yfinance as yf
import pandas_datareader as pdr
import requests

# 10Y Treasury yield from FRED
treasury_10y = pdr.get_data_fred('GS10', start='2015-01-01')

# 2s10s spread
spread_2s10s = pdr.get_data_fred('T10Y2Y', start='2015-01-01')

# IG credit spreads (BAML index via FRED)
ig_spreads = pdr.get_data_fred('BAMLC0A0CM', start='2015-01-01')

# VIX
vix = yf.download('^VIX', start='2015-01-01')

# SEC EDGAR — latest AAPL filing
url = "https://data.sec.gov/submissions/CIK0000320193.json"
filings = requests.get(url).json()
```

---

## Hackathon Demo Flow

**Input:** Ticker symbol (e.g., `AAPL`) + live EDGAR trigger

**What judges see:**

1. Agent 1 pulls AAPL's latest 10-Q live from EDGAR — real-time logs visible
2. Agent 4 simultaneously encodes today's market fingerprint — macro variables streaming in
3. Agent 5 queries Elastic — "Today's market most resembles December 2018 (94% similarity)"
4. **Wow moment:** Inject a deliberate math error into Agent 2's output — Agent 6 catches it, rejects it, sends it back with a specific correction instruction — all live
5. Corrected report renders — click any number — jumps to the exact paragraph in the SEC filing
6. Final verdict: *"Beat EPS by 4.2% — but macro regime resembles Dec 2018. History says: +1% at 30d, -9% at 90d."*

---

## Build Plan

### Day 1 — Data Pipelines
- [ ] SEC EDGAR pull working for any ticker
- [ ] FRED + yfinance macro pipeline pulling all 25 variables
- [ ] Both datasets stored in MongoDB with correct schema
- [ ] Basic normalization (z-score, percentile) running

### Day 2 — Vector Layer
- [ ] PCA encoder: 55-dim → 15-dim market state vector
- [ ] Historical market states indexed in Elastic as dense vectors
- [ ] kNN search returning sensible analogs (sanity check: Dec 2018 should match current high-vol, hiking environments)
- [ ] Outcome data (30/60/90d returns) attached to each historical day

### Day 3 — Agents
- [ ] Agents 1, 2, 3 wired in Google Cloud Agent Builder
- [ ] Agent 2 Python sandbox running and self-correcting
- [ ] Agents 4 and 5 running in parallel pipeline
- [ ] Agent 6 adversarial grader: rejection loop working
- [ ] Agent 6 synthesis: micro + macro fusion logic

### Day 4 — Demo Polish
- [ ] Streamlit dashboard with live agent logs
- [ ] Report renderer with clickable footnotes
- [ ] Deliberate error injection for the demo
- [ ] End-to-end run under 5 minutes

---

## Project Structure

```
quant/
├── agents/
│   ├── agent1_extraction.py       # SEC EDGAR pull + cross-reference
│   ├── agent2_quant_model.py      # Python sandbox + valuation
│   ├── agent3_narrative_drift.py  # Semantic diff NLP
│   ├── agent4_fingerprint.py      # Market vector encoding
│   ├── agent5_analog_search.py    # Elastic kNN + MongoDB retrieval
│   └── agent6_grader.py           # Adversarial grader + synthesis
├── pipelines/
│   ├── macro_ingestion.py         # Daily FRED/yfinance pull
│   ├── pca_encoder.py             # 55-dim → 15-dim compression
│   └── edgar_ingest.py            # Filing trigger + parse
├── storage/
│   ├── elastic_index.py           # Dense vector indexing
│   └── mongo_schema.py            # Document schemas
├── dashboard/
│   └── app.py                     # Streamlit report UI
├── data/
│   └── historical_states/         # Pre-built market state library
├── tests/
│   └── test_grader_rejection.py   # Demo error injection test
├── README.md
└── requirements.txt
```

---

## The One-Line Pitch

> Quant is the first system to tell you not just how a company performed — but how the market has historically reacted to that performance in environments like today's.

---

*Built for the Google Cloud + Gemini Hackathon — Elastic Partner Track*
