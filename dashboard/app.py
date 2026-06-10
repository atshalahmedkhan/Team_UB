"""Streamlit dashboard — professional multi-agent Quant analysis UI."""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from quant.pipeline import (  # noqa: E402
    check_prerequisites,
    run_full_analysis,
    save_report,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AGENT_NAMES = [
    "Agent 1 — Extraction",
    "Agent 2 — Quant model",
    "Agent 3 — Narrative drift",
    "Agent 4 — Market fingerprint",
    "Agent 5 — Analog search",
    "Agent 6 — Synthesis",
]

ACCENT = "#00d4ff"
BG = "#0a0a0f"
CARD = "#12121a"
ET = ZoneInfo("America/New_York")

Status = Literal["waiting", "running", "done", "failed"]

# ---------------------------------------------------------------------------
# Theme & formatting
# ---------------------------------------------------------------------------


def inject_theme() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

        .stApp {{ background-color: {BG}; color: #e4e4e7; }}
        #MainMenu, footer, header {{ visibility: hidden; }}
        .block-container {{ padding-top: 1.5rem; max-width: 1400px; }}

        .quant-logo {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 2rem;
            font-weight: 700;
            color: {ACCENT};
            letter-spacing: 0.15em;
            text-shadow: 0 0 20px rgba(0,212,255,0.4);
        }}
        .quant-subtitle {{ color: #71717a; font-size: 0.85rem; margin-top: -0.25rem; }}

        .quant-card {{
            background: {CARD};
            border: 1px solid rgba(0,212,255,0.25);
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
        }}
        .quant-card-glow {{
            box-shadow: 0 0 12px rgba(0,212,255,0.15);
        }}

        .quant-num {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            color: {ACCENT};
            text-shadow: 0 0 8px rgba(0,212,255,0.3);
        }}
        .quant-label {{ color: #a1a1aa; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }}

        .status-dot {{
            display: inline-block;
            width: 10px; height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        .dot-waiting {{ background: #555; }}
        .dot-running {{ background: #facc15; box-shadow: 0 0 6px #facc15; }}
        .dot-done {{ background: #22c55e; box-shadow: 0 0 6px #22c55e; }}
        .dot-failed {{ background: #ef4444; box-shadow: 0 0 6px #ef4444; }}

        .agent-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.4rem 0;
            border-bottom: 1px solid #1e1e2e;
            font-size: 0.85rem;
        }}
        .agent-row-failed {{ border-left: 3px solid #ef4444; padding-left: 0.5rem; }}

        .badge-beat {{ background: #166534; color: #86efac; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }}
        .badge-inline {{ background: #854d0e; color: #fde047; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }}
        .badge-miss {{ background: #991b1b; color: #fca5a5; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }}

        .chip-flag {{
            display: inline-block;
            background: rgba(245,158,11,0.15);
            border: 1px solid #f59e0b;
            color: #fbbf24;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.7rem;
            margin: 2px 4px 2px 0;
            text-transform: uppercase;
        }}

        .regime-badge {{
            display: inline-block;
            background: rgba(0,212,255,0.1);
            border: 1px solid {ACCENT};
            color: {ACCENT};
            padding: 0.5rem 1.25rem;
            border-radius: 6px;
            font-size: 1.25rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }}

        .rejection-badge {{
            background: rgba(239,68,68,0.15);
            border: 1px solid #ef4444;
            color: #fca5a5;
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            font-size: 0.8rem;
            margin-top: 0.5rem;
        }}

        .dist-bar {{ display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 0.5rem; }}
        .dist-pos {{ background: #22c55e; }}
        .dist-neg {{ background: #ef4444; }}

        .score-bar-bg {{ background: #1e1e2e; border-radius: 4px; height: 8px; flex: 1; margin: 0 0.75rem; }}
        .score-bar-fill {{ height: 100%; border-radius: 4px; }}

        .risk-card {{
            background: {CARD};
            border-left: 3px solid #f59e0b;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 0 6px 6px 0;
            font-size: 0.9rem;
        }}
        .risk-card-macro {{ border-left-color: {ACCENT}; }}

        .empty-hint {{ color: #52525b; font-style: italic; font-size: 0.9rem; }}

        @keyframes pulse {{
            0%, 100% {{ border-color: rgba(0,212,255,0.3); }}
            50% {{ border-color: rgba(0,212,255,0.8); box-shadow: 0 0 12px rgba(0,212,255,0.2); }}
        }}
        .ticker-pulse {{
            border: 1px solid rgba(0,212,255,0.3);
            border-radius: 6px;
            padding: 0.25rem;
            animation: pulse 2s ease-in-out infinite;
        }}

        .market-open {{ color: #22c55e; font-weight: 600; }}
        .market-closed {{ color: #71717a; font-weight: 600; }}

        .footer-bar {{
            border-top: 1px solid #1e1e2e;
            padding-top: 1rem;
            margin-top: 2rem;
            color: #52525b;
            font-size: 0.8rem;
            text-align: center;
        }}

        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {{
            background-color: #00d4ff !important;
            border-color: #00d4ff !important;
            color: #0a0a0f !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            background-color: #00b8e0 !important;
            border-color: #00b8e0 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_number(value: Any, kind: str = "auto") -> str:
    """Format numeric values for display."""
    if value is None:
        return "N/A"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)

    if kind == "percent" or (kind == "auto" and 0 < abs(num) < 1 and "margin" not in kind):
        if kind == "auto" and abs(num) > 0.5:
            pass
        elif abs(num) <= 1:
            return f"{num * 100:.1f}%"

    if kind == "eps" or (kind == "auto" and abs(num) < 1000 and num != int(num)):
        return f"${num:.2f}"

    if kind == "percent" or (kind == "auto" and 0 < num < 1):
        return f"{num * 100:.1f}%"

    abs_n = abs(num)
    sign = "-" if num < 0 else ""
    if abs_n >= 1e12:
        return f"{sign}${abs_n / 1e12:.1f}T"
    if abs_n >= 1e9:
        return f"{sign}${abs_n / 1e9:.1f}B"
    if abs_n >= 1e6:
        return f"{sign}${abs_n / 1e6:.1f}M"
    if abs_n >= 1e3:
        return f"{sign}${abs_n / 1e3:.1f}K"
    if abs(num) < 1 and abs(num) > 0:
        return f"{num * 100:.1f}%"
    return f"{sign}${abs_n:.2f}"


def format_return(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        v = float(value)
        if abs(v) <= 1:
            v *= 100
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.1f}%"
    except (TypeError, ValueError):
        return "N/A"


_SECTION4_HEADER = re.compile(r"## SECTION 4 — ACTIONABLE RISKS", re.IGNORECASE)


def format_earnings_summary_text(text: str) -> str:
    """Format raw numbers in Section 1 earnings summary for display."""

    def _fmt_large(n: float) -> str:
        if n >= 1_000_000_000:
            return f"${n / 1e9:.1f}B"
        if n >= 1_000_000:
            return f"${n / 1e6:.1f}M"
        return str(int(n)) if n == int(n) else str(n)

    text = re.sub(
        r"(?i)((?:revenue|net income):\s*)(\d+(?:\.\d+)?)",
        lambda m: f"{m.group(1)}{_fmt_large(float(m.group(2)))}",
        text,
    )
    text = re.sub(
        r"(?i)(eps:\s*)(\d+\.\d+)",
        lambda m: f"{m.group(1)}${float(m.group(2)):.2f}",
        text,
    )
    text = re.sub(
        r"(?i)((?:gross|operating) margin:\s*)(\d+\.\d+)",
        lambda m: f"{m.group(1)}{float(m.group(2)) * 100:.1f}%",
        text,
    )
    text = re.sub(
        r"(?i)(actual|consensus)=(\d+(?:\.\d+)?)",
        lambda m: (
            f"{m.group(1)}=${float(m.group(2)):.2f}"
            if m.group(1).lower() == "actual"
            and "eps" in text[max(0, m.start() - 20) : m.start()].lower()
            else f"{m.group(1)}={_fmt_large(float(m.group(2)))}"
            if float(m.group(2)) >= 1_000_000
            else f"{m.group(1)}={m.group(2)}"
        ),
        text,
    )
    return text


def strip_duplicate_section4(text: str) -> str:
    """Remove duplicate SECTION 4 block from parsed report text."""
    matches = list(_SECTION4_HEADER.finditer(text))
    if len(matches) >= 2:
        return text[: matches[1].start()].rstrip()
    if len(matches) == 1:
        return text[: matches[0].start()].rstrip()
    return text


def beat_badge_class(verdict: str) -> str:
    v = verdict.lower()
    if "beat" in v:
        return "badge-beat"
    if "miss" in v:
        return "badge-miss"
    return "badge-inline"


def score_color(score: float) -> str:
    if score < 4:
        return "#ef4444"
    if score <= 7:
        return "#facc15"
    return "#22c55e"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def reports_dir() -> Path:
    container = Path("/app/quant/reports")
    local = ROOT / "quant" / "reports"
    return container if container.exists() else local


def load_report_files(ticker: str) -> tuple[dict[str, Any] | None, str | None]:
    """Load today's JSON report and markdown text for a ticker."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base = reports_dir() / f"{ticker.upper()}_{date_str}"
    report_json: dict[str, Any] | None = None
    markdown: str | None = None
    if (base.with_suffix(".json")).exists():
        report_json = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
    if (base.with_suffix(".txt")).exists():
        markdown = base.with_suffix(".txt").read_text(encoding="utf-8")
    return report_json, markdown


def parse_report_sections(markdown: str) -> dict[str, str]:
    markers = [
        ("section1", r"## SECTION 1 — EARNINGS SUMMARY"),
        ("section2", r"## SECTION 2 — THESIS FLAG CHANGES"),
        ("section3", r"## SECTION 3 — MACRO REGIME CONTEXT"),
        ("section4", r"## SECTION 4 — ACTIONABLE RISKS"),
        ("rejections", r"## GRADER REJECTIONS"),
    ]
    sections: dict[str, str] = {}
    for i, (key, pattern) in enumerate(markers):
        match = re.search(pattern, markdown, re.IGNORECASE)
        if not match:
            continue
        start = match.end()
        end = len(markdown)
        for _, next_pat in markers[i + 1 :]:
            nm = re.search(next_pat, markdown[start:], re.IGNORECASE)
            if nm:
                end = start + nm.start()
                break
        sections[key] = markdown[start:end].strip()
    return sections


def parse_section1_metrics(section1: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    flags: list[str] = []
    for line in section1.splitlines():
        line = line.strip().lstrip("- ")
        if "actual=" in line or "→" in line:
            continue
        if line.lower().startswith("revenue:"):
            metrics["revenue"] = _parse_num(line.split(":", 1)[1])
        elif line.lower().startswith("net income:"):
            metrics["net_income"] = _parse_num(line.split(":", 1)[1])
        elif line.lower().startswith("eps:"):
            metrics["eps"] = _parse_num(line.split(":", 1)[1])
        elif line.lower().startswith("gross margin:"):
            metrics["gross_margin"] = _parse_num(line.split(":", 1)[1])
        elif line.lower().startswith("flag:"):
            flags.append(line.split(":", 1)[1].strip())
    metrics["flags"] = flags
    return metrics


def _parse_num(text: str) -> Any:
    text = text.strip()
    try:
        return float(text)
    except ValueError:
        return text


def nyse_status(now: datetime | None = None) -> str:
    now = now or datetime.now(ET)
    if now.weekday() >= 5:
        return "Closed"
    open_t = now.replace(hour=9, minute=30, second=0, microsecond=0)
    close_t = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return "Open" if open_t <= now <= close_t else "Closed"


def company_name(ticker: str) -> str:
    try:
        info = yf.Ticker(ticker.upper()).info
        return info.get("longName") or info.get("shortName") or ticker.upper()
    except Exception:
        return ticker.upper()


def median_90d(analogs: list[dict[str, Any]]) -> float | None:
    vals = [a.get("return_90d") for a in analogs if a.get("return_90d") is not None]
    if not vals:
        return None
    vals_f = sorted(float(v) for v in vals)
    mid = len(vals_f) // 2
    if len(vals_f) % 2:
        return vals_f[mid]
    return (vals_f[mid - 1] + vals_f[mid]) / 2


# ---------------------------------------------------------------------------
# HTML render helpers
# ---------------------------------------------------------------------------


def render_pipeline_html(
    statuses: dict[str, Status],
    timings: dict[str, float],
    *,
    highlight_agent: str | None = None,
) -> str:
    rows = []
    for name in AGENT_NAMES:
        status = statuses.get(name, "waiting")
        elapsed = timings.get(name)
        time_str = f"{elapsed:.1f}s" if elapsed is not None else "—"
        failed_cls = " agent-row-failed" if highlight_agent == name and status == "failed" else ""
        rows.append(
            f'<div class="agent-row{failed_cls}">'
            f'<span><span class="status-dot dot-{status}"></span>{name}</span>'
            f'<span class="quant-num" style="font-size:0.8rem">{time_str}</span>'
            f"</div>"
        )
    return '<div class="quant-card">' + "".join(rows) + "</div>"


def render_metric_card(label: str, value: str, glow: bool = False) -> str:
    cls = "quant-card quant-card-glow" if glow else "quant-card"
    return (
        f'<div class="{cls}" style="text-align:center">'
        f'<div class="quant-label">{label}</div>'
        f'<div class="quant-num" style="font-size:1.5rem;margin-top:0.25rem">{value}</div>'
        f"</div>"
    )


def render_distribution_bar(analogs: list[dict[str, Any]]) -> str:
    pos = sum(1 for a in analogs if (a.get("return_90d") or 0) > 0)
    neg = sum(1 for a in analogs if (a.get("return_90d") or 0) < 0)
    total = pos + neg or 1
    pw = int(pos / total * 100)
    nw = 100 - pw
    return (
        f'<div class="dist-bar">'
        f'<div class="dist-pos" style="width:{pw}%"></div>'
        f'<div class="dist-neg" style="width:{nw}%"></div>'
        f"</div>"
        f'<div style="font-size:0.7rem;color:#71717a;margin-top:0.25rem">'
        f"{pos} positive / {neg} negative analogs</div>"
    )


def render_materiality_bar(score: float) -> str:
    pct = min(max(score / 10 * 100, 0), 100)
    color = score_color(score)
    return (
        f'<div style="display:flex;align-items:center;margin:0.5rem 0">'
        f'<span class="quant-num" style="font-size:0.75rem;width:2rem">{score:.0f}</span>'
        f'<div class="score-bar-bg"><div class="score-bar-fill" style="width:{pct}%;background:{color}"></div></div>'
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Plotly chart
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_spx_history() -> Any:
    # Full history from 2015 for analog vertical lines (2021, 2018, etc.)
    data = yf.download("^GSPC", start="2015-01-01", progress=False, auto_adjust=True)
    if hasattr(data.columns, "levels"):
        data.columns = data.columns.get_level_values(0)
    return data


def build_analog_chart(analogs: list[dict[str, Any]]) -> go.Figure:
    spx = fetch_spx_history()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=spx.index,
            y=spx["Close"],
            mode="lines",
            name="S&P 500",
            line=dict(color="#52525b", width=1.5),
            hovertemplate="%{x|%Y-%m-%d}<br>Close: %{y:,.0f}<extra></extra>",
        )
    )

    today = datetime.now(timezone.utc).date()
    fig.add_vline(
        x=datetime.combine(today, datetime.min.time()),
        line=dict(color=ACCENT, width=2),
    )
    fig.add_annotation(
        x=datetime.combine(today, datetime.min.time()),
        y=1,
        yref="paper",
        text="TODAY",
        showarrow=False,
        font=dict(color=ACCENT, size=11),
    )

    for analog in analogs[:3]:
        date_str = analog.get("date", "")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
        regime = analog.get("regime_label", "")
        ret = format_return(analog.get("return_90d"))
        fig.add_vline(x=dt, line=dict(color="#f59e0b", width=1, dash="dash"))
        fig.add_annotation(
            x=dt,
            y=0,
            yref="paper",
            text=f"{date_str}<br>{regime}<br>90d: {ret}",
            showarrow=False,
            font=dict(size=9, color="#fbbf24"),
            yshift=-40,
        )

    fig.update_layout(
        title=dict(text="Historical Market Analogs", font=dict(color="#e4e4e7")),
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        height=380,
        margin=dict(l=40, r=20, t=50, b=60),
        xaxis=dict(gridcolor="#1e1e2e"),
        yaxis=dict(gridcolor="#1e1e2e", title="S&P 500"),
        showlegend=False,
        hovermode="x unified",
    )
    return fig


# ---------------------------------------------------------------------------
# Column renderers
# ---------------------------------------------------------------------------


def render_metrics_column(report_json: dict[str, Any], sections: dict[str, str], ticker: str) -> None:
    s1_metrics = parse_section1_metrics(sections.get("section1", ""))
    beats = report_json.get("beats_misses") or []

    rev = s1_metrics.get("revenue")
    ni = s1_metrics.get("net_income")
    eps = s1_metrics.get("eps")
    margin = s1_metrics.get("gross_margin")
    for bm in beats:
        m = bm.get("metric", "")
        if m == "revenue" and rev is None:
            rev = bm.get("actual")
        if m == "net_income" and ni is None:
            ni = bm.get("actual")
        if m == "eps" and eps is None:
            eps = bm.get("actual")

    name = company_name(ticker)
    st.markdown(
        f'<div style="margin-bottom:1rem">'
        f'<span class="quant-num" style="font-size:2rem">{ticker.upper()}</span>'
        f'<span style="color:#71717a;margin-left:0.75rem">{name}</span></div>',
        unsafe_allow_html=True,
    )

    ticker_obj = yf.Ticker(ticker.upper())
    fi = ticker_obj.fast_info
    live_price = fi.get("last_price") or fi.get("regular_market_price")
    prev_close = fi.get("previous_close")
    if live_price and prev_close:
        change_pct = ((live_price - prev_close) / prev_close) * 100
        sign = "+" if change_pct >= 0 else ""
        color = "#22c55e" if change_pct >= 0 else "#ef4444"
        st.markdown(
            f'<div style="margin-bottom:1rem">'
            f'<span class="quant-num" style="font-size:1.75rem">${live_price:,.2f}</span> '
            f'<span style="color:{color};font-size:0.9rem;font-weight:600">'
            f"{sign}{change_pct:.2f}%</span></div>",
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(render_metric_card("Revenue", format_number(rev)), unsafe_allow_html=True)
        st.markdown(render_metric_card("EPS", format_number(eps, "eps")), unsafe_allow_html=True)
    with c2:
        st.markdown(render_metric_card("Net Income", format_number(ni)), unsafe_allow_html=True)
        st.markdown(
            render_metric_card("Gross Margin", format_number(margin, "percent")),
            unsafe_allow_html=True,
        )

    if beats:
        st.markdown('<div class="quant-label" style="margin-top:0.5rem">Beat / Miss vs Consensus</div>', unsafe_allow_html=True)
        badges = []
        for bm in beats:
            metric = bm.get("metric", "").upper()
            verdict = bm.get("verdict", "In-line")
            cls = beat_badge_class(verdict)
            badges.append(f'<span class="{cls}">{metric} {verdict.upper()}</span> ')
        st.markdown("".join(badges), unsafe_allow_html=True)

    flags = s1_metrics.get("flags") or []
    if flags:
        st.markdown('<div class="quant-label" style="margin-top:0.75rem">Quant Flags</div>', unsafe_allow_html=True)
        chips = "".join(f'<span class="chip-flag">{f}</span>' for f in flags[:6])
        st.markdown(chips, unsafe_allow_html=True)


def render_macro_column(report_json: dict[str, Any]) -> None:
    regime = report_json.get("regime_label", "N/A")
    analogs = report_json.get("analogs") or []
    med = median_90d(analogs)

    st.markdown(f'<div class="regime-badge">{regime}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="margin:1rem 0">'
        f'<div class="quant-label">Median 90d Return</div>'
        f'<div class="quant-num" style="font-size:1.75rem">{format_return(med)}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="quant-label">Top Analog Dates</div>', unsafe_allow_html=True)
    for a in analogs[:3]:
        st.markdown(
            f'<div class="agent-row" style="font-size:0.8rem">'
            f"<span>{a.get('date', 'N/A')}</span>"
            f"<span style='color:#71717a'>{a.get('regime_label', '')}</span>"
            f'<span class="quant-num" style="font-size:0.8rem">{format_return(a.get("return_90d"))}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

    if analogs:
        st.markdown(render_distribution_bar(analogs), unsafe_allow_html=True)


def render_report_expanders(report_json: dict[str, Any], sections: dict[str, str]) -> None:
    with st.expander("EARNINGS SUMMARY", expanded=True):
        body = sections.get("section1") or report_json.get("markdown", "")
        if sections.get("section1"):
            st.markdown(format_earnings_summary_text(sections["section1"]))
        else:
            st.markdown(body[:2000] if body else "_No data_")

    with st.expander("THESIS FLAG CHANGES", expanded=True):
        flags = report_json.get("narrative_flags") or []
        if flags:
            for flag in flags:
                score = float(flag.get("materiality", 0))
                citation = flag.get("citation") or {}
                topic = (
                    citation.get("source_paragraph", "")
                    if isinstance(citation, dict)
                    else ""
                ) or "Thesis flag"
                old = flag.get("old_text", "")
                shift = flag.get("new_text", "")
                impact = flag.get("impact", "")
                st.markdown(render_materiality_bar(score), unsafe_allow_html=True)
                if old and old != topic:
                    st.markdown(f"**{topic}** — _{old}_ → {shift} _({impact})_")
                else:
                    st.markdown(f"**{topic}** — {shift} _({impact})_")
        elif sections.get("section2"):
            st.markdown(sections["section2"])
        else:
            st.markdown("_No narrative flags_")

    with st.expander("MACRO REGIME CONTEXT", expanded=True):
        synthesis = report_json.get("synthesis") or sections.get("section3", "")
        synthesis = strip_duplicate_section4(synthesis)
        st.markdown(synthesis or "_No macro context_")

    with st.expander("ACTIONABLE RISKS", expanded=True):
        risks = report_json.get("risks") or []
        macro_kw = ("macro", "regime", "rate", "vol", "credit", "market", "analog", "spx", "fed")
        if risks:
            for risk in risks:
                is_macro = any(k in risk.lower() for k in macro_kw)
                cls = "risk-card risk-card-macro" if is_macro else "risk-card"
                st.markdown(f'<div class="{cls}">{risk}</div>', unsafe_allow_html=True)
        elif sections.get("section4"):
            st.markdown(sections["section4"])
        else:
            st.markdown("_No risks identified_")


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


def init_session() -> None:
    defaults: dict[str, Any] = {
        "running": False,
        "agent_statuses": {n: "waiting" for n in AGENT_NAMES},
        "agent_timings": {},
        "result": None,
        "saved_path": None,
        "last_ticker": None,
        "rejections": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="Quant", layout="wide", page_icon="📊")
    inject_theme()
    init_session()

    # Top bar
    top_l, top_r = st.columns([3, 1])
    with top_l:
        st.markdown(
            '<div class="quant-logo">QUANT</div>'
            '<div class="quant-subtitle">Multi-Agent Analysis System</div>',
            unsafe_allow_html=True,
        )
    with top_r:
        now_et = datetime.now(ET)
        status = nyse_status(now_et)
        status_cls = "market-open" if status == "Open" else "market-closed"
        st.markdown(
            f'<div style="text-align:right">'
            f'<div class="quant-num" style="font-size:0.9rem">{now_et.strftime("%Y-%m-%d %H:%M:%S ET")}</div>'
            f'<div class="{status_cls}">NYSE {status}</div></div>',
            unsafe_allow_html=True,
        )

    col1, col2, col3 = st.columns([0.25, 0.45, 0.30])

    with col1:
        st.markdown('<div class="quant-label">Enter Ticker</div>', unsafe_allow_html=True)
        pulse_cls = "ticker-pulse" if st.session_state.result is None else ""
        st.markdown(f'<div class="{pulse_cls}">', unsafe_allow_html=True)
        ticker = st.text_input(
            "ticker",
            value=st.session_state.get("last_ticker") or "AAPL",
            label_visibility="collapsed",
            placeholder="> AAPL",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        run_clicked = st.button("Run Analysis", type="primary", use_container_width=True)

        st.markdown('<div class="quant-label" style="margin-top:1rem">Agent Pipeline</div>', unsafe_allow_html=True)
        pipeline_ph = st.empty()
        rejection_ph = st.empty()

        statuses: dict[str, Status] = dict(st.session_state.agent_statuses)
        timings: dict[str, float] = dict(st.session_state.agent_timings)
        pipeline_ph.markdown(render_pipeline_html(statuses, timings), unsafe_allow_html=True)

        rejections = st.session_state.rejections
        if rejections:
            rejection_ph.markdown(
                f'<div class="rejection-badge">Grader Rejections: {len(rejections)}</div>',
                unsafe_allow_html=True,
            )
            with st.expander("Rejection details", expanded=False):
                for entry in rejections:
                    st.warning(entry.get("reason", str(entry)))

    has_result = st.session_state.result is not None

    with col2:
        st.markdown('<div class="quant-label">Key Metrics</div>', unsafe_allow_html=True)
        if has_result:
            rj = st.session_state.result.report_json
            sections = parse_report_sections(st.session_state.result.markdown)
            render_metrics_column(rj, sections, st.session_state.last_ticker or ticker)
        else:
            st.markdown('<p class="empty-hint">Run analysis to populate metrics.</p>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="quant-label">Macro Regime</div>', unsafe_allow_html=True)
        if has_result:
            render_macro_column(st.session_state.result.report_json)
        else:
            st.markdown('<p class="empty-hint">Macro analogs appear after analysis.</p>', unsafe_allow_html=True)

    if run_clicked:
        symbol = ticker.upper().strip()
        if not symbol:
            st.error("Enter a ticker symbol.")
        else:
            issues = check_prerequisites(symbol)
            if issues:
                st.error("Fix setup issues before running:")
                for issue in issues:
                    st.markdown(f"- {issue}")
            else:
                statuses = {n: "waiting" for n in AGENT_NAMES}
                timings = {}
                st.session_state.running = True
                st.session_state.result = None
                st.session_state.rejections = []
                failed_agent: str | None = None

                def on_progress(event: str, agent: str, elapsed: float | None) -> None:
                    nonlocal failed_agent
                    if event == "agent_start":
                        statuses[agent] = "running"
                    elif event == "agent_done":
                        statuses[agent] = "done"
                        if elapsed is not None:
                            timings[agent] = elapsed
                    pipeline_ph.markdown(render_pipeline_html(statuses, timings), unsafe_allow_html=True)

                try:
                    with st.spinner(f"Running 6-agent pipeline for {symbol}…"):
                        result = run_full_analysis(symbol, on_progress)
                        out_path = save_report(symbol, result.markdown, result.report_json)
                except Exception as exc:
                    for name in AGENT_NAMES:
                        if statuses.get(name) == "running":
                            statuses[name] = "failed"
                            failed_agent = name
                            break
                    pipeline_ph.markdown(
                        render_pipeline_html(statuses, timings, highlight_agent=failed_agent),
                        unsafe_allow_html=True,
                    )
                    st.error(f"Analysis failed: {exc}")
                else:
                    rejections = result.report_json.get("audit", {}).get("rejections", [])
                    st.session_state.result = result
                    st.session_state.saved_path = str(out_path)
                    st.session_state.last_ticker = symbol
                    st.session_state.agent_statuses = statuses
                    st.session_state.agent_timings = timings
                    st.session_state.rejections = rejections
                    st.session_state.running = False
                    if rejections:
                        rejection_ph.markdown(
                            f'<div class="rejection-badge">Grader Rejections: {len(rejections)}</div>',
                            unsafe_allow_html=True,
                        )
                    st.rerun()

    if has_result:
        analogs = st.session_state.result.report_json.get("analogs") or []
        st.markdown("---")
        st.plotly_chart(build_analog_chart(analogs), use_container_width=True)

        sections = parse_report_sections(st.session_state.result.markdown)
        render_report_expanders(st.session_state.result.report_json, sections)

    # Bottom bar
    gen_at = ""
    path_str = ""
    if has_result:
        gen_at = st.session_state.result.report_json.get("generated_at", "")
        path_str = st.session_state.saved_path or ""

    st.markdown(
        f'<div class="footer-bar">'
        f"Powered by Gemini + Google Cloud Agent Builder<br>"
        f"Elastic &nbsp;|&nbsp; MongoDB<br>"
        f"{'Report: ' + path_str + ' &nbsp;·&nbsp; ' if path_str else ''}"
        f"{'Generated: ' + gen_at if gen_at else ''}"
        f"</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
