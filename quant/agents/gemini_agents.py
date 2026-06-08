"""
Six Gemini agents for Quant earnings + macro intelligence analysis.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from quant.agents.search_agent import search_analogs  # noqa: E402
from quant.agents.today_agent import describe_regime, get_today_vector  # noqa: E402
from quant.storage.mongo_client import db  # noqa: E402

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"

# Short names that work on AI Studio but not Vertex AI without remapping.
_VERTEX_MODEL_ALIASES = {
    "gemini-2.0-flash": "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite": "gemini-2.5-flash-lite",
    "gemini-2.0-flash-001": "gemini-2.5-flash-lite",
}
AGENT1_MAX_FILING_CHARS = 30_000
MAX_FILING_CHARS = 50_000
MAX_RETRIES = 5
RETRY_BASE_SEC = 15
_INVISIBLE_CHARS = ("\u200b", "\ufeff", "\xa0")


def get_gemini_model() -> str:
    """Return the configured Gemini model id (with Vertex aliases applied)."""
    model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()
    if use_vertexai():
        return _VERTEX_MODEL_ALIASES.get(model, model)
    return model


def use_vertexai() -> bool:
    """Return True when Gemini should use Vertex AI (GCP billing / credits)."""
    flag = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower()
    return flag in ("1", "true", "yes", "on")


def get_gcp_project() -> str:
    """Return GCP project id for Vertex AI."""
    project = (
        os.getenv("GCP_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or ""
    ).strip()
    if not project:
        raise RuntimeError(
            "Vertex AI mode requires GCP_PROJECT_ID (or GOOGLE_CLOUD_PROJECT) in .env."
        )
    return project


def get_gcp_location() -> str:
    """Return GCP region for Vertex AI."""
    return (
        os.getenv("GCP_LOCATION")
        or os.getenv("GOOGLE_CLOUD_LOCATION")
        or "us-central1"
    ).strip()


def get_auth_mode() -> str:
    """Return ``vertex`` or ``aistudio``."""
    return "vertex" if use_vertexai() else "aistudio"


def _sanitize_api_key(raw: str) -> str:
    """Strip whitespace, quotes, and invisible characters from an API key."""
    key = raw.strip().strip("\"'")
    for ch in _INVISIBLE_CHARS:
        key = key.replace(ch, "")
    return key


def _validate_api_key_ascii(key: str) -> None:
    """Reject API keys that would break httpx ASCII header encoding."""
    for idx, ch in enumerate(key):
        if ord(ch) > 127:
            raise RuntimeError(
                f"GOOGLE_API_KEY contains invalid character {ch!r} (U+{ord(ch):04X}) "
                f"at position {idx}. Re-copy from https://aistudio.google.com/apikey "
                "(keys are ~39 ASCII chars starting with AIza)."
            )


def _get_api_key() -> str:
    """
    Resolve Gemini API key from environment (AI Studio mode only).

    Returns:
        str: API key string.

    Raises:
        RuntimeError: If no key is configured or key contains non-ASCII chars.
    """
    api_key = (
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GEMINI_AGENTIC_PLATFORM_API_KEY")
    )
    if not api_key:
        raise RuntimeError(
            "No Gemini API key found. Set GOOGLE_API_KEY in .env "
            "(create one at https://aistudio.google.com/apikey), "
            "or enable Vertex AI: GOOGLE_GENAI_USE_VERTEXAI=true with GCP_PROJECT_ID."
        )
    key = _sanitize_api_key(api_key)
    _validate_api_key_ascii(key)
    if not (35 <= len(key) <= 45):
        print(
            f"  Warning: GOOGLE_API_KEY length is {len(key)} chars "
            "(expected ~39). Key may be corrupted."
        )
    return key


def validate_gemini_auth() -> None:
    """
    Verify Gemini auth is configured for the active mode.

    Raises:
        RuntimeError: If Vertex project/ADC or AI Studio key is missing.
    """
    if use_vertexai():
        project = get_gcp_project()
        os.environ.setdefault(
            "GOOGLE_CLOUD_QUOTA_PROJECT",
            os.getenv("GOOGLE_CLOUD_QUOTA_PROJECT") or project,
        )
        try:
            import google.auth

            google.auth.default()
        except Exception as exc:
            raise RuntimeError(
                "Vertex AI mode requires Application Default Credentials. Run:\n"
                "  gcloud auth application-default login\n"
                "  gcloud config set project "
                f"{get_gcp_project()}\n"
                f"Original error: {exc}"
            ) from exc
    else:
        _get_api_key()


def _get_client() -> Any:
    """
    Create a google-genai client for Vertex AI or AI Studio.

    Returns:
        genai.Client: Configured Gemini client.

    Raises:
        RuntimeError: If auth is not configured.
    """
    from google import genai

    if use_vertexai():
        validate_gemini_auth()
        project = get_gcp_project()
        os.environ.setdefault(
            "GOOGLE_CLOUD_QUOTA_PROJECT",
            os.getenv("GOOGLE_CLOUD_QUOTA_PROJECT") or project,
        )
        return genai.Client(
            vertexai=True,
            project=project,
            location=get_gcp_location(),
        )

    return genai.Client(api_key=_get_api_key())


def _format_gemini_error(exc: Exception) -> str:
    """
    Build a user-facing message for common Gemini API failures.

    Args:
        exc: Exception from the google-genai client.

    Returns:
        str: Actionable error text.
    """
    err_str = str(exc)
    if use_vertexai():
        if "403" in err_str or "PERMISSION_DENIED" in err_str:
            project = get_gcp_project()
            return (
                "Vertex AI Gemini call failed (403 PERMISSION_DENIED).\n"
                "Fix:\n"
                f"  1. Enable Vertex AI API on project {project}:\n"
                "     https://console.cloud.google.com/apis/library/aiplatform.googleapis.com\n"
                "  2. Run: gcloud auth application-default login\n"
                f"  3. Run: gcloud config set project {project}\n"
                f"Original error: {exc}"
            )
        return str(exc)

    if "403" in err_str or "PERMISSION_DENIED" in err_str or "API_KEY_SERVICE_BLOCKED" in err_str:
        return (
            "Gemini API access is blocked for this API key (403 PERMISSION_DENIED).\n"
            "AI Studio keys do NOT use GCP $300 credits. For GCP billing, set:\n"
            "  GOOGLE_GENAI_USE_VERTEXAI=true\n"
            "  GCP_PROJECT_ID=your-project\n"
            "Or fix AI Studio:\n"
            "  1. Create a key at https://aistudio.google.com/apikey\n"
            "  2. Enable Generative Language API in Cloud Console\n"
            "  3. Put key in .env as GOOGLE_API_KEY=your_key_here\n"
            f"Original error: {exc}"
        )
    return str(exc)


def _call_gemini(prompt: str) -> str:
    """
    Call Gemini with exponential backoff on rate-limit errors.

    Args:
        prompt: Full prompt text.

    Returns:
        str: Raw model response text.

    Raises:
        RuntimeError: If all retries are exhausted.
    """
    from google.genai import errors as genai_errors

    client = _get_client()
    last_exc: Optional[Exception] = None

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=get_gemini_model(),
                contents=prompt,
            )
            return (response.text or "").strip()
        except genai_errors.ClientError as exc:
            last_exc = exc
            code = getattr(exc, "code", None)
            if code == 429 or "429" in str(exc):
                wait = RETRY_BASE_SEC * (attempt + 1)
                print(f"  Rate limited — retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            if code == 403 or "403" in str(exc) or "API_KEY_SERVICE_BLOCKED" in str(exc):
                raise RuntimeError(_format_gemini_error(exc)) from exc
            raise RuntimeError(_format_gemini_error(exc)) from exc

    raise RuntimeError(f"Gemini API failed after {MAX_RETRIES} retries: {last_exc}")


def _generate_json(prompt: str) -> dict[str, Any] | list[Any]:
    """
    Call Gemini and parse JSON from the response.

    Args:
        prompt: Full prompt text.

    Returns:
        dict | list: Parsed JSON object.

    Raises:
        ValueError: If response is not valid JSON.
    """
    text = _call_gemini(prompt)
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _generate_text(prompt: str) -> str:
    """
    Call Gemini and return plain-text response.

    Args:
        prompt: Full prompt text.

    Returns:
        str: Model response text.
    """
    return _call_gemini(prompt)


def _filings_collection() -> Any:
    """Return MongoDB filings collection."""
    if db is None:
        raise RuntimeError("MongoDB is not connected. Set MONGO_URI in .env.")
    return db["filings"]


def _get_filing(ticker: str) -> dict[str, Any]:
    """
    Fetch the most recent filing for a ticker.

    Args:
        ticker: Stock symbol.

    Returns:
        dict: Filing document.

    Raises:
        ValueError: If no filing exists.
    """
    doc = (
        _filings_collection()
        .find_one({"ticker": ticker.upper()}, sort=[("filing_date", -1)])
    )
    if not doc:
        raise ValueError(f"No filing found for ticker {ticker}")
    return doc


# ---------------------------------------------------------------------------
# Agent 1 — Extraction
# ---------------------------------------------------------------------------


def run_extraction_agent(ticker: str) -> dict[str, Any]:
    """
    Extract structured financial metrics from SEC filing text.

    Args:
        ticker: Stock symbol.

    Returns:
        dict: Extracted financial metrics JSON.
    """
    print(f"[Agent 1] Extraction — {ticker}")
    filing = _get_filing(ticker)
    raw_text = (filing.get("raw_text") or "")[:AGENT1_MAX_FILING_CHARS]

    prompt = f"""You are a financial data extraction agent. Read this SEC filing text
