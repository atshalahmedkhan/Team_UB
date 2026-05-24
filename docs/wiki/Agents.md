# Agents

Six specialized agents. Implementation modules live under `quant/agents/`.

---

## Agent 1 — Extraction

**Trigger:** Earnings release (EDGAR filing available) or manual ticker.

**Responsibilities:**

- Pull 10-Q/10-K and earnings transcript via SEC EDGAR API
- Parse high-signal sections: income statement, balance sheet, cash flow, MD&A
- Cross-reference figures across tables; flag conflicts as anomalies

**Agentic loop:** On table mismatch, re-read source sections before accepting values.

**Output:** `ExtractionResult` — line items with `{ value, unit, source_paragraph, page }`.

**Tools:** HTTP (EDGAR), MongoDB MCP (persist raw + structured).

---

## Agent 2 — Quantitative model

**Trigger:** Agent 1 completion.

**Responsibilities:**

- Compute P/E, EV/EBITDA, FCF yield, margin deltas vs prior Q and consensus
- Sensitivity analysis (e.g. EBITDA margin −150 bps)
- Self-test Python in isolated sandbox

**Agentic loop:** Write → execute → verify balance sheet / formula → rewrite on failure.

**Output:** `ModelResult` — metrics with Beat | Miss | In-Line verdicts.

**Tools:** Cloud Run Python executor (no direct DB writes).

---

## Agent 3 — Narrative drift critic

**Trigger:** After Agent 1; needs prior quarter from MongoDB.

**Responsibilities:**

- Semantic diff (not keyword) between current and prior 10-Q + transcript
- Score materiality; classify Positive / Neutral / Negative / Watch
- Flag Q&A deflections on margins/growth

**Output:** `NarrativeFlag[]` ranked by materiality.

**Tools:** MongoDB MCP (read history), Gemini embeddings / comparison.

---

## Agent 4 — Market fingerprint

**Trigger:** In parallel with micro pipeline (same orchestration run).

**Responsibilities:**

- Pull 25+ macro variables (rates, vol, credit, cross-asset, breadth)
- Z-score, percentile, first derivatives
- PCA compress to **15-dimensional** regime vector + human-readable label

**Output:** `MarketFingerprint` — `{ vector[15], regime_label, as_of_date }`.

**Tools:** FRED / yfinance pipelines (batch or live subset for demo).

---

## Agent 5 — Analog search

**Trigger:** Agent 4 completion.

**Responsibilities:**

- kNN query in Elastic (top 10 similar historical days, ~10y history)
- Enrich from MongoDB: regime narrative, forward returns 30/60/90d
- Cluster bullish vs bearish resolution paths

**Output:** `AnalogSet` — top 5 with similarity scores and outcome distributions.

**Tools:** Elastic MCP (kNN), MongoDB MCP (context).

**Example:**

```
Analog #1 — 2018-12-24 (94%)
  30d: -9% | 60d: +14% | 90d: +19%
Distribution (n=10): 30d median -1%, range [-12%, +8%]
```

---

## Agent 6 — Adversarial grader + synthesis

**Trigger:** Micro branch complete + Agent 5 complete.

### Quality control

- Reconcile Agent 2 numbers against Agent 1 raw JSON → **reject** with error text on mismatch
- Verify Agent 3 citations exist in filing text

### Synthesis

Combine micro verdict with macro analog distribution:

- *Micro bullish + macro bearish override* — e.g. beat EPS but Dec-2018-like regime
- *Micro bearish + macro bullish override* — e.g. miss but Mar-2020-style recovery regime

**Output:** `FinalReport` — four UI sections + audit trail.

**Demo hook:** Inject wrong EPS calc; grader rejects and re-invokes Agent 2 live.

---

## Orchestration pseudocode

```python
async def run_quant(ticker: str):
    macro = asyncio.create_task(run_macro_agents())  # 4 → 5
    extraction = await agent1.run(ticker)
    model = await agent2.run(extraction)
    narrative = await agent3.run(ticker, extraction)
    analogs = await macro
    report = await agent6.run(extraction, model, narrative, analogs)
    return report
```

See [Architecture](Architecture.md) for diagrams.
