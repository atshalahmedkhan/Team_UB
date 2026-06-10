"""Agent 6 should reject Agent 2 output when figures disagree with extraction."""

from __future__ import annotations

from quant.agents.agent6_grader import grade_quant_model


def test_grader_rejects_injected_model_error() -> None:
    extraction = {
        "revenue": 111_184_000_000,
        "net_income": 29_578_000_000,
        "eps": 2.01,
    }
    model = {
        "pe_ratio": 28.5,
        "beat_miss_assessment": "In-line with expectations",
        "flags": ["Strong services mix"],
    }

    result = grade_quant_model(extraction, model, inject_error=True)

    assert not result.accepted
    assert result.rejections
    assert any("revenue" in item.lower() for item in result.rejections)


def test_grader_accepts_consistent_model() -> None:
    extraction = {"revenue": 100, "net_income": 10, "eps": 1.5}
    model = {
        "revenue_note": "Uses revenue of 100 from filing",
        "net_income": 10,
        "eps": 1.5,
        "beat_miss_assessment": "Beat",
        "flags": ["Healthy margin"],
    }

    result = grade_quant_model(extraction, model, inject_error=False)

    assert result.accepted
    assert not result.rejections
