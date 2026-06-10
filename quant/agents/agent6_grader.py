"""Agent 6 — adversarial grader and micro/macro synthesis."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from quant.schemas.report import Analog, Audit, FinalReport, NarrativeFlag

MAX_QUANT_RETRIES = 2
SynthesizeFn = Callable[[str], str]


@dataclass
class GradeResult:
    """Outcome of validating Agent 2 output against Agent 1 extraction."""

    accepted: bool
    warnings: list[str] = field(default_factory=list)
    rejections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "warnings": self.warnings,
            "rejections": self.rejections,
        }


def grade_quant_model(
    extraction: dict[str, Any],
    model: dict[str, Any],
    *,
    inject_error: bool | None = None,
) -> GradeResult:
    """
    Cross-check Agent 2 quant output against Agent 1 extraction.

    Hard reject when core figures from extraction are absent from the model.
    """
    if inject_error is None:
        inject_error = os.getenv("DEMO_INJECT_MODEL_ERROR", "false").lower() == "true"

    model_copy = dict(model)
    if inject_error:
        model_copy["revenue"] = -1

    warnings: list[str] = []
    rejections: list[str] = []
    model_str = json.dumps(model_copy)

    for key in ("revenue", "net_income", "eps"):
        value = extraction.get(key)
        if value is not None and str(value) not in model_str:
            rejections.append(
                f"{key} mismatch: extracted {key}={value} not referenced in quant model."
            )

    if not model_copy.get("beat_miss_assessment"):
        warnings.append("Quant model missing beat_miss_assessment.")

    if not model_copy.get("flags"):
        warnings.append("Quant model returned no metric flags.")

    return GradeResult(
        accepted=len(rejections) == 0,
        warnings=warnings,
        rejections=rejections,
    )


def _build_analogs(analog_result: dict[str, Any]) -> list[Analog]:
    analogs: list[Analog] = []
    for item in analog_result.get("analogs", [])[:10]:
        analogs.append(
            Analog(
                date=str(item.get("date", "")),
                similarity=float(item.get("similarity_score", item.get("similarity", 0)) or 0),
                regime_label=str(item.get("regime_label", "")),
                return_30d=item.get("ret_30d"),
                return_60d=item.get("ret_60d"),
                return_90d=item.get("ret_90d"),
            )
        )
    return analogs


def _build_narrative_flags(narrative: list[dict[str, Any]]) -> list[NarrativeFlag]:
    flags: list[NarrativeFlag] = []
    for item in sorted(
        narrative,
        key=lambda x: x.get("materiality_score", 0),
        reverse=True,
    )[:8]:
        flags.append(
            NarrativeFlag(
                materiality=float(item.get("materiality_score", 0) or 0),
                old_text=str(item.get("prior_language", item.get("old_text", ""))),
                new_text=str(item.get("shift_description", item.get("new_text", ""))),
                impact=str(item.get("tone", item.get("impact", "Neutral"))),
                citation={
                    "source_paragraph": str(item.get("topic", "narrative drift")),
                    "page": None,
                },
            )
        )
    return flags


def _sections_1_2(
    ticker: str,
    extraction: dict[str, Any],
    quant_model: dict[str, Any],
    narrative_drift: list[dict[str, Any]],
) -> tuple[str, str]:
    drift_sorted = sorted(
        narrative_drift,
        key=lambda x: x.get("materiality_score", 0),
        reverse=True,
    )

    section1 = "## SECTION 1 — EARNINGS SUMMARY\n"
    section1 += f"- Revenue: {extraction.get('revenue')}\n"
    section1 += f"- Net income: {extraction.get('net_income')}\n"
    section1 += f"- EPS: {extraction.get('eps')}\n"
    section1 += f"- Gross margin: {extraction.get('gross_margin')}\n"
    section1 += f"- Operating margin: {extraction.get('operating_margin')}\n"
    section1 += f"- Beat/miss: {quant_model.get('beat_miss_assessment', 'N/A')}\n"
    for flag in (quant_model.get("flags") or [])[:5]:
        section1 += f"- Flag: {flag}\n"

    section2 = "## SECTION 2 — THESIS FLAG CHANGES\n"
    for item in drift_sorted[:8]:
        section2 += (
            f"- [{item.get('materiality_score', '?')}/10] "
            f"{item.get('topic')}: {item.get('shift_description')} "
            f"({item.get('tone')})\n"
        )

    return section1, section2


def run(
    ticker: str,
    extraction: dict[str, Any],
    model: dict[str, Any],
    narrative: list[dict[str, Any]],
    fingerprint: dict[str, Any],
    analog_result: dict[str, Any],
    *,
    rejections_log: list[dict[str, Any]] | None = None,
    validation_warnings: list[str] | None = None,
    synthesize_sections_3_4: SynthesizeFn | None = None,
) -> dict[str, Any]:
    """
    Validate outputs and produce final markdown + structured report JSON.

    Args:
        ticker: Stock symbol.
        extraction: Agent 1 output.
        model: Agent 2 output.
        narrative: Agent 3 output list.
        fingerprint: Agent 4 output.
        analog_result: Agent 5 output.
        rejections_log: Prior Agent 2 rejection attempts from the pipeline.
        validation_warnings: Non-blocking warnings accumulated during grading.
        synthesize_sections_3_4: Optional LLM callback for macro sections.

    Returns:
        dict with keys ``markdown``, ``report``, ``validation_warnings``, ``rejections``.
    """
    grade = grade_quant_model(extraction, model)
    warnings = list(validation_warnings or []) + grade.warnings
    rejections = list(rejections_log or [])

    section1, section2 = _sections_1_2(ticker, extraction, model, narrative)

    analogs = analog_result.get("analogs", [])[:3]
    top_analog_lines = []
    for analog in analogs:
        ret90 = analog.get("ret_90d")
        ret_str = f"{ret90 * 100:.1f}%" if ret90 is not None else "N/A"
        top_analog_lines.append(
            f"- {analog.get('date')} (similarity={analog.get('similarity_score', 0):.3f}, "
            f"90d return={ret_str}, regime={analog.get('regime_label')})"
        )

    macro_prompt = f"""Write two report sections in markdown for {ticker}.