for {ticker} and extract the following as JSON:
- revenue (most recent quarter, USD)
- net_income
- eps
- gross_margin (decimal, e.g. 0.45 for 45%)
- operating_margin
- guidance_language (string summary)
- risk_factor_changes (list of strings describing notable changes)

Return ONLY valid JSON with those keys. Use null for unavailable fields.

FILING TEXT:
{raw_text}
"""
    extracted = _generate_json(prompt)
    if not isinstance(extracted, dict):
        raise ValueError("Extraction agent did not return a JSON object")

    _filings_collection().update_one(
        {"_id": filing["_id"]},
        {"$set": {"extracted_data": extracted, "status": "extracted"}},
    )
    print("  Stored extracted_data, status=extracted")
    return extracted


# ---------------------------------------------------------------------------
# Agent 2 — Quantitative model
# ---------------------------------------------------------------------------


def run_quant_model_agent(ticker: str, extracted: dict[str, Any]) -> dict[str, Any]:
    """
    Compute valuation ratios and flags from extracted fundamentals.

    Args:
        ticker: Stock symbol.
        extracted: Output from extraction agent.

    Returns:
        dict: Quant model JSON with ratios and flags.
    """
    print(f"[Agent 2] Quantitative model — {ticker}")
    prompt = f"""You are a quantitative equity analyst. Given this extracted data
