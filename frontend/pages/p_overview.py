import streamlit as st
import pandas as pd
from components.landing import render_landing
from components.charts import get_chart_theme
from components.tab_graph import render_graph_preview
import plotly.graph_objects as go
import os

BACKEND = os.environ.get("BACKEND_URL", "http://localhost:8000")

result = st.session_state.get("result")
if not result:
    render_landing(BACKEND)
    st.stop()

is_dark = st.session_state.get("theme", "dark") == "dark"
seg_df  = pd.DataFrame(result.get("segment_adoption", []))
assum   = result["assumptions"]

# ── Quick-stats metrics ────────────────────────────────────────────────────────
st.markdown(
    '<div class="vg-section-head">📊 Results Overview</div>',
    unsafe_allow_html=True,
)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Final MRR",     f"${result['final_mrr']:,.0f}")
col2.metric("Peak Adoption", f"{result['peak_adoption_rate']*100:.1f}%")
col3.metric("Monthly Churn", f"{result['final_churn_rate']*100:.1f}%")
col4.metric("ARR",           f"${result['final_arr']:,.0f}")

# ── Segment adoption bar chart ────────────────────────────────────────────────
if not seg_df.empty and {"month", "seg_name", "adoption_rate"}.issubset(seg_df.columns):
    CT  = get_chart_theme(is_dark)
    lm  = seg_df[seg_df["month"] == seg_df["month"].max()]
    fig = go.Figure(go.Bar(
        x=lm["seg_name"],
        y=(lm["adoption_rate"] * 100).round(1),
        marker_color=["#818cf8", "#34d399", "#fbbf24", "#f472b6"][: len(lm)],
        text=(lm["adoption_rate"] * 100).round(1).astype(str) + "%",
        textposition="outside",
    ))
    fig.update_layout(
        **CT,
        title="Final Adoption Rate by Segment",
        yaxis_title="Adoption %",
        height=300,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── AI assumptions summary ────────────────────────────────────────────────────
with st.expander("🤖 AI Assumptions"):
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("TAM",          f"{assum['total_addressable_market']:,}")
    a2.metric("Monthly Churn",f"{assum['churn_rate_monthly']*100:.1f}%")
    a3.metric("Virality",     f"{assum['virality_coefficient']:.2f}")
    a4.metric("Feature Match",f"{assum['feature_match']*100:.0f}%")

st.markdown("<div style='margin:.75rem 0'></div>", unsafe_allow_html=True)

# ── Live population graph ──────────────────────────────────────────────────────
st.markdown(
    '<div class="vg-section-head">🌐 Live Population Graph</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="vg-result-sub">Nodes settle in real time via physics simulation — hover any node for details. '
    'Use the <b>Graph</b> page in the sidebar for the full view with refresh controls.</div>',
    unsafe_allow_html=True,
)

gd = st.session_state.get("graph_data", {})
render_graph_preview(gd, is_dark)
