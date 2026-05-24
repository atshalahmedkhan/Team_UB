"""Streamlit dashboard — report delivery and demo UI."""

import streamlit as st

st.set_page_config(page_title="Quant", layout="wide")
st.title("Quant")
st.caption("Agentic earnings intelligence + market analog search")

ticker = st.text_input("Ticker", value="AAPL")
run = st.button("Run analysis")

if run:
    st.info(
        "Pipeline not wired yet. See docs/IMPLEMENTATION_PLAN.md and the GitHub Wiki."
    )
    st.markdown(
        "- [Wiki](https://github.com/atshalahmedkhan/Team_UB/wiki)\n"
        "- [Demo guide](https://github.com/atshalahmedkhan/Team_UB/wiki/Demo-Guide)"
    )
