"""FastAPI server — health, setup, and SSE analysis stream."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from quant.pipeline import check_prerequisites, run_full_analysis, save_report  # noqa: E402

app = FastAPI(title="Quant API", version="1.0.0")

_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
_origins = [
    o.strip()
    for o in os.getenv("FRONTEND_ORIGIN", _default_origins).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SetupResponse(BaseModel):
    ready: bool
    issues: list[str]
    ticker: str


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for Cloud Run."""
    return {"status": "ok"}


@app.get("/setup", response_model=SetupResponse)
def setup(ticker: str = "AAPL") -> SetupResponse:
    """Return prerequisite check results for a ticker."""
    symbol = ticker.upper().strip()
    issues = check_prerequisites(symbol)
    return SetupResponse(ready=len(issues) == 0, issues=issues, ticker=symbol)


def _sse_payload(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@app.get("/analyze/{ticker}/stream")
async def analyze_stream(ticker: str) -> StreamingResponse:
    """Stream agent progress and final report via Server-Sent Events."""
    symbol = ticker.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Ticker is required")

    issues = check_prerequisites(symbol)
    if issues:
        raise HTTPException(status_code=400, detail={"issues": issues})

    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    def on_progress(event: str, agent: str, elapsed: float | None) -> None:
        if event == "agent_start":
            queue.put_nowait({"type": "agent_start", "agent": agent})
        elif event == "agent_done":
            queue.put_nowait(
                {
                    "type": "agent_done",
                    "agent": agent,
                    "elapsed_sec": elapsed,
                }
            )

    async def run_pipeline() -> None:
        try:
            result = await asyncio.to_thread(
                run_full_analysis,
                symbol,
                on_progress,
            )
            path = await asyncio.to_thread(
                save_report,
                symbol,
                result.markdown,
                result.report_json,
            )
            await queue.put(
                {
                    "type": "complete",
                    "report": result.markdown,
                    "report_json": result.report_json,
                    "rejections": result.report_json.get("audit", {}).get("rejections", []),
                    "timings": result.timings,
                    "saved_path": str(path),
                }
            )
        except Exception as exc:  # noqa: BLE001
            await queue.put({"type": "error", "message": str(exc)})
        finally:
            await queue.put(None)

    async def event_generator():
        task = asyncio.create_task(run_pipeline())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield _sse_payload(item)
        finally:
            await task

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