for {ticker}, compute and return JSON with:
- pe_ratio
- ev_ebitda
- fcf_yield
- qoq_margin_change (gross and operating if possible)
- beat_miss_assessment (string)
- flags (list of strings for unusually high/low metrics)

Use reasonable assumptions where market data is missing. Return ONLY valid JSON.

EXTRACTED DATA:
{json.dumps(extracted, indent=2)}
"""
    quant_model = _generate_json(prompt)
    if not isinstance(quant_model, dict):
        raise ValueError("Quant model agent did not return a JSON object")

    _filings_collection().update_one(
        {"ticker": ticker.upper()},
        {"$set": {"quant_model": quant_model, "status": "modeled"}},
    )
    print("  Stored quant_model, status=modeled")
    return quant_model


# ---------------------------------------------------------------------------
# Agent 3 — Narrative drift
# ---------------------------------------------------------------------------


def run_narrative_drift_agent(ticker: str) -> list[dict[str, Any]]:
    """
    Compare current vs prior quarter filing tone and risk language.

    Args:
        ticker: Stock symbol.

    Returns:
        list[dict]: Drift findings with tone and materiality scores.
    """
    print(f"[Agent 3] Narrative drift — {ticker}")
    filings = list(
        _filings_collection()
        .find({"ticker": ticker.upper()})
        .sort("filing_date", -1)
        .limit(2)
    )
    if len(filings) < 1:
        raise ValueError(f"No filings for {ticker}")

    current_text = (filings[0].get("raw_text") or "")[:MAX_FILING_CHARS]
    prior_text = (
        (filings[1].get("raw_text") or "")[:MAX_FILING_CHARS]
        if len(filings) > 1
        else "(No prior quarter filing available — analyze current filing only.)"
    )

    prompt = f"""You are a narrative drift critic for SEC filings ({ticker}).
