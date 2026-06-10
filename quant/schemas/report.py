"""Final report contract (agents → dashboard)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_paragraph: str
    page: int | None = None


class BeatMiss(BaseModel):
    metric: str
    actual: float
    consensus: float | None = None
    verdict: str  # Beat | Miss | In-Line
    citation: Citation


class NarrativeFlag(BaseModel):
    materiality: float
    old_text: str
    new_text: str
    impact: str  # Positive | Neutral | Negative | Watch
    citation: Citation


class Analog(BaseModel):
    date: str
    similarity: float
    regime_label: str
    return_30d: float | None = None
    return_60d: float | None = None
    return_90d: float | None = None


class Audit(BaseModel):
    agent_runs: list[str] = Field(default_factory=list)
    rejections: list[dict] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    ticker: str
    generated_at: str
    beats_misses: list[BeatMiss] = Field(default_factory=list)
    narrative_flags: list[NarrativeFlag] = Field(default_factory=list)
    analogs: list[Analog] = Field(default_factory=list)
    regime_label: str = ""
    synthesis: str = ""
    risks: list[str] = Field(default_factory=list)
    markdown: str = ""
    audit: Audit = Field(default_factory=Audit)