SECTION 3 — MACRO REGIME CONTEXT
Today's regime: {fingerprint.get('regime_label')}
Description: {fingerprint.get('description')}
Top analog dates:
{chr(10).join(top_analog_lines)}
Median 90d return across analogs: {analog_result.get('stats', {}).get('ret_90d', {}).get('median')}
Write 2-3 paragraphs. Include a sentence like:
"Today's market most resembles [DATE] ([REGIME]). In that environment, the S&P 500 returned X% over 90 days."

SECTION 4 — ACTIONABLE RISKS
Combine micro risks from narrative drift and macro risks from analog outcomes.
Be specific and concrete. Use bullet points.

Context:
Extracted: {json.dumps(extraction)[:2000]}
Quant flags: {json.dumps(model.get('flags', []))}
Drift: {json.dumps(narrative[:5])}
Validation warnings: {warnings}
Grader rejections: {rejections}
"""

    if synthesize_sections_3_4 is not None:
        sections_3_4 = synthesize_sections_3_4(macro_prompt)
    else:
        sections_3_4 = (
            "## SECTION 3 — MACRO REGIME CONTEXT\n"
            f"Regime: {fingerprint.get('regime_label')}\n\n"
            "## SECTION 4 — ACTIONABLE RISKS\n"
            "- Review narrative drift and analog outcomes.\n"
        )

    markdown = f"# Quant Analysis Report — {ticker.upper()}\n\n"
    markdown += section1 + "\n"
    markdown += section2 + "\n"
    markdown += sections_3_4 + "\n"

    if rejections:
        markdown += "\n## GRADER REJECTIONS (Agent 2 retries)\n"
        for entry in rejections:
            markdown += f"- Attempt {entry.get('attempt', '?')}: {entry.get('reason', entry)}\n"

    if warnings:
        markdown += "\n## VALIDATION WARNINGS\n"
        for warning in warnings:
            markdown += f"- {warning}\n"

    risks: list[str] = []
    for item in narrative[:5]:
        topic = item.get("topic", "Risk")
        shift = item.get("shift_description", "")
        if shift:
            risks.append(f"{topic}: {shift}")

    final = FinalReport(
        ticker=ticker.upper(),
        generated_at=datetime.now(timezone.utc).isoformat(),
        narrative_flags=_build_narrative_flags(narrative),
        analogs=_build_analogs(analog_result),
        regime_label=str(fingerprint.get("regime_label", "")),
        synthesis=sections_3_4.strip(),
        risks=risks,
        markdown=markdown,
        audit=Audit(
            rejections=rejections,
            validation_warnings=warnings,
        ),
    )

    return {
        "markdown": markdown,
        "report": final.model_dump(),
        "validation_warnings": warnings,
        "rejections": rejections,
        "grade": grade.to_dict(),
    }
