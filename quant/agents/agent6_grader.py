"""Agent 6 — adversarial grader and micro/macro synthesis."""

from __future__ import annotations

import os


def run(
    extraction: dict,
    model: dict,
    narrative: dict,
    analogs: dict,
    *,
    inject_error: bool | None = None,
) -> dict:
    """Validate outputs and produce final four-section report."""
    if inject_error is None:
        inject_error = os.getenv("DEMO_INJECT_MODEL_ERROR", "false").lower() == "true"
    raise NotImplementedError("Wire rejection loop + synthesis prompts")