Compare CURRENT vs PRIOR quarter filings. Identify shifts in tone around:
revenue guidance, margin outlook, competition, supply chain, regulatory risk.

Return ONLY a JSON array of objects with keys:
- topic (string)
- shift_description (string)
- tone (Positive | Neutral | Negative)
- materiality_score (integer 1-10)

CURRENT FILING:
{current_text[:60000]}

PRIOR FILING:
{prior_text[:60000]}
"""
    drift = _generate_json(prompt)
    if not isinstance(drift, list):
        drift = drift.get("findings", []) if isinstance(drift, dict) else []

    _filings_collection().update_one(
        {"_id": filings[0]["_id"]},
        {"$set": {"narrative_drift": drift, "status": "narrative_analyzed"}},
    )
    print("  Stored narrative_drift, status=narrative_analyzed")
    return drift


# ---------------------------------------------------------------------------
# Agent 4 — Market fingerprint
# ---------------------------------------------------------------------------


def run_fingerprint_agent() -> dict[str, Any]:
    """
    Compute today's 15-dim PCA vector and regime description.

    Returns:
        dict: Keys ``vector``, ``regime_label``, ``description``, ``raw``.
    """
    print("[Agent 4] Market fingerprint (today)")
    vector, regime, fingerprint = get_today_vector()
    description = describe_regime(regime)
    print(f"  Regime: {regime}")
    return {
        "vector": vector,
        "regime_label": regime,
        "description": description,
        "raw": fingerprint.get("raw", {}),
    }


# ---------------------------------------------------------------------------
# Agent 5 — Analog search
# ---------------------------------------------------------------------------


def run_analog_search_agent(vector: list[float], k: int = 10) -> dict[str, Any]:
    """
    Find historical analog days and summarize forward return outcomes.

    Args:
        vector: Today's 15-dim PCA fingerprint.
        k: Number of analogs to retrieve.

    Returns:
        dict: Analogs, clusters, and outcome statistics.
    """
    print(f"[Agent 5] Analog search (k={k})")
    analogs = search_analogs(vector, k=k)

    cluster_a = [a for a in analogs if (a.get("ret_90d") or 0) > 0]
    cluster_b = [a for a in analogs if (a.get("ret_90d") or 0) < 0]

    def _stats(key: str) -> dict[str, Optional[float]]:
        values = [a[key] for a in analogs if a.get(key) is not None]
        if not values:
            return {"median": None, "min": None, "max": None}
        import statistics

        return {
            "median": float(statistics.median(values)),
            "min": float(min(values)),
            "max": float(max(values)),
        }

    result = {
        "analogs": analogs,
        "cluster_a_bullish": cluster_a,
        "cluster_b_bearish": cluster_b,
        "stats": {
            "ret_30d": _stats("ret_30d"),
            "ret_60d": _stats("ret_60d"),
            "ret_90d": _stats("ret_90d"),
        },
    }
    print(f"  Found {len(analogs)} analogs | Bullish: {len(cluster_a)} | Bearish: {len(cluster_b)}")
    return result


# ---------------------------------------------------------------------------
# Agent 6 — Adversarial grader + synthesis
# ---------------------------------------------------------------------------


def _validate_agents(extracted: dict[str, Any], quant_model: dict[str, Any]) -> list[str]:
    """
    Cross-check Agent 1 extracted revenue against Agent 2 assumptions.

    Args:
        extracted: Extraction output.
        quant_model: Quant model output.

    Returns:
        list[str]: Validation warning messages.
    """
    warnings: list[str] = []
    ext_rev = extracted.get("revenue")
    quant_str = json.dumps(quant_model)
    if ext_rev is not None and str(ext_rev) not in quant_str:
        warnings.append(
            f"Revenue mismatch: extracted revenue={ext_rev} not referenced in quant model."
        )
    return warnings


def run_synthesis_agent(
    ticker: str,
    extracted: dict[str, Any],
    quant_model: dict[str, Any],
    narrative_drift: list[dict[str, Any]],
    fingerprint: dict[str, Any],
    analog_result: dict[str, Any],
) -> str:
    """
    Validate agent outputs and synthesize the final four-section report.

    Args:
        ticker: Stock symbol.
        extracted: Agent 1 output.
        quant_model: Agent 2 output.
        narrative_drift: Agent 3 output.
        fingerprint: Agent 4 output.
        analog_result: Agent 5 output.

    Returns:
        str: Complete markdown report.
    """
    print(f"[Agent 6] Adversarial grader + synthesis — {ticker}")
    validation_warnings = _validate_agents(extracted, quant_model)

    analogs = analog_result.get("analogs", [])[:3]
    top_analog_lines = []
    for a in analogs:
        ret90 = a.get("ret_90d")
        ret_str = f"{ret90 * 100:.1f}%" if ret90 is not None else "N/A"
        top_analog_lines.append(
            f"- {a.get('date')} (similarity={a.get('similarity_score', 0):.3f}, "
            f"90d return={ret_str}, regime={a.get('regime_label')})"
        )

    drift_sorted = sorted(
        narrative_drift,
        key=lambda x: x.get("materiality_score", 0),
        reverse=True,
    )

    section1 = "## SECTION 1 — EARNINGS SUMMARY\n"
    section1 += f"- Revenue: {extracted.get('revenue')}\n"
    section1 += f"- Net income: {extracted.get('net_income')}\n"
    section1 += f"- EPS: {extracted.get('eps')}\n"
    section1 += f"- Gross margin: {extracted.get('gross_margin')}\n"
    section1 += f"- Operating margin: {extracted.get('operating_margin')}\n"
    section1 += f"- Beat/miss: {quant_model.get('beat_miss_assessment', 'N/A')}\n"
    flags = quant_model.get("flags") or []
    for flag in flags[:5]:
        section1 += f"- Flag: {flag}\n"

    section2 = "## SECTION 2 — THESIS FLAG CHANGES\n"
    for item in drift_sorted[:8]:
        section2 += (
            f"- [{item.get('materiality_score', '?')}/10] "
            f"{item.get('topic')}: {item.get('shift_description')} "
            f"({item.get('tone')})\n"
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
Extracted: {json.dumps(extracted)[:2000]}
Quant flags: {json.dumps(quant_model.get('flags', []))}
Drift: {json.dumps(drift_sorted[:5])}
Validation warnings: {validation_warnings}
"""
    sections_3_4 = _generate_text(macro_prompt)

    report = f"# Quant Analysis Report — {ticker.upper()}\n\n"
    report += section1 + "\n"
    report += section2 + "\n"
    report += sections_3_4 + "\n"
    if validation_warnings:
        report += "\n## VALIDATION WARNINGS\n"
        for w in validation_warnings:
            report += f"- {w}\n"

    return report
