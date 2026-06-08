"""Streamlit dashboard — report delivery and demo UI."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from quant.pipeline import check_prerequisites, run_full_analysis, save_report  # noqa: E402

st.set_page_config(page_title="Quant", layout="wide")
st.title("Quant")
st.caption("Agentic earnings intelligence + market analog search")

ticker = st.text_input("Ticker", value="AAPL")
run = st.button("Run analysis", type="primary")

with st.expander("Setup status", expanded=False):
    issues = check_prerequisites(ticker.upper().strip()) if ticker else []
    if not issues:
        st.success("Ready to run analysis.")
    else:
        for issue in issues:
            st.warning(issue)

if run:
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
            with st.spinner(f"Running 6-agent analysis for {symbol}…"):
                start = time.perf_counter()
                try:
                    report, timings = run_full_analysis(symbol)
                    elapsed = time.perf_counter() - start
                    out_path = save_report(symbol, report)
                except Exception as exc:
                    st.error(f"Analysis failed: {exc}")
                else:
                    st.success(f"Done in {elapsed:.0f}s — saved to `{out_path}`")
                    with st.expander("Agent timings"):
                        for name, sec in timings.items():
                            st.write(f"{name}: {sec:.1f}s")
                    st.markdown(report)
