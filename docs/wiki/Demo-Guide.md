# Demo Guide

Target runtime: **under 5 minutes**. Audience: hackathon judges.

## Setup (before recording)

1. Pre-index Elastic with historical vectors (avoid cold-start delay).
2. Cache AAPL latest filing in MongoDB; enable **live** pull as backup.
3. Configure Agent Builder session with all MCP tools connected (green status).
4. Open Streamlit dashboard fullscreen; hide dev toolbars.

## Script (6 beats)

### 1 — Hook (30s)

> "Analysts know if Apple beat earnings in five minutes. They don't know how the market reacted to similar beats in environments like today. Quant does both."

Enter ticker: `AAPL`.

### 2 — Micro layer live (90s)

- Show Agent 1 log: EDGAR pull, section extraction, cross-reference pass.
- Show Agent 2: Python sandbox updating ratios; Beat/Miss table appearing.
- Show Agent 3: one narrative drift flag with **old vs new** language side by side.

### 3 — Macro layer parallel (60s)

- Agent 4: stream macro variables → regime label (e.g. "hiking · widening credit · low breadth").
- Agent 5: Elastic kNN → **"Today most resembles Dec 24, 2018 (94%)"** with outcome stats.

### 4 — Wow moment — adversarial grader (60s)

- Enable **demo mode** (`DEMO_INJECT_MODEL_ERROR=true`).
- Agent 6 detects EPS mismatch vs extraction → **rejection** card with specific fix instruction.
- Re-run Agent 2 → corrected table.

### 5 — Report walkthrough (60s)

Scroll four sections:

1. **Beats & Misses** — click footnote → filing paragraph
2. **Thesis flags** — materiality sorted
3. **Macro context** — analog distribution chart (not a price prediction)
4. **Portfolio risks** — combined micro/macro watch items

### 6 — Close (30s)

> "Quant doesn't predict the stock. It shows what historically happened when earnings looked like this **and** the market looked like this."

## Fallbacks

| Failure | Fallback |
|---------|----------|
| EDGAR timeout | Load cached filing; mention live path in README |
| Elastic down | Pre-rendered analog JSON for demo date |
| Agent Builder latency | Run pre-baked `reports` document; show recording of live run |

## Environment flags

```bash
DEMO_INJECT_MODEL_ERROR=true   # Agent 6 rejection demo
DEMO_TICKER=AAPL
DEMO_USE_CACHED_FILING=false   # set true for offline
```

## Recording tips

- Picture-in-picture: Streamlit + Agent Builder trace
- Caption partner logos: Elastic + MongoDB + Google Cloud
- End card: repo URL + wiki link
